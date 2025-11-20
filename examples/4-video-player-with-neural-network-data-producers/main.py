#!/usr/bin/env python3
"""keyboard controller and display example with frames of a video + semantic segmentation"""
# pylint: disable=duplicate-code
from __future__ import annotations
from queue import Queue
from pathlib import Path
from functools import partial
from argparse import ArgumentParser, Namespace
import time
from vre_video import VREVideo
import numpy as np

from drone_ioact.data_producers.semantic_segmentation import PHGMAESemanticDataProducer

from drone_ioact import Action, ActionsQueue, DataChannel, DataItem
from drone_ioact.drones.video import VideoPlayer, VideoActionsConsumer, VideoDataProducer
from drone_ioact.data_consumers import ScreenDisplayer, KeyboardController
from drone_ioact.utils import logger, ThreadGroup, image_write, colorize_semantic_segmentation

QUEUE_MAX_SIZE = 30
SCREEN_HEIGHT = 480 # width is auto-scaled

def screen_frame_semantic(data: DataItem, color_map: list[tuple[int, int, int]]) -> np.ndarray:
    """produces RGB + semantic segmentation as a single frame"""
    sema_rgb = colorize_semantic_segmentation(data["semantic"].argmax(-1), color_map).astype(np.uint8)
    combined = np.concatenate([data["rgb"], sema_rgb], axis=1)
    return combined

def video_actions_callback(actions_maker: VideoActionsConsumer, action: Action) -> bool:
    """the actions callback from generic actions to video-specific ones"""
    video_player = actions_maker.video_player
    if action == "DISCONNECT":
        video_player.stop_video()
    if action == "PLAY_PAUSE":
        video_player.is_paused = not video_player.is_paused
    if action == "SKIP_AHEAD_ONE_SECOND":
        video_player.increment_frame(video_player.fps)
    if action == "GO_BACK_ONE_SECOND":
        video_player.increment_frame(-video_player.fps)
    if action == "TAKE_SCREENSHOT":
        image_write(video_player.get_current_frame()["rgb"], pth := f"{Path.cwd()}/frame.png")
        logger.debug(f"Stored screenshot at '{pth}'")
    return True

def get_args() -> Namespace:
    """cli args"""
    parser = ArgumentParser()
    parser.add_argument("video_path")
    parser.add_argument("weights_path")
    args = parser.parse_args()
    return args

def main(args: Namespace):
    """main fn"""
    (video_player := VideoPlayer(VREVideo(args.video_path))).start() # start the video player

    actions = ["DISCONNECT", "PLAY_PAUSE", "SKIP_AHEAD_ONE_SECOND", "GO_BACK_ONE_SECOND", "TAKE_SCREENSHOT"]
    actions_queue = ActionsQueue(Queue(maxsize=QUEUE_MAX_SIZE), actions=actions)
    data_channel = DataChannel(supported_types=["rgb", "frame_ix", "semantic"],
                               eq_fn=lambda a, b: a["frame_ix"] == b["frame_ix"])

    # define the threads of the app
    video_data_producer = VideoDataProducer(video_player=video_player, data_channel=data_channel)
    semantic_data_producer = PHGMAESemanticDataProducer(rgb_data_producer=video_data_producer,
                                                         weights_path=args.weights_path)
    screen_frame_callback = partial(screen_frame_semantic, color_map=PHGMAESemanticDataProducer.COLOR_MAP)
    semantic_screen_displayer = ScreenDisplayer(data_channel=data_channel, screen_height=SCREEN_HEIGHT,
                                                screen_frame_callback=screen_frame_callback)
    key_to_action = {"Key.space": "PLAY_PAUSE", "q": "DISCONNECT", "Key.right": "SKIP_AHEAD_ONE_SECOND",
                     "Key.left": "GO_BACK_ONE_SECOND"}
    kb_controller = KeyboardController(data_channel=data_channel, actions_queue=actions_queue,
                                       key_to_action=key_to_action)
    video_actions_consumer = VideoActionsConsumer(video_player=video_player, actions_queue=actions_queue,
                                                  actions_callback=video_actions_callback)

    # start the threads
    threads = ThreadGroup({
        "Semantic data producer": semantic_data_producer,
        "Semantic screen displayer": semantic_screen_displayer,
        "Keyboard controller": kb_controller,
        "Video actions consumer": video_actions_consumer,
    }).start()

    while not threads.is_any_dead():
        logger.debug2(f"{data_channel}. Actions queue size: {len(actions_queue)}")
        time.sleep(1)

    video_player.stop_video()
    threads.join(timeout=1)

if __name__ == "__main__":
    main(get_args())
