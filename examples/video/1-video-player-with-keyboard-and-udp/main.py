#!/usr/bin/env python3
"""keyboard controller and display example with frames of a video not a real or simulated drone"""
# pylint: disable=duplicate-code
from __future__ import annotations
from argparse import ArgumentParser, Namespace
from vre_video import VREVideo

from robobase import ActionsQueue, DataChannel, Robot, Action as A
from roboimpl.envs.video import VideoPlayerEnv, video_action_fn, VIDEO_ACTION_NAMES
from roboimpl.controllers import ScreenDisplayer, UDPController

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

    actions_queue = ActionsQueue(action_names=VIDEO_ACTION_NAMES)
    data_channel = DataChannel(supported_types=["rgb", "frame_ix"], eq_fn=lambda a, b: a["frame_ix"] == b["frame_ix"])

    robot = Robot(env=video_player, data_channel=data_channel, actions_queue=actions_queue, action_fn=video_action_fn)
    key_to_action = {"space": A("PLAY_PAUSE"), "Escape": A("DISCONNECT"), "Left": A("GO_BACK", (video_player.fps, )),
                     "Right": A("GO_FORWARD", (video_player.fps, )), "comma": A("GO_BACK", (1, )),
                     "period": A("GO_FORWARD", (1, ))}
    screen_displayer = ScreenDisplayer(data_channel, actions_queue, resolution=DEFAULT_SCREEN_RESOLUTION,
                                       key_to_action=key_to_action)
    udp_controller = UDPController(port=args.port, data_channel=data_channel, actions_queue=actions_queue)
    robot.add_controller(screen_displayer, name="Screen displayer")
    robot.add_controller(udp_controller, name="UDP controller")
    robot.run()

    data_channel.close()
    video_player.close()

if __name__ == "__main__":
    main(get_args())
