"""video_player.py - this acts as a video player that continuously plays the video at the target FPS in real time"""
import threading
from datetime import datetime
import time
import numpy as np
from vre_video import VREVideo

from drone_ioact.utils import logger

class VideoPlayer(threading.Thread):
    """video player implementation. Plays the video and defines the state of it (paused/current frame etc.)"""
    def __init__(self, video: VREVideo):
        threading.Thread.__init__(self, daemon=True)
        self.video = video
        self.fps = video.fps
        # video state
        self.is_paused = False
        self.is_done = False
        self.frame_ix = 0
        self._current_frame: np.ndarray | None = None
        self._current_frame_lock = threading.Lock()

    def increment_frame(self, n: int):
        """thread-safe way to increment the frame. Called by the actions maker on key presses"""
        with self._current_frame_lock:
            self.frame_ix = (self.frame_ix + int(n)) % len(self.video)

    def get_current_frame(self) -> dict[str, np.ndarray]:
        """thread-safe to get the current frame (rgb + frame_ix keys)"""
        with self._current_frame_lock:
            return {"rgb": self._current_frame.copy(), "frame_ix": self.frame_ix}

    def stop_video(self):
        """stops the video playing thread"""
        if self.is_done:
            return
        assert self.is_alive(), "cannot stop the video if it was never started :)"
        self.is_done = True

    def run(self):
        self.is_paused = False
        while not self.is_done:
            try:
                now = datetime.now()
                with self._current_frame_lock:
                    if not self.is_paused:
                        self.frame_ix = (self.frame_ix + 1) % len(self.video)
                    self._current_frame = self.video[self.frame_ix]
                if (diff := (1 / self.fps - (took_s := (datetime.now() - now).total_seconds()))) > 0:
                    time.sleep(diff)
                logger.debug2(f"Frame: {self.frame_ix}. FPS: {self.fps:.2f}. Took: {took_s:.5f}. Diff: {diff:.5f}")
            except Exception as e:
                logger.error(e)
                self.is_done = True
