#!/usr/bin/env python3
"""keyboard controller and display example"""
import sys
import time
from pathlib import Path
from queue import Queue

import olympe
from drone_ioact.olympe import OlympeFrameReader, OlympeActionsMaker
from drone_ioact.data_consumers import KeyboardController, ScreenDisplayer
from drone_ioact.utils import logger

QUEUE_MAX_SIZE = 30

def main():
    """main fn"""
    drone = olympe.Drone(ip := sys.argv[1])
    assert drone.connect(), f"could not connect to '{ip}'"
    actions_queue = Queue(maxsize=QUEUE_MAX_SIZE)

    # data producer thread (1) (drone I/O in -> data/RGB out)
    olympe_frame_reader = OlympeFrameReader(drone=drone, metadata_dir=Path.cwd() / "metadata")
    # data consumer threads (data/RGB in -> I/O out)
    screen_displayer = ScreenDisplayer(drone_in=olympe_frame_reader)
    # data consumer & actions producer threads (data/RGB in -> action out)
    kb_controller = KeyboardController(drone_in=olympe_frame_reader, actions_queue=actions_queue)
    # actions consumer thread (1) (action in -> drone I/O out)
    olympe_actions_maker = OlympeActionsMaker(drone=drone, actions_queue=actions_queue)

    while True:
        threads = {
            "Olympe frame reader": olympe_frame_reader.is_streaming(),
            "Keyboard controller": kb_controller.is_alive(),
            "Screen displayer": screen_displayer.is_alive(),
            "Olympe actions maker": olympe_actions_maker.is_alive(),
        }
        if any(v is False for v in threads.values()):
            logger.info("\n".join(f"- {k}: {v}" for k, v in threads.items()))
            break
        time.sleep(1)
    drone.disconnect()

if __name__ == "__main__":
    main()
