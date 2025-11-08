#!/usr/bin/env python3
"""keyboard controller and display example with frames of a video not a real or simulated drone"""
# pylint: disable=duplicate-code
from queue import Queue
from datetime import datetime
import sys
import time
import threading
import numpy as np
from vre_video import VREVideo # pylint: disable=import-error

from drone_ioact import DroneIn, Action, ActionsQueue, ActionsProducer
from drone_ioact.data_consumers import ScreenDisplayer, KeyboardController
from drone_ioact.utils import logger

QUEUE_MAX_SIZE = 30

class MyActionsQueue(ActionsQueue):
    """Defines the actions of this video player"""
    def get_actions(self) -> list[Action]:
        return ["DISCONNECT", "PLAY_PAUSE", "SKIP_AHEAD_ONE_SECOND", "GO_BACK_ONE_SECOND"]

class VideoContainer(threading.Thread):
    """This 'acts' as a drone and the only action we can control is the frame number or if it's paused"""
    def __init__(self, video: VREVideo):
        super().__init__()
        self.video = video
        self.frame_ix = 0
        self.is_paused = True
        self.is_done = False
        self.fps = video.fps
        self._current_frame: np.ndarray | None = None
        self._current_frame_lock = threading.Lock()

    def get_current_frame(self) -> np.ndarray:
        """gets the current frame in a thread safe way"""
        with self._current_frame_lock:
            return self._current_frame

    def increment_frame(self, n: int):
        """thread-safe way to increment the frame. Called by the actions maker on key presses"""
        with self._current_frame_lock:
            self.frame_ix = (self.frame_ix + int(n)) % len(self.video)

    def run(self):
        self.is_paused = False
        while not self.is_done:
            now = datetime.now()
            with self._current_frame_lock:
                self._current_frame = self.video[self.frame_ix]
            if not self.is_paused:
                self.increment_frame(n=1)
            if (diff := (1 / self.fps - (datetime.now() - now).total_seconds())) > 0:
                time.sleep(diff)

class VideoFrameReader(DroneIn):
    """VideoFrameReader gets data from a video file"""
    def __init__(self, video: VideoContainer):
        self.video = video

    def get_current_data(self, timeout_s: int = 10) -> dict[str, np.ndarray]:
        return {"rgb": self.video.get_current_frame()}

    def is_streaming(self) -> bool:
        return not self.video.is_done

    def stop_streaming(self):
        self.video.is_done = True

class VideoActionsMaker(ActionsProducer, threading.Thread):
    """VideoActionsMaker defines the actions taken on the video container based on the actions produced"""
    def __init__(self, video: VideoContainer, actions_queue: Queue):
        ActionsProducer.__init__(self, actions_queue)
        threading.Thread.__init__(self)
        self.video = video

    def run(self):
        while True:
            action: Action = self.actions_queue.get()
            logger.debug(f"Received action: '{action}' (#in queue: {len(self.actions_queue)})")
            if action == "DISCONNECT":
                break
            if action == "PLAY_PAUSE":
                self.video.is_paused = not self.video.is_paused
            if action == "SKIP_AHEAD_ONE_SECOND":
                self.video.increment_frame(self.video.fps)
            if action == "GO_BACK_ONE_SECOND":
                self.video.increment_frame(-self.video.fps)

def main():
    """main fn"""
    video = VREVideo(sys.argv[1])
    logger.info(f"Read video: {video}")
    actions_queue = MyActionsQueue(Queue(maxsize=QUEUE_MAX_SIZE))
    (video_container := VideoContainer(video)).start()

    # data producer thread (1) (drone I/O in -> data/RGB out)
    video_frame_reader = VideoFrameReader(video=video_container)
    # data consumer threads (data/RGB in -> I/O out)
    screen_displayer = ScreenDisplayer(drone_in=video_frame_reader)
    # data consumer & actions producer threads (data/RGB in -> action out)
    key_to_action = {"Key.space": "PLAY_PAUSE", "q": "DISCONNECT", "Key.right": "SKIP_AHEAD_ONE_SECOND",
                     "Key.left": "GO_BACK_ONE_SECOND"}
    kb_controller = KeyboardController(drone_in=video_frame_reader, actions_queue=actions_queue,
                                       key_to_action=key_to_action)
    # actions consumer thread (1) (action in -> drone I/O out)
    video_actions_maker = VideoActionsMaker(video=video_container, actions_queue=actions_queue)

    threads: dict[str, threading.Thread] = {
        "Keyboard controller": kb_controller,
        "Screen displayer": screen_displayer,
        "Video actions maker": video_actions_maker,
    }
    [v.start() for v in threads.values()] # start the threads

    while True:
        logger.debug2(f"Queue size: {len(actions_queue)}")
        if any(not v.is_alive() for v in threads.values()) or not video_frame_reader.is_streaming():
            logger.info(f"{video_frame_reader} streaming: {video_frame_reader.is_streaming()}")
            logger.info("\n".join(f"- {k}: {v}" for k, v in threads.items()))
            break
        time.sleep(1)
    video_frame_reader.stop_streaming()

if __name__ == "__main__":
    main()
