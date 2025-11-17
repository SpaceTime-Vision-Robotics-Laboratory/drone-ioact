"""video_frame_reader.py acts as a drone producing frames in real time"""
# pylint: disable=duplicate-code
from datetime import datetime
import threading
import time
from overrides import overrides
import numpy as np
from vre_video import VREVideo # pylint: disable=import-error

from drone_ioact import DataProducer
from drone_ioact.utils import logger

class VideoFrameReader(DataProducer, threading.Thread):
    """This 'acts' as a drone and the only action we can control is the frame number or if it's paused"""
    def __init__(self, video_path: str):
        super().__init__()
        self.video = VREVideo(video_path)
        logger.info(f"Read video: {self.video}")
        self.frame_ix = 0
        self.is_paused = True
        self.is_done = False
        self.fps = self.video.fps
        self._current_frame: np.ndarray | None = None
        self._current_frame_lock = threading.Lock()

    @overrides
    def get_current_data(self, timeout_s: int = 10) -> dict[str, np.ndarray]:
        with self._current_frame_lock:
            return {"rgb": self._current_frame}

    @overrides
    def is_streaming(self) -> bool:
        return not self.is_done

    def get_supported_types(self) -> list[str]:
        return ["rgb"]

    def increment_frame(self, n: int):
        """thread-safe way to increment the frame. Called by the actions maker on key presses"""
        with self._current_frame_lock:
            self.frame_ix = (self.frame_ix + int(n)) % len(self.video)

    def run(self):
        self.is_paused = False
        while self.is_streaming():
            try:
                now = datetime.now()
                with self._current_frame_lock:
                    self._current_frame = self.video[self.frame_ix]
                if not self.is_paused:
                    self.increment_frame(n=1)
                if (diff := (1 / self.fps - (took_s := (datetime.now() - now).total_seconds()))) > 0:
                    time.sleep(diff)
                logger.debug2(f"Frame: {self.frame_ix}. FPS: {self.fps:.2f}. Took: {took_s:.5f}. Diff: {diff:.5f}")
            except Exception as e:
                logger.error(e)
                self.is_done = True
