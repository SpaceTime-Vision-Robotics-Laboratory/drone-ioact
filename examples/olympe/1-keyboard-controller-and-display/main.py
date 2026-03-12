#!/usr/bin/env python3
"""keyboard controller and display example"""
import sys
from queue import Queue

from robobase import ActionsQueue, DataChannel, Robot, Action as A
from roboimpl.envs.olympe import OlympeEnv, olympe_actions_fn, OLYMPE_ACTION_NAMES
from roboimpl.controllers import ScreenDisplayer

QUEUE_MAX_SIZE = 30
RESOLUTION = 480, 640
DT = 0.15

def main():
    """main fn"""
    env = OlympeEnv(ip=sys.argv[1])
    actions_queue = ActionsQueue(action_names=OLYMPE_ACTION_NAMES, queue=Queue(maxsize=QUEUE_MAX_SIZE))
    data_channel = DataChannel(supported_types=env.get_modalities(),
                               eq_fn=lambda a, b: a["metadata"]["time"] == b["metadata"]["time"])

    robot = Robot(env=env, data_channel=data_channel, actions_queue=actions_queue, action_fn=olympe_actions_fn)
    key_to_action = {
        "Escape": A("DISCONNECT"), "space": A("LIFT"), "b": A("LAND"),
        "w": A("FORWARD", parameters=(50, DT)), "a": A("LEFT", parameters=(50, DT)),
        "s": A("BACKWARD", parameters=(50, DT)), "d": A("RIGHT", parameters=(50, DT)),
        "q": A("ROTATE_LEFT", parameters=(50, DT)), "e": A("ROTATE_RIGHT", parameters=(50, DT)),
        "Up": A("INCREASE_HEIGHT", parameters=(50, DT)), "Down": A("DECREASE_HEIGHT", parameters=(50, DT)),
        "Prior": A("GIMBAL_UP", parameters=(50, DT)), "Next": A("GIMBAL_DOWN", parameters=(50, DT)),
        "k": A("GIMBAL_ABSOLUTE", parameters=(-45, )),
    }
    screen_displayer = ScreenDisplayer(data_channel, actions_queue, key_to_action=key_to_action, resolution=RESOLUTION)
    robot.add_controller(screen_displayer, name="Screen Displayer")
    robot.run()

    data_channel.close()
    env.close()

if __name__ == "__main__":
    main()
