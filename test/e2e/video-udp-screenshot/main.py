#!/usr/bin/env python3
"""keyboard controller and display example with frames of a video not a real or simulated drone"""
# pylint: disable=duplicate-code
from __future__ import annotations
from queue import Queue
from pathlib import Path
from argparse import ArgumentParser, Namespace
import time
from vre_video import VREVideo

from robobase import Action, ActionsQueue, DataChannel, DataProducerList
from robobase.utils import logger, ThreadGroup
from roboimpl.drones.video import VideoPlayer, VideoActionsConsumer, VideoDataProducer, video_actions_callback
from roboimpl.data_consumers import UDPController
from roboimpl.utils import image_write

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

    actions = ["DISCONNECT", "PLAY_PAUSE", "SKIP_AHEAD_ONE_SECOND", "GO_BACK_ONE_SECOND", "TAKE_SCREENSHOT"]
    actions_queue = ActionsQueue(Queue(maxsize=QUEUE_MAX_SIZE), actions=actions)
    data_channel = DataChannel(supported_types=["rgb", "frame_ix"], eq_fn=lambda a, b: a["frame_ix"] == b["frame_ix"])

    # define the threads of the app
    data_producers = DataProducerList(data_channel, data_producers=[VideoDataProducer(video_player=video_player)])
    udp_controller = UDPController(port=args.port, data_channel=data_channel, actions_queue=actions_queue)
    video_actions_consumer = VideoActionsConsumer(video_player=video_player, actions_queue=actions_queue,
                                                  actions_callback=video_actions_callback, write_path=Path.cwd())

    # start the threads
    threads = ThreadGroup({
        "Data producer": data_producers,
        "UDP controller": udp_controller,
        "Video actions consumer": video_actions_consumer,
    }).start()

    while not video_player.is_done and not threads.is_any_dead():
        logger.trace(f"Data channel: {data_channel}. Actions queue size: {len(actions_queue)}")
        time.sleep(1)

    video_player.stop_video()
    threads.join(timeout=1)

if __name__ == "__main__":
    main(get_args())
