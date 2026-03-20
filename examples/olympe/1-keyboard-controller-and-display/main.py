#!/usr/bin/env python3
"""keyboard controller and display example"""
from argparse import ArgumentParser, Namespace
from queue import Queue

from robobase import ActionsQueue, DataChannel, Robot, Action as Act
from roboimpl.envs.olympe import OlympeEnv, olympe_actions_fn, OLYMPE_ACTION_NAMES
from roboimpl.controllers import ScreenDisplayer, Key

QUEUE_MAX_SIZE = 30
RESOLUTION = 480, 640
DT = 0.15

def get_args() -> Namespace:
    """cli args"""
    parser = ArgumentParser()
    parser.add_argument("ip", help="IP for olympe simulator: 10.202.0.1")
    parser.add_argument("--image_size", nargs=2, type=int)
    args = parser.parse_args()
    return args

def main(args: Namespace):
    """main fn"""
    env = OlympeEnv(ip=args.ip, image_size=args.image_size)
    actions_queue = ActionsQueue(action_names=OLYMPE_ACTION_NAMES, queue=Queue(maxsize=QUEUE_MAX_SIZE))
    data_channel = DataChannel(supported_types=env.get_modalities(),
                               eq_fn=lambda a, b: a["metadata"]["time"] == b["metadata"]["time"])

    robot = Robot(env=env, data_channel=data_channel, actions_queue=actions_queue, action_fn=olympe_actions_fn)
    key_to_action = {
        Key.Esc: Act("DISCONNECT"), Key.Space: Act("LIFT"), Key.b: Act("LAND"),
        Key.w: Act("FORWARD", parameters=(50, DT)), Key.a: Act("LEFT", parameters=(50, DT)),
        Key.s: Act("BACKWARD", parameters=(50, DT)), Key.d: Act("RIGHT", parameters=(50, DT)),
        Key.q: Act("ROTATE_LEFT", parameters=(50, DT)), Key.e: Act("ROTATE_RIGHT", parameters=(50, DT)),
        Key.Up: Act("INCREASE_HEIGHT", parameters=(50, DT)), Key.Down: Act("DECREASE_HEIGHT", parameters=(50, DT)),
        Key.PageUp: Act("GIMBAL_UP", parameters=(50, DT)), Key.PageDown: Act("GIMBAL_DOWN", parameters=(50, DT)),
        Key.k: Act("GIMBAL_ABSOLUTE", parameters=(-45, )),
    }
    screen_displayer = ScreenDisplayer(data_channel, actions_queue, key_to_action=key_to_action, resolution=RESOLUTION)
    robot.add_controller(screen_displayer, name="Screen Displayer")
    robot.run()

    data_channel.close()
    env.close()

if __name__ == "__main__":
    main(get_args())
