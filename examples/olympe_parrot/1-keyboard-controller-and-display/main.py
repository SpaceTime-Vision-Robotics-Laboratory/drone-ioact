#!/usr/bin/env python3
"""keyboard controller and display example"""
import sys
import time
from queue import Queue
from loggez import loggez_logger as logger

from robobase import ActionsQueue, DataChannel, ThreadGroup, DataProducers2Channels, Actions2Robot, RawDataProducer
from roboimpl.drones.olympe_parrot import OlympeEnv, olympe_actions_fn, OLYMPE_SUPPORTED_ACTIONS
from roboimpl.controllers import ScreenDisplayer

QUEUE_MAX_SIZE = 30
RESOLUTION = 480, 640

def main():
    """main fn"""
    env = OlympeEnv(ip=sys.argv[1])
    actions_queue = ActionsQueue(Queue(maxsize=QUEUE_MAX_SIZE), actions=OLYMPE_SUPPORTED_ACTIONS)
    data_channel = DataChannel(supported_types=["rgb", "metadata"],
                               eq_fn=lambda a, b: a["metadata"]["time"] == b["metadata"]["time"])

    # define the threads
    raw_data_producer = RawDataProducer(env=env)
    data_producers = DataProducers2Channels(data_producers=[raw_data_producer], data_channels=[data_channel])
    key_to_action = {
        "Escape": "DISCONNECT", "space": "LIFT", "b": "LAND",
        "w": "FORWARD", "a": "LEFT", "s": "BACKWARD", "d": "RIGHT", "q": "ROTATE_LEFT", "e": "ROTATE_RIGHT",
        "Up": "INCREASE_HEIGHT", "Down": "DECREASE_HEIGHT", "Next": "TILT_DOWN", "Prior": "TILT_UP"
    }
    screen_displayer = ScreenDisplayer(data_channel, actions_queue, key_to_action=key_to_action, resolution=RESOLUTION)
    action2drone = Actions2Robot(env=env, actions_queue=actions_queue, action_fn=olympe_actions_fn)

    threads = ThreadGroup({
        "Drone -> Data": data_producers,
        "Screen displayer": screen_displayer,
        "Action -> Drone": action2drone,
    }).start()

    while not threads.is_any_dead():
        logger.trace(f"{data_channel}. Actions queue size: {len(actions_queue)}")
        time.sleep(1)

    env.drone.disconnect()
    threads.join(timeout=1)

if __name__ == "__main__":
    main()
