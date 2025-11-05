import os
import numpy as np
from pathlib import Path
import json
from datetime import datetime
from pynput.keyboard import Listener, KeyCode
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Final
import logging
import threading
import time
import cv2

import olympe
from olympe.messages import camera
from olympe.messages.ardrone3.Piloting import Landing, TakeOff

olympe.log.update_config({"loggers": {"olympe": {"level": "CRITICAL"}}})

class LoggerSetup:
    LEVEL_WIDTH: Final[int] = 8

    @staticmethod
    def setup_logger(
            logger_name: str,
            log_file: str | Path | None = None,
            level: int = logging.DEBUG,
            console_level: int = logging.INFO,
            file_level: int = logging.DEBUG
    ) -> logging.Logger:
        """
        Set up a logger with both console and file handlers.

        :param logger_name: Name of the logger.
        :param log_file: Optional path to log file. If None, only console logging is set.
        :param level: Overall logging level.
        :param console_level: Logging level for console output.
        :param file_level: Logging level for file output.
        :return: Configured logger instance.
        """
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
        logger.handlers.clear()

        console_formatter = logging.Formatter(
            f'%(asctime)s - [%(levelname)-{LoggerSetup.LEVEL_WIDTH:d}s] - %(name)s - '
            f'[%(filename)s:%(lineno)d] - %(message)s'
        )
        file_formatter = logging.Formatter(
            f'%(asctime)s - [%(levelname)-{LoggerSetup.LEVEL_WIDTH:d}s] - %(name)s - [%(filename)s:%(lineno)d] - '
            f'[Thread: %(threadName)s | PID: %(process)d] - %(message)s'
        )

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(console_level)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=5)
            file_handler.setLevel(file_level)
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)

        return logger

class DroneFrameReader:
    """
    Handler for drone video streams that processes frames and manages metadata.

    This class handles the streaming of video from a drone, converting frames to OpenCV
    format, and optionally saving metadata associated with the stream.
    """

    def __init__(self, drone: olympe.Drone, 
                 logger_dir: str | Path | None = None, metadata_dir: str | Path | None = None):
        assert drone.connected, f"{drone} is not connected"
        assert drone.streaming is not None, f"{drone} drone.streaming is None"
        self.drone = drone
        logger_dir = Path(logger_dir) / f"{self.__class__.__name__}.log" if logger_dir is not None else None
        self.logger = LoggerSetup.setup_logger(logger_name=self.__class__.__name__, log_file=logger_dir)
        self.metadata = []
        self.metadata_dir = Path(metadata_dir) / "metadata.json" if metadata_dir is not None else None
        self._current_frame: np.ndarray | None = None
        self._current_frame_lock = threading.Lock()

    def get_current_frame(self, timeout_s: int = 10) -> np.ndarray:
        """gets the latest frame processed from the drone stream. Blocks for timeout_s if no frame is available yet."""
        assert self.drone.connected, f"{self.drone} is not connected"
        n_tries, sleep_duration = 0, 1
        while self._current_frame is None:
            if n_tries * sleep_duration > timeout_s:
                raise ValueError(f"Waited for {timeout_s} and no frame was produced")
            self.logger.info("No frame yet... blocking")
            time.sleep(1)
            n_tries += 1
        with self._current_frame_lock:
            return self._current_frame

    def start_streaming(self):
        """Setup callback functions for live config processing and starts the config streaming."""
        self.drone.streaming.set_callbacks(
            raw_cb=self._yuv_frame_cb,
            start_cb=(lambda _: self.logger.info("Video stream started.")),
            end_cb=(lambda _: self.logger.info("Video stream end.")),
            flush_raw_cb=(lambda _: self.logger.warning("Flush requested for stream. Resetting queue.")),
        )
        self.logger.info("Starting streaming...")
        self.drone.streaming.start()
        self.is_streaming = True

    def stop_streaming(self):
        """Properly stop the config stream and disconnect."""
        self.logger.info("Stopping streaming...")
        try:
            self.drone.streaming.stop()
            self._save_metadata()
        except Exception as e:
            self.logger.error("Unable to properly stop the streaming...")
            self.logger.critical(e, exc_info=True)

    def _yuv_frame_cb(self, yuv_frame: olympe.VideoFrame):
        """
        This function will be called by Olympe for each decoded YUV frame. It transforms the YUV frame into an OpenCV
        frame, and unrefs the frame.
        """
        cv2_cvt_colors = {
            olympe.VDEF_I420: cv2.COLOR_YUV2BGR_I420,
            olympe.VDEF_NV12: cv2.COLOR_YUV2BGR_NV12,
        }

        if not yuv_frame:
            self.logger.warning("Received empty frame")
            return
        try:
            with self._current_frame_lock:
                yuv_frame.ref()
                self._current_frame = cv2.cvtColor(yuv_frame.as_ndarray(), cv2_cvt_colors[yuv_frame.format()])
                self.logger.debug(f"Received a new frame at {datetime.now().isoformat()}. "
                                  f"Shape: {self._current_frame.shape}")
                self._prepare_metadata(vmeta_data=yuv_frame.vmeta()[1])
        finally:
            yuv_frame.unref()

    def _prepare_metadata(self, vmeta_data: dict) -> None:
        if self.metadata_dir is None:
            return
        if len(vmeta_data) == 0:
            self.logger.warning("Received empty metadta")
            return

        self.metadata.append({
            "time": datetime.now().isoformat(),
            "drone": vmeta_data["drone"],
            "camera": vmeta_data["camera"],
        })
        if len(self.metadata) == 100:
            self._save_metadata()

    def _save_metadata(self) -> None:
        """Save the current metadata to disk and clear the in-memory list."""
        if self.metadata_dir is None or len(self.metadata) == 0:
            self.logger.warning("No metadata to save or path non existent.")
            return

        self.logger.info(f"Saving {len(self.metadata)} metadata entries...")
        Path(self.metadata_save_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self.metadata_save_path, "a") as fp:
            fp.write(json.dumps(self.medata, indent=4))


class KeyboardController(threading.Thread):
    def __init__(self, drone: olympe.Drone):
        super().__init__()
        self.listener = Listener(on_release=self.on_release)
        self.drone = drone

    def on_release(self, key: KeyCode):
        if key == KeyCode.from_char("T"):
            print("T pressed. Lifting off.")
            self.drone(TakeOff()).wait().success()
        elif key == KeyCode.from_char("L"):
            print("L pressed. Landing.")
            self.drone(Landing()).wait().success()
        else:
            print(f"Unused char: {key}")

    def run(self):
        self.listener.start()
        self.listener.join()

def main():
    drone = olympe.Drone(ip := os.getenv("DRONE_IP"))
    assert drone.connect(), f"could not connect to '{ip}'"
    frame_reader = DroneFrameReader(drone, logger_dir=Path.cwd() / "logs", metadata_dir=Path.cwd() / "metadata")
    frame_reader.start_streaming()

    kb_controller = KeyboardController(drone=drone)
    kb_controller.start()

    while frame_reader.is_streaming:
        time.sleep(1)
        rgb = frame_reader.get_current_frame()
        print(f"RGB: {rgb.shape}")
        cv2.imshow("img", rgb)
        cv2.waitKey(1)
    drone.disconnect()

if __name__ == '__main__':
    main()
