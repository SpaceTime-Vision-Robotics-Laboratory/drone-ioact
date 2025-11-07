#!/usr/bin/env python3
"""keyboard controller and display example + priority queue"""
import sys
import time
from pathlib import Path
from queue import PriorityQueue
from pynput.keyboard import KeyCode

import olympe
from drone_ioact.actions import Action
from drone_ioact.olympe import OlympeFrameReader, OlympeActionsMaker
from drone_ioact.data_consumers import KeyboardController, ScreenDisplayer
from drone_ioact.utils import logger

QUEUE_MAX_SIZE = 30

class CustomKBController(KeyboardController):
    """Wrapper that inserts two actions with higher priority in the queue"""
    def on_release(self, key: KeyCode) -> bool:
        action: Action = self.key_to_action(key)
        if action is None:
            logger.debug(f"Unused char: {key}")
            return True

        logger.info(f"Pressed {key}. Pushing: {action.name}")
        priority = 1 # lower is better
        if action in (Action.FORWARD_NOWAIT, Action.ROTATE_NOWAIT, Action.DISCONNECT):
            logger.debug(f"Received a priority action: {action.name}. Adding it to the start of the queue")
            priority = 0
        self.actions_queue.put((priority, action), block=True)

        if action == Action.DISCONNECT:
            logger.info("Disconnect was requested. Stopping Keyboard Controller.")
            return False
        return True

class CustomPriorityQueue(PriorityQueue):
    """Wrapper that returns the item and not the priority"""
    def get(self, *args, **kwargs) -> Action:
        return super().get(*args, **kwargs)[1] # (priority, action)

def main():
    """main fn"""
    drone = olympe.Drone(ip := sys.argv[1])
    assert drone.connect(), f"could not connect to '{ip}'"
    actions_queue = CustomPriorityQueue(maxsize=QUEUE_MAX_SIZE)

    # data producer thread (1) (drone I/O in -> data/RGB out)
    olympe_frame_reader = OlympeFrameReader(drone=drone, metadata_dir=Path.cwd() / "metadata")
    # data consumer threads (data/RGB in -> I/O out)
    screen_displayer = ScreenDisplayer(drone_in=olympe_frame_reader)
    # data consumer & actions producer threads (data/RGB in -> action out)
    kb_controller = CustomKBController(drone_in=olympe_frame_reader, actions_queue=actions_queue)
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
