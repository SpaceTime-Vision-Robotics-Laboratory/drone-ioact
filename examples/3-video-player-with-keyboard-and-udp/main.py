#!/usr/bin/env python3
"""keyboard controller and display example with frames of a video not a real or simulated drone"""
# pylint: disable=duplicate-code
from __future__ import annotations
from queue import Queue
from pathlib import Path
from argparse import ArgumentParser, Namespace
import time
from vre_video import VREVideo

from drone_ioact import Action, ActionsQueue, DataChannel
from drone_ioact.drones.video import VideoPlayer, VideoActionsConsumer, VideoDataProducer
from drone_ioact.data_consumers import ScreenDisplayer, KeyboardController, UDPController
from drone_ioact.utils import logger, ThreadGroup, image_write

QUEUE_MAX_SIZE = 30
SCREEN_HEIGHT = 420

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
    parser.add_argument("--port", type=int, default=42069)
    args = parser.parse_args()
    return args

def main(args: Namespace):
    """main fn"""
    (video_player := VideoPlayer(VREVideo(args.video_path))).start() # start the video player

    actions = ["DISCONNECT", "PLAY_PAUSE", "SKIP_AHEAD_ONE_SECOND", "GO_BACK_ONE_SECOND", "TAKE_SCREENSHOT"]
    actions_queue = ActionsQueue(Queue(maxsize=QUEUE_MAX_SIZE), actions=actions)
    data_channel = DataChannel(supported_types=["rgb", "frame_ix"], eq_fn=lambda a, b: a["frame_ix"] == b["frame_ix"])

    # define the threads of the app
    video_data_producer = VideoDataProducer(video_player=video_player, data_channel=data_channel)
    screen_displayer = ScreenDisplayer(data_channel=data_channel, screen_height=SCREEN_HEIGHT)
    key_to_action = {"Key.space": "PLAY_PAUSE", "q": "DISCONNECT", "Key.right": "SKIP_AHEAD_ONE_SECOND",
                     "Key.left": "GO_BACK_ONE_SECOND"}
    kb_controller = KeyboardController(data_channel=data_channel, actions_queue=actions_queue,
                                       key_to_action=key_to_action)
    udp_controller = UDPController(port=args.port, data_channel=data_channel, actions_queue=actions_queue)
    video_actions_consumer = VideoActionsConsumer(video_player=video_player, actions_queue=actions_queue,
                                                  actions_callback=video_actions_callback)

    # start the threads
    threads = ThreadGroup({
        "Video data producer": video_data_producer,
        "Screen displayer": screen_displayer,
        "Keyboard controller": kb_controller,
        "UDP controller": udp_controller,
        "Video actions consumer": video_actions_consumer,
    }).start()

    while not threads.is_any_dead():
        logger.debug2(f"{data_channel}. Actions queue size: {len(actions_queue)}")
        time.sleep(1)

    video_player.stop_video()
    threads.join(timeout=1)

if __name__ == "__main__":
    main(get_args())
