#!/usr/bin/env python3
"""keyboard controller and display example"""
import sys
import time
from queue import Queue

import olympe

from drone_ioact import ActionsQueue, DataChannel
from drone_ioact.drones.olympe_parrot import (
    OlympeDataProducer, OlympeActionsConsumer, olympe_actions_callback, OLYMPE_SUPPORTED_ACTIONS)
from drone_ioact.data_consumers import ScreenDisplayer
from drone_ioact.utils import logger, ThreadGroup

QUEUE_MAX_SIZE = 30

def main():
    """main fn"""
    drone = olympe.Drone(ip := sys.argv[1])
    assert drone.connect(), f"could not connect to '{ip}'"
    actions_queue = ActionsQueue(Queue(maxsize=QUEUE_MAX_SIZE), actions=OLYMPE_SUPPORTED_ACTIONS)
    data_channel = DataChannel(supported_types=["rgb", "metadata"],
                               eq_fn=lambda a, b: a["frame_ix"] == b["frame_ix"])

    # define the threads
    olympe_data_producer = OlympeDataProducer(drone=drone, data_channel=data_channel)
    key_to_action = {"q": "DISCONNECT", "t": "LIFT", "l": "LAND", "i": "FORWARD",
                     "o": "ROTATE", "w": "FORWARD_NOWAIT", "e": "ROTATE_NOWAIT"}
    screen_displayer = ScreenDisplayer(data_channel, actions_queue, key_to_action=key_to_action)
    olympe_actions_consumer = OlympeActionsConsumer(drone=drone, actions_queue=actions_queue,
                                                    actions_callback=olympe_actions_callback)

    threads = ThreadGroup({
        "Olympe data producer": olympe_data_producer,
        "Screen displayer": screen_displayer,
        "Olympe actions consumer": olympe_actions_consumer,
    }).start()

    while not threads.is_any_dead():
        logger.debug2(f"{data_channel}. Actions queue size: {len(actions_queue)}")
        time.sleep(1)

    drone.disconnect()
    threads.join(timeout=1)

if __name__ == "__main__":
    main()
