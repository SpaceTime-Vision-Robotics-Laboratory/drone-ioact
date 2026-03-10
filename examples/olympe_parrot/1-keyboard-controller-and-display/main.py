#!/usr/bin/env python3
"""keyboard controller and display example"""
import sys
from queue import Queue

from robobase import ActionsQueue, DataChannel, Robot, Action
from roboimpl.envs.olympe_parrot import OlympeEnv, olympe_actions_fn, OLYMPE_SUPPORTED_ACTIONS
from roboimpl.controllers import ScreenDisplayer

QUEUE_MAX_SIZE = 30
RESOLUTION = 480, 640
DT = 0.15

def main():
    """main fn"""
    env = OlympeEnv(ip=sys.argv[1])
    actions_queue = ActionsQueue(actions=OLYMPE_SUPPORTED_ACTIONS, queue=Queue(maxsize=QUEUE_MAX_SIZE))
    data_channel = DataChannel(supported_types=env.get_modalities(),
                               eq_fn=lambda a, b: a["metadata"]["time"] == b["metadata"]["time"])

    robot = Robot(env=env, data_channel=data_channel, actions_queue=actions_queue, action_fn=olympe_actions_fn)
    key_to_action = {
        "Escape": "DISCONNECT", "space": "LIFT", "b": "LAND",
        "w": Action("FORWARD", parameters=(50, DT)), "a": Action("LEFT", parameters=(50, DT)),
        "s": Action("BACKWARD", parameters=(50, DT)), "d": Action("RIGHT", parameters=(50, DT)),
        "q": Action("ROTATE_LEFT", parameters=(50, DT)), "e": Action("ROTATE_RIGHT", parameters=(50, DT)),
        "Up": Action("INCREASE_HEIGHT", parameters=(50, DT)), "Down": Action("DECREASE_HEIGHT", parameters=(50, DT)),
        "Prior": Action("GIMBAL_UP", parameters=(50, DT)), "Next": Action("GIMBAL_DOWN", parameters=(50, DT)),
        "k": Action("GIMBAL_ABSOLUTE", parameters=(-45, )),
    }
    screen_displayer = ScreenDisplayer(data_channel, actions_queue, key_to_action=key_to_action, resolution=RESOLUTION)
    robot.add_controller(screen_displayer, name="Screen Displayer")
    robot.run()

    data_channel.close()
    env.close()

if __name__ == "__main__":
    main()
