#!/usr/bin/env python3
"""keyboard controller and display example with frames of a video not a real or simulated drone"""
# pylint: disable=duplicate-code
from __future__ import annotations
from queue import Queue
from functools import partial
from argparse import ArgumentParser, Namespace
import time
from vre_video import VREVideo

from robobase import ActionsQueue, DataChannel, DataProducers2Channels, Actions2Robot, LambdaDataProducer
from robobase.utils import logger, ThreadGroup
from roboimpl.drones.video import VideoPlayerEnv, video_actions_fn
from roboimpl.controllers import UDPController

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
    (video_player := VideoPlayerEnv(VREVideo(args.video_path))).start() # start the video player

    actions = ["DISCONNECT", "PLAY_PAUSE", "SKIP_AHEAD_ONE_SECOND", "GO_BACK_ONE_SECOND", "TAKE_SCREENSHOT"]
    actions_queue = ActionsQueue(Queue(maxsize=QUEUE_MAX_SIZE), actions=actions)
    data_channel = DataChannel(supported_types=["rgb", "frame_ix"], eq_fn=lambda a, b: a["frame_ix"] == b["frame_ix"])

    # define the threads of the app
    video_dp = LambdaDataProducer(lambda deps: video_player.get_state(), modalities=["rgb", "frame_ix"])
    video2data = DataProducers2Channels(data_channels=[data_channel], data_producers=[video_dp])
    udp_controller = UDPController(port=args.port, data_channel=data_channel, actions_queue=actions_queue)
    action2video = Actions2Robot(actions_queue=actions_queue, termination_fn=lambda: video_player.is_done,
                                 action_fn=partial(video_actions_fn, video_player=video_player))

    # start the threads
    threads = ThreadGroup({
        "Video -> Data": video2data,
        "UDP controller": udp_controller,
        "Action -> Video": action2video,
    }).start()

    while not video_player.is_done and not threads.is_any_dead():
        logger.trace(f"\n-{data_channel}\n-{actions_queue}")
        time.sleep(1)

    video_player.stop_video()
    threads.join(timeout=1)

if __name__ == "__main__":
    main(get_args())
