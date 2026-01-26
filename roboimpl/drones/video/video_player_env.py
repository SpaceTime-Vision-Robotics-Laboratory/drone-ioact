"""video_player.py - this acts as a video player that continuously plays the video at the target FPS in real time"""
import threading
from datetime import datetime
import traceback
import numpy as np
from overrides import overrides
from vre_video import VREVideo

from robobase import Environment
from roboimpl.utils import logger

class VideoPlayerEnv(threading.Thread, Environment):
    """video player implementation. Plays the video and defines the state of it (paused/current frame etc.)"""
    def __init__(self, video: VREVideo, loop: bool=True):
        threading.Thread.__init__(self, daemon=True)
        Environment.__init__(self, frequency=video.fps)
        self.video = video
        self.loop = loop # if set to true, it will endlessly run, otherwise it stops after the video ends.
        self.fps = video.fps
        # video state
        self.is_paused = False
        self.is_done = False
        self.frame_ix = 0
        self._current_frame: np.ndarray | None = None
        self._current_frame_lock = threading.Lock()

    @overrides
    def get_state(self) -> dict[str, np.ndarray | int]:
        """thread-safe to get the current frame (rgb + frame_ix keys)"""
        with self._current_frame_lock:
            return {"rgb": self._current_frame.copy(), "frame_ix": self.frame_ix}

    @overrides
    def is_running(self) -> bool:
        return not self.is_done and self.is_alive()

    @overrides
    def get_modalities(self) -> list[str]:
        return ["rgb", "frame_ix"]

    @overrides
    def run(self):
        self.is_paused = self.is_paused
        while not self.is_done:
            try:
                now = datetime.now()
                with self._current_frame_lock:
                    if not self.is_paused:
                        self.frame_ix = self.frame_ix + 1
                        if self.frame_ix >= len(self.video) and not self.loop:
                            self.is_done = True
                        self.frame_ix = self.frame_ix % len(self.video)
                    self._current_frame = self.video[self.frame_ix]
                self.freq_barrier()
                took_s = (datetime.now() - now).total_seconds()
                logger.trace(f"Frame: {self.frame_ix}. FPS: {self.fps:.2f}. Took: {took_s:.5f}")
            except Exception as e:
                logger.error(f"Error {e}\nTraceback: {traceback.format_exc()}")
                self.is_done = True

    def increment_frame(self, n: int):
        """thread-safe way to increment the frame. Called by the actions maker on key presses"""
        with self._current_frame_lock:
            self.frame_ix = (self.frame_ix + int(n)) % len(self.video)

    def stop_video(self):
        """stops the video playing thread"""
        if self.is_done:
            return
        assert self.is_alive(), "cannot stop the video if it was never started :)"
        self.is_done = True

    def __repr__(self):
        return f"[VideoPlayerEnv] {repr(self.video)}"
