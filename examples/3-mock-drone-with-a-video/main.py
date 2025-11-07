#!/usr/bin/env python3
"""keyboard controller and display example with frames of a video not a real or simulated drone"""
# pylint: disable=duplicate-code
from queue import Queue
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

class VideoWithFrames(VREVideo):
    """This 'acts' as a drone and the only action we can control is the frame number"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.frame_ix = 0
        self.is_paused = False

class VideoFrameReader(DroneIn):
    """VideoFrameReader gets data from a video file"""
    def __init__(self, video: VideoWithFrames):
        self.video = video
        self._is_streaming = True

    def get_current_data(self, timeout_s: int = 10) -> dict[str, np.ndarray]:
        data = self.video[self.video.frame_ix]
        # TODO: kinda hacky that the data receiver appends this
        if not self.video.is_paused:
            self.video.frame_ix = (self.video.frame_ix + 1) % len(self.video)
        return {"rgb": data}

    def is_streaming(self) -> bool:
        return self._is_streaming

    def stop_streaming(self):
        self._is_streaming = False

class VideoActionsMaker(ActionsProducer, threading.Thread):
    """VideoActionsMaker defines the actions taken on the video container based on the actions produced"""
    def __init__(self, video: VideoWithFrames, actions_queue: Queue):
        ActionsProducer.__init__(self, actions_queue)
        threading.Thread.__init__(self)
        self.video = video

    def run(self):
        while True:
            item: Action = self.actions_queue.get()
            if item == "DISCONNECT":
                break
            if item == "PLAY_PAUSE":
                self.video.is_paused = not self.video.is_paused
            if item == "SKIP_AHEAD_ONE_SECOND":
                self.video.frame_ix = int(self.video.frame_ix + self.video.fps) % len(self.video)
            if item == "GO_BACK_ONE_SECOND":
                self.video.frame_ix = int(self.video.frame_ix - self.video.fps) % len(self.video)

def main():
    """main fn"""
    video = VideoWithFrames(sys.argv[1])
    logger.info(f"Read video: {video}")
    actions_queue = MyActionsQueue(Queue(maxsize=QUEUE_MAX_SIZE))

    # data producer thread (1) (drone I/O in -> data/RGB out)
    video_frame_reader = VideoFrameReader(video=video)
    # data consumer threads (data/RGB in -> I/O out)
    screen_displayer = ScreenDisplayer(drone_in=video_frame_reader)
    # data consumer & actions producer threads (data/RGB in -> action out)
    key_to_action = {"Key.space": "PLAY_PAUSE", "q": "DISCONNECT", "Key.right": "SKIP_AHEAD_ONE_SECOND",
                     "Key.left": "GO_BACK_ONE_SECOND"}
    kb_controller = KeyboardController(drone_in=video_frame_reader, actions_queue=actions_queue,
                                       key_to_action=key_to_action)
    # actions consumer thread (1) (action in -> drone I/O out)
    video_actions_maker = VideoActionsMaker(video=video, actions_queue=actions_queue)

    threads: dict[str, threading.Thread] = {
        "Keyboard controller": kb_controller,
        "Screen displayer": screen_displayer,
        "Video actions maker": video_actions_maker,
    }
    [v.start() for v in threads.values()] # start the threads

    while True:
        logger.debug2(f"Queue size: {len(actions_queue)}")
        if any(not v.is_alive() for v in threads.values()) or not video_frame_reader.is_streaming():
            logger.info(f"{video_frame_reader} streaming:. {video_frame_reader.is_streaming()}")
            logger.info("\n".join(f"- {k}: {v}" for k, v in threads.items()))
            break
        time.sleep(1)
    video_frame_reader.stop_streaming()

if __name__ == "__main__":
    main()
