import os
import olympe
import numpy as np
from pathlib import Path
import json
from datetime import datetime

from drone_base.config.drone import DroneIp
from drone_base.stream.base_streaming_controller import BaseStreamingController
from drone_base.stream.display_only_processor import DisplayOnlyProcessor
from drone_base.control.drone_commander import DroneCommander
# from drone_base.stream.stream_handler import StreamHandler
from drone_base.config.video import VideoConfig

import threading
import time
from pathlib import Path

import cv2
import numpy as np
import olympe
from olympe.messages import camera

from drone_base.config.logger import LoggerSetup
from drone_base.config.video import VideoConfig
from drone_base.stream.processing.streaming_metadata import save_data

olympe.log.update_config({"loggers": {"olympe": {"level": "CRITICAL"}}})


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
        with open(self.metadata_save_path, "a") as fp:
            fp.write(json.dumps(self.medata, indent=4))

class Processor(DisplayOnlyProcessor):
    def _process_frame(self, frame: np.ndarray) -> np.ndarray:
        # global IX, STATE
        # if IX % 100 == 0:
        #     if STATE == 0:
        #         print("================= Taking off")
        #         self.drone_commander.take_off()
        #     else:
        #         print("================= Landing")
        #         self.drone_commander.land()
        #     STATE = 1 - STATE
        # IX += 1
        return frame

def main():
    drone = olympe.Drone(ip := os.getenv("DRONE_IP"))
    assert drone.connect(), f"could not connect to '{ip}'"
    frame_reader = DroneFrameReader(drone, logger_dir=Path.cwd() / "logs", metadata_dir=Path.cwd() / "metadata")
    frame_reader.start_streaming()
    while frame_reader.is_streaming:
        time.sleep(1)
        rgb = frame_reader.get_current_frame()
        print(f"RGB: {rgb.shape}")
        cv2.imshow("img", rgb)
        cv2.waitKey(1)

if __name__ == '__main__':
    main()