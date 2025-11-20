#!/usr/bin/env python3
"""keyboard controller and display example"""
import sys
import time
from queue import Queue

import olympe
from olympe.messages.ardrone3.PilotingState import FlyingStateChanged
from olympe.messages.ardrone3.Piloting import moveBy, Landing, TakeOff

from drone_ioact import ActionsQueue, Action, DataChannel
from drone_ioact.drones.olympe_parrot import OlympeDataProducer, OlympeActionsConsumer
from drone_ioact.data_consumers import KeyboardController, ScreenDisplayer
from drone_ioact.utils import logger, ThreadGroup

QUEUE_MAX_SIZE = 30

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

def main():
    """main fn"""
    drone = olympe.Drone(ip := sys.argv[1])
    assert drone.connect(), f"could not connect to '{ip}'"
    actions = ["DISCONNECT", "LIFT", "LAND", "FORWARD", "ROTATE", "FORWARD_NOWAIT", "ROTATE_NOWAIT"]
    actions_queue = ActionsQueue(Queue(maxsize=QUEUE_MAX_SIZE), actions=actions)
    data_channel = DataChannel(supported_types=["rgb", "metadata"],
                               eq_fn=lambda a, b: a["frame_ix"] == b["frame_ix"])

    # define the threads
    olympe_data_producer = OlympeDataProducer(drone=drone, data_channel=data_channel)
    screen_displayer = ScreenDisplayer(data_channel=data_channel)
    key_to_action = {"q": "DISCONNECT", "t": "LIFT", "l": "LAND", "i": "FORWARD",
                     "o": "ROTATE", "w": "FORWARD_NOWAIT", "e": "ROTATE_NOWAIT"}
    kb_controller = KeyboardController(data_channel=data_channel, actions_queue=actions_queue,
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
        logger.debug2(f"{data_channel}. Actions queue size: {len(actions_queue)}")
        time.sleep(1)

    drone.disconnect()
    threads.join(timeout=1)

if __name__ == "__main__":
    main()
