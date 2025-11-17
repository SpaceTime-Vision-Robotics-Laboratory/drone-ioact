#!/usr/bin/env python3
"""keyboard controller and display example. Same as the first example but also uses a priority queue."""
# pylint: disable=duplicate-code
import sys
import time
from pathlib import Path
from queue import PriorityQueue

import numpy as np
import olympe
from olympe.messages.ardrone3.PilotingState import FlyingStateChanged
from olympe.messages.ardrone3.Piloting import moveBy, Landing, TakeOff
from safeuav_semantic_data_producer import SafeUAVSemanticDataProducer, COLOR_MAP

from drone_ioact.drones.olympe_parrot import OlympeFrameReader, OlympeActionsMaker
from drone_ioact.data_consumers import KeyboardController, ScreenDisplayer
from drone_ioact import ActionsQueue, Action
from drone_ioact.utils import logger, ThreadGroup, colorize_semantic_segmentation

QUEUE_MAX_SIZE = 30
SCREEN_HEIGHT = 420

class SemanticScreenDisplayer(ScreenDisplayer):
    """Extends ScreenDisplayer to display semantic segmentation"""
    def __init__(self, *args, color_map: list[tuple[int, int, int]], **kwargs):
        super().__init__(*args, **kwargs)
        assert "semantic" in (st := self.data_producer.get_supported_types()), f"'rgb' not in {st}"
        self.color_map = color_map

    def get_current_frame(self):
        data = self.data_producer.get_current_data()
        rgb, semantic = data["rgb"], data["semantic"]
        sema_rgb = colorize_semantic_segmentation(semantic.argmax(-1), self.color_map).astype(np.uint8)
        combined = np.concatenate([rgb, sema_rgb], axis=1)
        return combined

def action_callback(actions_maker: OlympeActionsMaker, action: Action) -> bool:
    """the actions callback from generic actions to drone-specific ones"""
    drone: olympe.Drone = actions_maker.drone
    if action == "DISCONNECT":
        actions_maker.stop_streaming()
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

    # data producer thread (1) (drone I/O in -> data/RGB out)
    olympe_frame_reader = OlympeFrameReader(drone=drone, metadata_dir=Path.cwd() / "metadata")
    if len(sys.argv) == 3:
        semantic_data_producer = SafeUAVSemanticDataProducer(data_producer=olympe_frame_reader,
                                                             weights_path=sys.argv[2])
        screen_displayer = SemanticScreenDisplayer(data_producer=semantic_data_producer, screen_height=SCREEN_HEIGHT,
                                                   color_map=COLOR_MAP)
    else:
        screen_displayer = ScreenDisplayer(data_producer=olympe_frame_reader, screen_height=SCREEN_HEIGHT)
    # data consumer & actions producer threads (data/RGB in -> action out)
    key_to_action = {"q": "DISCONNECT", "t": "LIFT", "l": "LAND", "i": "FORWARD",
                     "o": "ROTATE", "w": "FORWARD_NOWAIT", "e": "ROTATE_NOWAIT"}
    kb_controller = PriorityKeyboardController(data_producer=olympe_frame_reader, actions_queue=actions_queue,
                                               key_to_action=key_to_action)
    # actions consumer thread (1) (action in -> drone I/O out)
    olympe_actions_maker = OlympeActionsMaker(drone=drone, actions_queue=actions_queue, action_callback=action_callback)

    threads = ThreadGroup({
        "Keyboard controller": kb_controller,
        "Screen displayer": screen_displayer,
        "Olympe actions maker": olympe_actions_maker,
    })
    threads.start()

    while olympe_frame_reader.is_streaming() and not threads.is_any_dead():
        logger.debug2(f"Queue size: {len(actions_queue)}")
        time.sleep(1)

    drone.disconnect()
    threads.join(timeout=1)

if __name__ == "__main__":
    main()
