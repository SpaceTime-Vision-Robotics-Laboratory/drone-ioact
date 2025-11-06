#!/usr/bin/env python3
import os
import numpy as np
from abc import ABC, abstractmethod
from pathlib import Path
import json
from datetime import datetime
from pynput.keyboard import Listener, KeyCode, Key
from pathlib import Path
from loggez import make_logger
import threading
import time
import cv2
import olympe
from olympe.messages.ardrone3.PilotingState import FlyingStateChanged
from olympe.messages.ardrone3.Piloting import moveBy, Landing, TakeOff

olympe.log.update_config({"loggers": {"olympe": {"level": "CRITICAL"}}})
logger = make_logger("DRONE", log_file=Path.cwd() / f"logs/logs-{datetime.now().isoformat()[0:-6]}.txt")

class DroneIn(ABC):
    @abstractmethod
    def get_current_data(self, timeout_s: int = 10) -> dict[str, np.ndarray]:
        """gets the data (RGB and maybe others) as a dict of numpy arrays"""

    @abstractmethod
    def is_streaming(self) -> bool:
        """checks if the drone is connected and streaming or not"""

    @abstractmethod
    def stop_streaming(self):
        """calls the drone to stop sending messages"""

class DroneFrameReader(DroneIn):
    """
    Handler for drone video streams that processes frames and manages metadata.
    This class handles the streaming of video from a drone, converting frames to OpenCV
    format, and optionally saving metadata associated with the stream.
    """
    SAVE_EVERY_N_METADATA = 100

    def __init__(self, drone: olympe.Drone, 
                 logger_dir: str | Path | None = None, metadata_dir: str | Path | None = None):
        assert drone.connected, f"{drone} is not connected"
        assert drone.streaming is not None, f"{drone} drone.streaming is None"
        self.drone = drone
        logger_dir = Path(logger_dir) / f"{self.__class__.__name__}.log" if logger_dir is not None else None
        self.metadata_dir = Path(metadata_dir) / "metadata.json" if metadata_dir is not None else None

        self._metadata = []
        self._current_frame: np.ndarray | None = None
        self._current_frame_lock = threading.Lock()

        self.drone.streaming.set_callbacks(
            raw_cb=self._yuv_frame_cb,
            start_cb=(lambda _: logger.info("Video stream started.")),
            end_cb=(lambda _: logger.info("Video stream end.")),
            flush_raw_cb=(lambda _: logger.warning("Flush requested for stream. Resetting queue.")),
        )
        logger.info("Starting streaming...")
        self.drone.streaming.start()
        self._is_streaming = True

    def get_current_data(self, timeout_s: int = 10) -> np.ndarray:
        """gets the latest frame processed from the drone stream. Blocks for timeout_s if no frame is available yet."""
        assert self.is_streaming(), f"{self.drone} is not streaming"
        n_tries, sleep_duration = 0, 1
        while self._current_frame is None:
            if n_tries * sleep_duration > timeout_s:
                raise ValueError(f"Waited for {timeout_s} and no frame was produced")
            logger.info("No frame yet... blocking")
            time.sleep(1)
            n_tries += 1
        with self._current_frame_lock:
            return {"rgb": self._current_frame}

    def is_streaming(self) -> bool:
        connected = self.drone.connected
        streaming = self.drone.streaming is not None
        logger.debug(f"Connected: {connected}. Streaming: {streaming}")
        return connected and streaming

    def stop_streaming(self):
        logger.info("Stopping streaming...")
        try:
            self.drone.streaming.stop()
            self._save_metadata()
        except Exception as e:
            logger.error("Unable to properly stop the streaming...")
            logger.critical(e, exc_info=True)

    def _yuv_frame_cb(self, yuv_frame: olympe.VideoFrame):
        """
        This function will be called by Olympe for each decoded YUV frame. It transforms the YUV frame into an OpenCV
        frame, and unrefs the frame.
        """
        if not yuv_frame:
            logger.warning("Received empty frame")
            return

        cv2_cvt_colors = {
            olympe.VDEF_I420: cv2.COLOR_YUV2BGR_I420,
            olympe.VDEF_NV12: cv2.COLOR_YUV2BGR_NV12,
        }

        try:
            with self._current_frame_lock:
                yuv_frame.ref()
                self._current_frame = cv2.cvtColor(yuv_frame.as_ndarray(), cv2_cvt_colors[yuv_frame.format()])
                logger.debug(f"Received a new frame at {datetime.now().isoformat()[0:-6]}. "
                             f"Shape: {self._current_frame.shape}")
                self._prepare_metadata(vmeta_data=yuv_frame.vmeta()[1])
        finally:
            yuv_frame.unref()

    def _prepare_metadata(self, vmeta_data: dict) -> None:
        if self.metadata_dir is None or len(vmeta_data) == 0:
            logger.debug(f"Received empty metadata (len: {len(vmeta_data)} or dir is empty.")
            return

        self._metadata.append({
            "time": datetime.now().isoformat(),
            "drone": vmeta_data["drone"],
            "camera": vmeta_data["camera"],
        })
        if len(self._metadata) >= DroneFrameReader.SAVE_EVERY_N_METADATA:
            self._save_metadata()

    def _save_metadata(self) -> None:
        """Save the current metadata to disk and clear the in-memory list."""
        if self.metadata_dir is None or len(self._metadata) == 0:
            logger.debug("No metadata to save or path non existent.")
            return

        logger.debug2(f"Saving {len(self._metadata)} metadata entries...")
        Path(self.metadata_save_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self.metadata_save_path, "a") as fp:
            fp.write(json.dumps(self._metadata, indent=4))
        self._metadata = []

    def __del__(self):
        self._save_metadata()

class KeyboardController(threading.Thread):
    def __init__(self, drone: olympe.Drone, logger_dir: str | None = None):
        super().__init__()
        logger_dir = Path(logger_dir) / f"{self.__class__.__name__}.log" if logger_dir is not None else None
        self.listener = Listener(on_release=self.on_release)
        self.drone = drone
        self.start()

    def on_release(self, key: KeyCode) -> bool | None:
        res = True
        if key == KeyCode.from_char("T"):
            logger.info("T pressed. Lifting off.")
            res = self.drone(TakeOff()).wait().success()
        elif key == KeyCode.from_char("L"):
            logger.info("L pressed. Landing.")
            res = self.drone(Landing()).wait().success()
        elif key == Key.esc:
            logger.info("ESC pressed. Stopping Keyboard Controller.")
            return False
        elif key == KeyCode.from_char("i"): # forward
            logger.info("i pressed. Moving forward.")
            res = self.drone(
                moveBy(1, 0, 0, 0) >> # (forward, right, down, rotation)
                FlyingStateChanged(state="hovering", _timeout=3)
            ).wait()
        elif key == KeyCode.from_char("k"): # rotate (?)
            logger.info("k pressed. Rotating")
            res = self.drone(
                moveBy(0, 0, 0, 0.2) >> # (forward, right, down, rotation)
                FlyingStateChanged(state="hovering", _timeout=3)
            ).wait()
        else:
            logger.debug(f"Unused char: {key}")
        if not res: logger.info("{key} failed")

    def run(self):
        self.listener.start()
        self.listener.join()

def main():
    drone = olympe.Drone(ip := os.getenv("DRONE_IP"))
    assert drone.connect(), f"could not connect to '{ip}'"
    frame_reader = DroneFrameReader(drone, metadata_dir=Path.cwd() / "metadata")

    kb_controller = KeyboardController(drone=drone)

    prev_frame = None
    while True:
        if not (fr := frame_reader.is_streaming()) or not (kbc := kb_controller.is_alive()):
            logger.info(f"Frame reader={fr}. Keyboard controller={kbc}")
            break
        time.sleep(0.01)
        rgb = frame_reader.get_current_data()["rgb"]
        if prev_frame is None or not np.allclose(prev_frame, rgb):
            cv2.imshow("img", rgb)
            cv2.waitKey(1)
        prev_frame = rgb
    drone.disconnect()

if __name__ == '__main__':
    main()
