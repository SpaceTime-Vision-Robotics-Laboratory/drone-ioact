#!/usr/bin/env python3
"""keyboard controller and display example with frames of a video not a real or simulated drone"""
# pylint: disable=duplicate-code
from __future__ import annotations
from queue import Queue
import sys
import time
import numpy as np

from video_container import VideoContainer

from drone_ioact import DataProducer, Action, ActionsQueue, ActionsConsumer
from drone_ioact.data_consumers import ScreenDisplayer, KeyboardController
from drone_ioact.utils import logger, ThreadGroup

QUEUE_MAX_SIZE = 30
SCREEN_HEIGHT = 402

class VideoFrameReader(DataProducer):
    """VideoFrameReader gets data from a video container (producing frames in real time)"""
    def __init__(self, video: VideoContainer):
        self.video = video

    def get_current_data(self, timeout_s: int = 10) -> dict[str, np.ndarray]:
        return {"rgb": self.video.get_current_frame()}

    def is_streaming(self) -> bool:
        return not self.video.is_done

class VideoActionsMaker(ActionsConsumer):
    """VideoActionsMaker defines the actions taken on the video container based on the actions produced"""
    def __init__(self, video: VideoContainer, actions_queue: Queue):
        super().__init__(actions_queue, VideoActionsMaker.video_action_callback)
        self.video = video

    def stop_streaming(self):
        self.video.is_done = True

    def is_streaming(self) -> bool:
        return not self.video.is_done

    @staticmethod
    def video_action_callback(actions_maker: VideoActionsMaker, action: Action) -> bool:
        """the actions callback from generic actions to video-specific ones"""
        if action == "DISCONNECT":
            actions_maker.stop_streaming()
        if action == "PLAY_PAUSE":
            actions_maker.video.is_paused = not actions_maker.video.is_paused
        if action == "SKIP_AHEAD_ONE_SECOND":
            actions_maker.video.increment_frame(actions_maker.video.fps)
        if action == "GO_BACK_ONE_SECOND":
            actions_maker.video.increment_frame(-actions_maker.video.fps)
        return True

def main():
    """main fn"""
    (video_container := VideoContainer(sys.argv[1])).start() # start the video thread so it produces "real time" frames
    actions = ["DISCONNECT", "PLAY_PAUSE", "SKIP_AHEAD_ONE_SECOND", "GO_BACK_ONE_SECOND"]
    actions_queue = ActionsQueue(Queue(maxsize=QUEUE_MAX_SIZE), actions=actions)

    # data producer thread (1) (drone I/O in -> data/RGB out)
    video_frame_reader = VideoFrameReader(video=video_container)
    # data consumer threads (data/RGB in -> I/O out)
    screen_displayer = ScreenDisplayer(data_producer=video_frame_reader, screen_height=SCREEN_HEIGHT)
    # data consumer & actions producer threads (data/RGB in -> action out)
    key_to_action = {"Key.space": "PLAY_PAUSE", "q": "DISCONNECT", "Key.right": "SKIP_AHEAD_ONE_SECOND",
                     "Key.left": "GO_BACK_ONE_SECOND"}
    kb_controller = KeyboardController(data_producer=video_frame_reader, actions_queue=actions_queue,
                                       key_to_action=key_to_action)
    # actions consumer thread (1) (action in -> drone I/O out)
    video_actions_maker = VideoActionsMaker(video=video_container, actions_queue=actions_queue)

    threads = ThreadGroup({
        "Keyboard controller": kb_controller,
        "Screen displayer": screen_displayer,
        "Video actions maker": video_actions_maker,
    })
    threads.start()

    while video_frame_reader.is_streaming() and not threads.is_any_dead():
        logger.debug2(f"Queue size: {len(actions_queue)}")
        time.sleep(1)

    video_actions_maker.stop_streaming()
    threads.join(timeout=1)

if __name__ == "__main__":
    main()
