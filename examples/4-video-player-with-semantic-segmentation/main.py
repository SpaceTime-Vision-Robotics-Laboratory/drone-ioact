#!/usr/bin/env python3
"""keyboard controller and display example with frames of a video + semantic segmentation"""
# pylint: disable=duplicate-code
from queue import Queue
import sys
import time
import threading
import cv2
import numpy as np

from drone_ioact import Action, ActionsQueue, ActionsProducer
from drone_ioact.data_consumers import ScreenDisplayer, KeyboardController
from drone_ioact.utils import logger

from video_container import VideoContainer
from semantic_data_producer import SemanticDataProducer, colorize_semantic_segmentation

QUEUE_MAX_SIZE = 30

class MyActionsQueue(ActionsQueue):
    """Defines the actions of this video player"""
    def get_actions(self) -> list[Action]:
        return ["DISCONNECT", "PLAY_PAUSE", "SKIP_AHEAD_ONE_SECOND", "GO_BACK_ONE_SECOND"]

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

class SemanticScreenDisplayer(ScreenDisplayer):
    def run(self):
        prev_frame = None
        while self.drone_in.is_streaming():
            data = self.drone_in.get_current_data()
            rgb, semantic = data["rgb"], data["semantic"]
            if prev_frame is None or not np.allclose(prev_frame, rgb):
                sema_rgb = colorize_semantic_segmentation(semantic.argmax(-1)).astype(np.uint8)
                combined = np.concatenate([rgb, sema_rgb], axis=1)
                aspect_ratio = combined.shape[1] / combined.shape[0]
                w = int(self.h / aspect_ratio)
                combined = cv2.resize(combined, (self.h, w)) if self.h is not None else combined
                cv2.imshow("img", cv2.cvtColor(combined, cv2.COLOR_RGB2BGR))
                cv2.waitKey(1)
            prev_frame = rgb
        logger.warning("ScreenDisplayer thread stopping")


def main():
    """main fn"""
    # start the video thread immediately so it produces "real time" frames
    (video_container := VideoContainer(video_path=sys.argv[1])).start()
    actions_queue = MyActionsQueue(Queue(maxsize=QUEUE_MAX_SIZE))

    # data producer thread (1) (drone I/O in -> data/RGB out)
    video_frame_reader = SemanticDataProducer(video=video_container, weights_path=sys.argv[2])
    # data consumer threads (data/RGB in -> I/O out)
    screen_displayer = SemanticScreenDisplayer(drone_in=video_frame_reader, screen_height=720)
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
