#!/usr/bin/env python3
"""keyboard controller and display example"""
import sys
import time
import threading
from pathlib import Path
from queue import Queue

import olympe
from drone_ioact.olympe import OlympeFrameReader, OlympeActionsMaker
from drone_ioact.data_consumers import KeyboardController, ScreenDisplayer
from drone_ioact import ActionsQueue
from drone_ioact.utils import logger, ThreadGroup

QUEUE_MAX_SIZE = 30

def main():
    """main fn"""
    drone = olympe.Drone(ip := sys.argv[1])
    assert drone.connect(), f"could not connect to '{ip}'"
    actions = ["DISCONNECT", "LIFT", "LAND", "FORWARD", "ROTATE", "FORWARD_NOWAIT", "ROTATE_NOWAIT"]
    actions_queue = ActionsQueue(Queue(maxsize=QUEUE_MAX_SIZE), actions=actions)

    # data producer thread (1) (drone I/O in -> data/RGB out)
    olympe_frame_reader = OlympeFrameReader(drone=drone, metadata_dir=Path.cwd() / "metadata")
    # data consumer threads (data/RGB in -> I/O out)
    screen_displayer = ScreenDisplayer(drone_in=olympe_frame_reader)
    # data consumer & actions producer threads (data/RGB in -> action out)
    key_to_action = {"q": "DISCONNECT", "t": "LIFT", "l": "LAND", "i": "FORWARD",
                     "o": "ROTATE", "w": "FORWARD_NOWAIT", "e": "ROTATE_NOWAIT"}
    kb_controller = KeyboardController(drone_in=olympe_frame_reader, actions_queue=actions_queue,
                                       key_to_action=key_to_action)
    # actions consumer thread (1) (action in -> drone I/O out)
    olympe_actions_maker = OlympeActionsMaker(drone=drone, actions_queue=actions_queue)

    threads = ThreadGroup({
        "Keyboard controller": kb_controller,
        "Screen displayer": screen_displayer,
        "Olympe actions maker": olympe_actions_maker,
    })
    threads.strart()

    while olympe_frame_reader.is_streaming() and not threads.is_any_dead():
        logger.debug2(f"Queue size: {len(actions_queue)}")
        time.sleep(1)

    logger.info(f"Stopping threads: \n{threads}")
    drone.disconnect()

if __name__ == "__main__":
    main()
