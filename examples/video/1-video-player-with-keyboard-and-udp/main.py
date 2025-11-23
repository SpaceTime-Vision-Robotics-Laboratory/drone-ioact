#!/usr/bin/env python3
"""keyboard controller and display example with frames of a video not a real or simulated drone"""
# pylint: disable=duplicate-code
from __future__ import annotations
from queue import Queue
from argparse import ArgumentParser, Namespace
import time
from vre_video import VREVideo

from drone_ioact import ActionsQueue, DataChannel
from drone_ioact.drones.video import (
    VideoPlayer, VideoActionsConsumer, VideoDataProducer, video_actions_callback, VIDEO_SUPPORTED_ACTIONS)
from drone_ioact.data_consumers import ScreenDisplayer, UDPController
from drone_ioact.utils import logger, ThreadGroup

QUEUE_MAX_SIZE = 30
SCREEN_HEIGHT = 420

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

    actions_queue = ActionsQueue(Queue(maxsize=QUEUE_MAX_SIZE), actions=VIDEO_SUPPORTED_ACTIONS)
    data_channel = DataChannel(supported_types=["rgb", "frame_ix"], eq_fn=lambda a, b: a["frame_ix"] == b["frame_ix"])

    # define the threads of the app
    video_data_producer = VideoDataProducer(video_player=video_player, data_channel=data_channel)
    key_to_action = {"space": "PLAY_PAUSE", "q": "DISCONNECT", "Right": "SKIP_AHEAD_ONE_SECOND",
                     "Left": "GO_BACK_ONE_SECOND"}
    screen_displayer = ScreenDisplayer(data_channel, actions_queue, screen_height=SCREEN_HEIGHT,
                                       key_to_action=key_to_action)
    udp_controller = UDPController(port=args.port, data_channel=data_channel, actions_queue=actions_queue)
    video_actions_consumer = VideoActionsConsumer(video_player=video_player, actions_queue=actions_queue,
                                                  actions_callback=video_actions_callback)

    # start the threads
    threads = ThreadGroup({
        "Video data producer": video_data_producer,
        "Screen displayer": screen_displayer,
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
