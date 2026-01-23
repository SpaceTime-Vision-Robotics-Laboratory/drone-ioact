#!/usr/bin/env python3
"""keyboard controller and display example"""
import sys
import time
from queue import Queue
from functools import partial
from loggez import loggez_logger as logger

import olympe
from olympe.video.pdraw import PdrawState

from robobase import ActionsQueue, DataChannel, ThreadGroup, DataProducerList, Actions2Robot
from roboimpl.drones.olympe_parrot import OlympeDataProducer, olympe_actions_fn, OLYMPE_SUPPORTED_ACTIONS
from roboimpl.controllers import ScreenDisplayer

QUEUE_MAX_SIZE = 30
SCREEN_HEIGHT = 480 # width is auto-scaled

def main():
    """main fn"""
    drone = olympe.Drone(ip := sys.argv[1])
    assert drone.connect(), f"could not connect to '{ip}'"
    actions_queue = ActionsQueue(Queue(maxsize=QUEUE_MAX_SIZE), actions=OLYMPE_SUPPORTED_ACTIONS)
    data_channel = DataChannel(supported_types=["rgb", "metadata"],
                               eq_fn=lambda a, b: a["metadata"]["time"] == b["metadata"]["time"])

    # define the threads
    olympe_data_producer = OlympeDataProducer(drone=drone)
    data_producers = DataProducerList(data_channel=data_channel, data_producers=[olympe_data_producer])
    key_to_action = {"Escape": "DISCONNECT", "space": "LIFT", "b": "LAND",
                     "w": "FORWARD", "a": "LEFT", "s": "BACKWARD", "d": "RIGHT",
                     "Up": "INCREASE_HEIGHT", "Down": "DECREASE_HEIGHT", "Left": "ROTATE_LEFT", "Right": "ROTATE_RIGHT"}
    screen_displayer = ScreenDisplayer(data_channel, actions_queue, key_to_action=key_to_action,
                                       screen_height=SCREEN_HEIGHT)
    termination_fn = lambda: drone.connected and drone.streaming.state == PdrawState.Playing # pylint: disable=all #noqa
    actions_fn = partial(olympe_actions_fn, drone=drone)
    action2drone = Actions2Robot(actions_queue, action_fn=actions_fn, termination_fn=termination_fn)

    threads = ThreadGroup({
        "Drone -> Data": data_producers,
        "Screen displayer": screen_displayer,
        "Action -> Drone": action2drone,
    }).start()

    while not threads.is_any_dead():
        logger.trace(f"{data_channel}. Actions queue size: {len(actions_queue)}")
        time.sleep(1)

    drone.disconnect()
    threads.join(timeout=1)

if __name__ == "__main__":
    main()
