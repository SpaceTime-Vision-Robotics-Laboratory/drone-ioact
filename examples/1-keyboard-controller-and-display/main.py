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
from drone_ioact import ActionsQueue, Action
from drone_ioact.utils import logger

QUEUE_MAX_SIZE = 30

class MyActionsQueue(ActionsQueue):
    """Defines the actions of this drone controller"""
    def get_actions(self) -> list[Action]:
        return ["DISCONNECT", "LIFT", "LAND", "FORWARD", "ROTATE", "FORWARD_NOWAIT", "ROTATE_NOWAIT"]

def main():
    """main fn"""
    drone = olympe.Drone(ip := sys.argv[1])
    assert drone.connect(), f"could not connect to '{ip}'"
    actions_queue = MyActionsQueue(Queue(maxsize=QUEUE_MAX_SIZE))

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

    threads: dict[str, threading.Thread] = {
        "Keyboard controller": kb_controller,
        "Screen displayer": screen_displayer,
        "Olympe actions maker": olympe_actions_maker,
    }
    [v.start() for v in threads.values()] # start the threads

    while True:
        logger.debug2(f"Queue size: {len(actions_queue)}")
        if any(not v.is_alive() for v in threads.values()) or not olympe_frame_reader.is_streaming():
            logger.info(f"{olympe_frame_reader} streaming:. {olympe_frame_reader.is_streaming()}")
            logger.info("\n".join(f"- {k}: {v.is_alive()}" for k, v in threads.items()))
            break
        time.sleep(1)
    drone.disconnect()

if __name__ == "__main__":
    main()
