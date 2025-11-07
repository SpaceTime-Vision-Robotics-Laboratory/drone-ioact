#!/usr/bin/env python3
"""keyboard controller and display example + priority queue"""
import sys
import time
from pathlib import Path
from queue import PriorityQueue

import olympe
from drone_ioact.olympe import OlympeFrameReader, OlympeActionsMaker
from drone_ioact.data_consumers import KeyboardController, ScreenDisplayer
from drone_ioact import ActionsQueue, Action
from drone_ioact.utils import logger

QUEUE_MAX_SIZE = 30

class MyActionsPriorityQueue(ActionsQueue):
    """Wrapper on top of a priority queue for actions"""
    def get_actions(self) -> list[Action]:
        return ["DISCONNECT", "LIFT", "LAND", "FORWARD", "ROTATE", "FORWARD_NOWAIT", "ROTATE_NOWAIT"]

    def put(self, item: tuple[int, Action], *args, **kwargs):
        self.queue.put(item, *args, **kwargs)

    def get(self, *args, **kwargs) -> Action:
        return self.queue.get(*args, **kwargs)[1]

class PriorityKeyboardController(KeyboardController):
    def add_to_queue(self, action: Action):
        """1 = low priority, 0 = high priority as per PriorityQueue rules: lower is better"""
        priority = 1
        if action in ("DISCONNECT", "FORWARD_NOWAIT", "ROTATE_NOWAIT"):
            priority = 0
        return super().add_to_queue((priority, action))

def main():
    """main fn"""
    drone = olympe.Drone(ip := sys.argv[1])
    assert drone.connect(), f"could not connect to '{ip}'"
    actions_queue = MyActionsPriorityQueue(PriorityQueue(maxsize=QUEUE_MAX_SIZE))

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
