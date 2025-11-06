#!/usr/bin/env python3
import os
from pathlib import Path
from multiprocessing import Queue

import olympe
from olympe_io import OlympeFrameReader, OlympleActionsMaker
from controllers import KeyboardController, ScreenDisplayer
from utils import logger

QUEUE_MAX_SIZE = 30

def main():
    """main fn"""
    drone = olympe.Drone(ip := os.getenv("DRONE_IP"))
    assert drone.connect(), f"could not connect to '{ip}'"

    # data producer threads
    olympe_frame_reader = OlympeFrameReader(drone=drone, metadata_dir=Path.cwd() / "metadata")
    # data consumer threads
    screen_displayer = ScreenDisplayer(drone_in=olympe_frame_reader)
    queue = Queue(maxsize=QUEUE_MAX_SIZE)
    # data consumer and action producer threads
    kb_controller = KeyboardController(drone_in=olympe_frame_reader, actions_queue=queue)
    olympe_actions_maker = OlympleActionsMaker(drone=drone, actions_queue=queue)

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
    drone.disconnect()

if __name__ == '__main__':
    main()
