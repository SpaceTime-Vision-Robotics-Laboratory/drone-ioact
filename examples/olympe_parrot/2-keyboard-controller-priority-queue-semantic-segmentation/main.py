#!/usr/bin/env python3
"""keyboard controller and display example. Same as the first example but also uses a priority queue."""
# pylint: disable=duplicate-code
import sys
from queue import PriorityQueue
from functools import partial
from overrides import overrides
import numpy as np

from robobase import Robot, ActionsQueue, Action, DataItem, DataChannel
from roboimpl.data_producers.semantic_segmentation import PHGMAESemanticDataProducer
from roboimpl.envs.olympe_parrot import OlympeEnv, olympe_actions_fn, OLYMPE_SUPPORTED_ACTIONS
from roboimpl.controllers import ScreenDisplayer
from roboimpl.utils import semantic_map_to_image

QUEUE_MAX_SIZE = 30
RESOLUTION = 480, 640

def screen_frame_semantic(data: dict[str, DataItem], color_map: list[tuple[int, int, int]]) -> np.ndarray:
    """produces RGB + semantic segmentation as a single frame"""
    sema_rgb = semantic_map_to_image(data["semantic"].argmax(-1), color_map).astype(np.uint8)
    combined = np.concatenate([data["rgb"], sema_rgb], axis=1)
    return combined

class MyActionsPriorityQueue(ActionsQueue):
    """Wrapper on top of a priority queue for actions"""
    @overrides(check_signature=False)
    def put(self, item: tuple[int, Action], *args, **kwargs):
        self.queue.put(item, *args, **kwargs)

    @overrides
    def get(self, *args, **kwargs) -> Action:
        return self.queue.get(*args, **kwargs)[1]

class PriorityScreenDisplayer(ScreenDisplayer):
    """1 = low priority, 0 = high priority as per PriorityQueue rules: lower is better"""
    @overrides
    def add_to_queue(self, action: Action):
        priority = 1
        if action in ("DISCONNECT", "FORWARD_NOWAIT", "ROTATE_NOWAIT"):
            priority = 0
        return super().add_to_queue((priority, action))

def main():
    """main fn"""
    env = OlympeEnv(ip=sys.argv[1])
    actions_queue = MyActionsPriorityQueue(OLYMPE_SUPPORTED_ACTIONS, queue=PriorityQueue(maxsize=QUEUE_MAX_SIZE))
    data_channel = DataChannel(supported_types=["rgb", "metadata", *(["semantic"] if len(sys.argv) == 3 else [])],
                               eq_fn=lambda a, b: a["metadata"]["time"] == b["metadata"]["time"])
    screen_frame_callback = None

    robot = Robot(env=env, data_channel=data_channel, actions_queue=actions_queue, action_fn=olympe_actions_fn)

    # define the threads
    if len(sys.argv) == 3:
        robot.add_data_producer(PHGMAESemanticDataProducer(weights_path=sys.argv[2]))
        screen_frame_callback = partial(screen_frame_semantic, color_map=PHGMAESemanticDataProducer.COLOR_MAP)

    key_to_action = {
        "Escape": "DISCONNECT", "space": "LIFT", "b": "LAND",
        "w": "FORWARD", "a": "LEFT", "s": "BACKWARD", "d": "RIGHT", "q": "ROTATE_LEFT", "e": "ROTATE_RIGHT",
        "Up": "INCREASE_HEIGHT", "Down": "DECREASE_HEIGHT", "Next": "TILT_DOWN", "Prior": "TILT_UP"
    }
    screen_displayer = PriorityScreenDisplayer(data_channel, actions_queue, resolution=RESOLUTION,
                                               screen_frame_callback=screen_frame_callback, key_to_action=key_to_action)
    robot.add_controller(screen_displayer, name="Screen displayer")
    robot.run()

    env.close()
    data_channel.close()

if __name__ == "__main__":
    main()
