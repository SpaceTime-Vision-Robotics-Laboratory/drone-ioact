#!/usr/bin/env python3
"""keyboard controller and display example. Same as the first example but also uses a priority queue."""
# pylint: disable=duplicate-code
import sys
import time
import threading
from pathlib import Path
from queue import PriorityQueue

import olympe
from drone_ioact.olympe import OlympeFrameReader, OlympeActionsMaker
from drone_ioact.data_consumers import KeyboardController, ScreenDisplayer
from drone_ioact import ActionsQueue, Action
from drone_ioact.utils import logger, ThreadGroup

QUEUE_MAX_SIZE = 30

class MyActionsPriorityQueue(ActionsQueue):
    """Wrapper on top of a priority queue for actions"""
    def put(self, item: tuple[int, Action], *args, **kwargs):
        self.queue.put(item, *args, **kwargs)

    def get(self, *args, **kwargs) -> Action:
        return self.queue.get(*args, **kwargs)[1]

class PriorityKeyboardController(KeyboardController):
    """1 = low priority, 0 = high priority as per PriorityQueue rules: lower is better"""
    def add_to_queue(self, action: Action):
        priority = 1
        if action in ("DISCONNECT", "FORWARD_NOWAIT", "ROTATE_NOWAIT"):
            priority = 0
        return super().add_to_queue((priority, action))

def main():
    """main fn"""
    drone = olympe.Drone(ip := sys.argv[1])
    assert drone.connect(), f"could not connect to '{ip}'"
    actions = ["DISCONNECT", "LIFT", "LAND", "FORWARD", "ROTATE", "FORWARD_NOWAIT", "ROTATE_NOWAIT"]
    actions_queue = MyActionsPriorityQueue(PriorityQueue(maxsize=QUEUE_MAX_SIZE), actions=actions)

    # data producer thread (1) (drone I/O in -> data/RGB out)
    olympe_frame_reader = OlympeFrameReader(drone=drone, metadata_dir=Path.cwd() / "metadata")
    # data consumer threads (data/RGB in -> I/O out)
    screen_displayer = ScreenDisplayer(drone_in=olympe_frame_reader)
    # data consumer & actions producer threads (data/RGB in -> action out)
    key_to_action = {"q": "DISCONNECT", "t": "LIFT", "l": "LAND", "i": "FORWARD",
                     "o": "ROTATE", "w": "FORWARD_NOWAIT", "e": "ROTATE_NOWAIT"}
    kb_controller = PriorityKeyboardController(drone_in=olympe_frame_reader, actions_queue=actions_queue,
                                               key_to_action=key_to_action)
    # actions consumer thread (1) (action in -> drone I/O out)
    olympe_actions_maker = OlympeActionsMaker(drone=drone, actions_queue=actions_queue)

    threads = ThreadGroup({
        "Keyboard controller": kb_controller,
        "Screen displayer": screen_displayer,
        "Olympe actions maker": olympe_actions_maker,
    })
    threads.start()

    while olympe_frame_reader.is_streaming() and not threads.is_any_dead():
        logger.debug2(f"Queue size: {len(actions_queue)}")
        time.sleep(1)

    logger.info(f"Stopping threads: \n{threads}")
    drone.disconnect()

if __name__ == "__main__":
    main()
