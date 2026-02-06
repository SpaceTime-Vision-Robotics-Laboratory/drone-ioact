#!/usr/bin/env python3
"""keyboard controller and display example with frames of a video not a real or simulated drone"""
# pylint: disable=duplicate-code
from __future__ import annotations
from argparse import ArgumentParser, Namespace
from vre_video import VREVideo

from robobase import ActionsQueue, DataChannel, Robot
from roboimpl.envs.video import VideoPlayerEnv, video_action_fn
from roboimpl.controllers import UDPController

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
    actions_queue = ActionsQueue(actions=actions)
    data_channel = DataChannel(supported_types=["rgb", "frame_ix"], eq_fn=lambda a, b: a["frame_ix"] == b["frame_ix"])

    robot = Robot(env=video_player, data_channel=data_channel, actions_queue=actions_queue, action_fn=video_action_fn)
    udp_controller = UDPController(port=args.port, data_channel=data_channel, actions_queue=actions_queue)
    robot.add_controller(udp_controller, name="UDP controller")
    robot.run()

    video_player.close()

if __name__ == "__main__":
    main(get_args())
