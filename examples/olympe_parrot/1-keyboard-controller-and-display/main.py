#!/usr/bin/env python3
"""keyboard controller and display example"""
import sys
from queue import Queue

from robobase import ActionsQueue, DataChannel, Robot
from roboimpl.envs.olympe_parrot import OlympeEnv, olympe_actions_fn, OLYMPE_SUPPORTED_ACTIONS
from roboimpl.controllers import ScreenDisplayer

QUEUE_MAX_SIZE = 30
RESOLUTION = 480, 640

def main():
    """main fn"""
    env = OlympeEnv(ip=sys.argv[1])
    actions_queue = ActionsQueue(actions=OLYMPE_SUPPORTED_ACTIONS, queue=Queue(maxsize=QUEUE_MAX_SIZE))
    data_channel = DataChannel(supported_types=["rgb", "metadata"],
                               eq_fn=lambda a, b: a["metadata"]["time"] == b["metadata"]["time"])

    robot = Robot(env=env, data_channel=data_channel, actions_queue=actions_queue, action_fn=olympe_actions_fn)
    key_to_action = {
        "Escape": "DISCONNECT", "space": "LIFT", "b": "LAND",
        "w": "FORWARD", "a": "LEFT", "s": "BACKWARD", "d": "RIGHT", "q": "ROTATE_LEFT", "e": "ROTATE_RIGHT",
        "Up": "INCREASE_HEIGHT", "Down": "DECREASE_HEIGHT", "Next": "TILT_DOWN", "Prior": "TILT_UP"
    }
    screen_displayer = ScreenDisplayer(data_channel, actions_queue, key_to_action=key_to_action, resolution=RESOLUTION)
    robot.add_controller(screen_displayer, name="Screen Displayer")
    robot.run()

    data_channel.close()
    env.close()

if __name__ == "__main__":
    main()
