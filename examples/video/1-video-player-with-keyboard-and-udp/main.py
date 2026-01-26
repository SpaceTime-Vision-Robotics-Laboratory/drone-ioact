#!/usr/bin/env python3
"""keyboard controller and display example with frames of a video not a real or simulated drone"""
# pylint: disable=duplicate-code
from __future__ import annotations
from queue import Queue
from argparse import ArgumentParser, Namespace
import time
from vre_video import VREVideo
from loggez import loggez_logger as logger

from robobase import ActionsQueue, DataChannel, ThreadGroup, DataProducers2Channels, Actions2Robot, RawDataProducer
from roboimpl.drones.video import VideoPlayerEnv, video_action_fn, VIDEO_SUPPORTED_ACTIONS
from roboimpl.controllers import ScreenDisplayer, UDPController

QUEUE_MAX_SIZE = 30
DEFAULT_SCREEN_RESOLUTION = (420, 640)

def get_args() -> Namespace:
    """cli args"""
    parser = ArgumentParser()
    parser.add_argument("video_path")
    parser.add_argument("--port", type=int, default=42069)
    args = parser.parse_args()
    return args

def main(args: Namespace):
    """main fn"""
    (video_player := VideoPlayerEnv(VREVideo(args.video_path))).start() # start the video player

    actions_queue = ActionsQueue(Queue(maxsize=QUEUE_MAX_SIZE), actions=VIDEO_SUPPORTED_ACTIONS)
    data_channel = DataChannel(supported_types=["rgb", "frame_ix"], eq_fn=lambda a, b: a["frame_ix"] == b["frame_ix"])

    # define the threads of the app
    raw_data_producer = RawDataProducer(env=video_player)
    data_producers = DataProducers2Channels(data_channels=[data_channel], data_producers=[raw_data_producer])
    key_to_action = {"space": "PLAY_PAUSE", "q": "DISCONNECT", "Right": "SKIP_AHEAD_ONE_SECOND",
                     "Left": "GO_BACK_ONE_SECOND"}
    screen_displayer = ScreenDisplayer(data_channel, actions_queue, resolution=DEFAULT_SCREEN_RESOLUTION,
                                       key_to_action=key_to_action)
    udp_controller = UDPController(port=args.port, data_channel=data_channel, actions_queue=actions_queue)
    action2video = Actions2Robot(env=video_player, actions_queue=actions_queue, action_fn=video_action_fn)

    # start the threads
    threads = ThreadGroup({
        "Video -> Data": data_producers,
        "Screen displayer": screen_displayer,
        "UDP controller": udp_controller,
        "Action -> Video": action2video,
    }).start()

    while not threads.is_any_dead():
        logger.trace(f"{data_channel}. Actions queue size: {len(actions_queue)}")
        time.sleep(1)

    video_player.stop_video()
    threads.join(timeout=1)

if __name__ == "__main__":
    main(get_args())
