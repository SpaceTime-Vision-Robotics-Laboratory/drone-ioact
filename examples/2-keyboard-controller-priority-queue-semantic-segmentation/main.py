#!/usr/bin/env python3
"""keyboard controller and display example. Same as the first example but also uses a priority queue."""
# pylint: disable=duplicate-code
import sys
import time
from queue import PriorityQueue

import numpy as np
import olympe
from olympe.messages.ardrone3.PilotingState import FlyingStateChanged
from olympe.messages.ardrone3.Piloting import moveBy, Landing, TakeOff
from safeuav_semantic_data_producer import SafeUAVSemanticDataProducer, COLOR_MAP

from drone_ioact import ActionsQueue, Action, DataItem, DataChannel
from drone_ioact.drones.olympe_parrot import OlympeDataProducer, OlympeActionsConsumer
from drone_ioact.data_consumers import KeyboardController, ScreenDisplayer
from drone_ioact.utils import logger, ThreadGroup, colorize_semantic_segmentation

QUEUE_MAX_SIZE = 30
SCREEN_HEIGHT = 420

class SemanticScreenDisplayer(ScreenDisplayer):
    """Extends ScreenDisplayer to display semantic segmentation"""
    def __init__(self, *args, color_map: list[tuple[int, int, int]], **kwargs):
        super().__init__(*args, **kwargs)
        assert "semantic" in (st := self.data_channel.supported_types), f"'semantic' not in {st}"
        self.color_map = color_map

    def get_screen_frame(self, data: DataItem) -> np.ndarray:
        sema_rgb = colorize_semantic_segmentation(data["semantic"].argmax(-1), self.color_map).astype(np.uint8)
        combined = np.concatenate([data["rgb"], sema_rgb], axis=1)
        return combined

def actions_callback(actions_consumer: OlympeActionsConsumer, action: Action) -> bool:
    """the actions callback from generic actions to drone-specific ones"""
    drone: olympe.Drone = actions_consumer.drone
    if action == "DISCONNECT":
        drone.streaming.stop()
        return True
    if action == "LIFT":
        return drone(TakeOff()).wait().success()
    if action == "LAND":
        return drone(Landing()).wait().success()
    if action == "FORWARD":
        return drone(
            moveBy(1, 0, 0, 0) >> # (forward, right, down, rotation)
            FlyingStateChanged(state="hovering", _timeout=3)
        ).wait()
    if action == "ROTATE":
        return drone(
            moveBy(0, 0, 0, 0.2) >> # (forward, right, down, rotation)
            FlyingStateChanged(state="hovering", _timeout=3)
        ).wait()
    if action == "FORWARD_NOWAIT":
        drone(
            moveBy(1, 0, 0, 0) >> # (forward, right, down, rotation)
            FlyingStateChanged(state="hovering", _timeout=3)
        )
        return True
    if action == "ROTATE_NOWAIT":
        drone(
            moveBy(0, 0, 0, 0.2) >> # (forward, right, down, rotation)
            FlyingStateChanged(state="hovering", _timeout=3)
        )
        return True
    return False

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
    data_channel = DataChannel(supported_types=["rgb", "metadata"])

    # define the threads
    olympe_data_producer = OlympeDataProducer(drone=drone, data_channel=data_channel)
    if len(sys.argv) == 3:
        semantic_data_producer = SafeUAVSemanticDataProducer(rgb_data_producer=olympe_data_producer,
                                                             weights_path=sys.argv[2])
        screen_displayer = SemanticScreenDisplayer(data_producer=semantic_data_producer, screen_height=SCREEN_HEIGHT,
                                                   color_map=COLOR_MAP)
    else:
        screen_displayer = ScreenDisplayer(data_channel=data_channel, screen_height=SCREEN_HEIGHT)
    key_to_action = {"q": "DISCONNECT", "t": "LIFT", "l": "LAND", "i": "FORWARD",
                     "o": "ROTATE", "w": "FORWARD_NOWAIT", "e": "ROTATE_NOWAIT"}
    kb_controller = PriorityKeyboardController(data_channel=data_channel, actions_queue=actions_queue,
                                               key_to_action=key_to_action)
    olympe_actions_consumer = OlympeActionsConsumer(drone=drone, actions_queue=actions_queue,
                                                    actions_callback=actions_callback)

    threads = ThreadGroup({
        "Olympe data producer": olympe_data_producer,
        "Keyboard controller": kb_controller,
        "Screen displayer": screen_displayer,
        "Olympe actions consumer": olympe_actions_consumer,
    }).start()

    while not threads.is_any_dead():
        logger.debug2(f"Queue size: {len(actions_queue)}")
        time.sleep(1)

    drone.disconnect()
    threads.join(timeout=1)

if __name__ == "__main__":
    main()
