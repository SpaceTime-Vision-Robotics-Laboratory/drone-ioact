"""olympe_data_producer.py - Data producer for an olympe drone."""
# TODO: refactor this as olympe environment.
from datetime import datetime
import threading
import time
from overrides import overrides
import numpy as np
import cv2
import olympe
from olympe.video.pdraw import PdrawState

from robobase import DataProducer, DataItem
from roboimpl.utils import logger

class OlympeDataProducer(DataProducer):
    """
    Handler for drone video streams that processes frames and manages metadata.
    This class handles the streaming of video from a drone, converting frames to OpenCV
    format, and optionally saving metadata associated with the stream.
    """
    SAVE_EVERY_N_METADATA = 100
    WAIT_FOR_DATA_SECONDS = 5

    def __init__(self, drone: olympe.Drone):
        super().__init__(modalities=["rgb", "metadata"])
        assert drone.connected, f"{drone} is not connected"
        assert drone.streaming is not None, f"{drone} drone.streaming is None"
        self.drone = drone

        self._current_frame: np.ndarray | None = None
        self._current_metadata: dict | None = None
        self._current_frame_lock = threading.Lock()

        self.drone.streaming.set_callbacks(
            raw_cb=self._yuv_frame_cb,
            start_cb=(lambda _: logger.info("Video stream started.")),
            end_cb=(lambda _: logger.info("Video stream end.")),
            flush_raw_cb=(lambda _: logger.warning("Flush requested for stream. Resetting queue.")),
        )
        assert self.drone.streaming.start(), "error starting stream"
        logger.info("Starting streaming...")

    @overrides
    def produce(self, deps: dict[str, DataItem] | None = None) -> dict[str, DataItem]:
        """gets the latest frame processed from the drone stream. Blocks for timeout_s if no frame is available yet."""
        assert (A := self.drone.connected) and (B := self.drone.streaming.state == PdrawState.Playing), (A, B)
        self._wait_for_data()
        with self._current_frame_lock:
            return {"rgb": self._current_frame, "metadata": self._current_metadata}

    def _wait_for_data(self):
        """wait for data at the beginning before anything was sent by the parrot drone"""
        n_tries = 0
        while self._current_frame is None:
            time.sleep(1)
            n_tries += 1
            if n_tries > OlympeDataProducer.WAIT_FOR_DATA_SECONDS:
                raise ValueError(f"no data produced for {OlympeDataProducer.WAIT_FOR_DATA_SECONDS} seconds")

    def _yuv_frame_cb(self, yuv_frame: olympe.VideoFrame):
        """
        This function will be called by Olympe for each decoded YUV frame. It transforms the YUV frame into an OpenCV
        frame, and unrefs the frame.
        """
        if not yuv_frame:
            logger.warning("Received empty frame")
            return

        cv2_cvt_colors = {
            olympe.VDEF_I420: cv2.COLOR_YUV2RGB_I420,
            olympe.VDEF_NV12: cv2.COLOR_YUV2RGB_NV12,
        }

        try:
            with self._current_frame_lock:
                yuv_frame.ref()
                self._current_frame = cv2.cvtColor(yuv_frame.as_ndarray(), cv2_cvt_colors[yuv_frame.format()])
                now = datetime.now().isoformat()
                logger.trace(f"Received a new frame at {now}. Shape: {self._current_frame.shape}")
                self._current_metadata = {
                    "time": now,
                    "drone": yuv_frame.vmeta()[1]["drone"],
                    "camera": yuv_frame.vmeta()[1]["camera"],
                }
        finally:
            yuv_frame.unref()
