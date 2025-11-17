#!/usr/bin/env python3
"""keyboard controller and display example with frames of a video + semantic segmentation"""
# pylint: disable=duplicate-code
from __future__ import annotations
from queue import Queue
import sys
import time

from safeuav_semantic_data_producer import SafeUAVSemanticDataProducer, COLOR_MAP
import numpy as np

from drone_ioact import Action, ActionsQueue, ActionsConsumer
from drone_ioact.drones.video import VideoFrameReader
from drone_ioact.data_consumers import ScreenDisplayer, KeyboardController
from drone_ioact.utils import logger, ThreadGroup, colorize_semantic_segmentation

QUEUE_MAX_SIZE = 30
SCREEN_HEIGHT = 480 # width is auto-scaled

class VideoActionsMaker(ActionsConsumer):
    """VideoActionsMaker defines the actions taken on the video container based on the actions produced"""
    def __init__(self, video: VideoFrameReader, actions_queue: Queue):
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

class SemanticScreenDisplayer(ScreenDisplayer):
    """Extends ScreenDisplayer to display semantic segmentation"""
    def __init__(self, *args, color_map: list[tuple[int, int, int]], **kwargs):
        super().__init__(*args, **kwargs)
        assert "semantic" in (st := self.data_producer.get_supported_types()), f"'rgb' not in {st}"
        self.color_map = color_map

    def get_current_frame(self):
        data = self.data_producer.get_current_data()
        rgb, semantic = data["rgb"], data["semantic"]
        sema_rgb = colorize_semantic_segmentation(semantic.argmax(-1), self.color_map).astype(np.uint8)
        combined = np.concatenate([rgb, sema_rgb], axis=1)
        return combined

def main():
    """main fn"""
    # start the video thread immediately so it produces "real time" frames
    (video_frame_reader := VideoFrameReader(video_path=sys.argv[1])).start()
    actions = ["DISCONNECT", "PLAY_PAUSE", "SKIP_AHEAD_ONE_SECOND", "GO_BACK_ONE_SECOND"]
    actions_queue = ActionsQueue(Queue(maxsize=QUEUE_MAX_SIZE), actions=actions)

    # data producer thread (1) (drone I/O in -> data/RGB out)
    semantic_data_producer = SafeUAVSemanticDataProducer(data_producer=video_frame_reader, weights_path=sys.argv[2])
    # data consumer threads (data/RGB in -> I/O out)
    screen_displayer = SemanticScreenDisplayer(data_producer=semantic_data_producer, screen_height=SCREEN_HEIGHT,
                                               color_map=COLOR_MAP)
    # data consumer & actions producer threads (data/RGB in -> action out)
    key_to_action = {"Key.space": "PLAY_PAUSE", "q": "DISCONNECT", "Key.right": "SKIP_AHEAD_ONE_SECOND",
                     "Key.left": "GO_BACK_ONE_SECOND"}
    kb_controller = KeyboardController(data_producer=semantic_data_producer, actions_queue=actions_queue,
                                       key_to_action=key_to_action)
    # actions consumer thread (1) (action in -> drone I/O out)
    video_actions_maker = VideoActionsMaker(video=video_frame_reader, actions_queue=actions_queue)

    threads = ThreadGroup({
        "Keyboard controller": kb_controller,
        "Screen displayer": screen_displayer,
        "Video actions maker": video_actions_maker,
    })
    threads.start()

    while semantic_data_producer.is_streaming() and not threads.is_any_dead():
        logger.debug2(f"Queue size: {len(actions_queue)}")
        time.sleep(1)

    video_actions_maker.stop_streaming()
    threads.join(timeout=1)

if __name__ == "__main__":
    main()
