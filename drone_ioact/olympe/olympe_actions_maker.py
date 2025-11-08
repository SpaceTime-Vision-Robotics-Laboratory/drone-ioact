"""olympe_actions_maker.py: Takes generic actions and converts them to olympe-specific commands"""
import threading
from queue import Queue
import olympe
from olympe.messages.ardrone3.PilotingState import FlyingStateChanged
from olympe.messages.ardrone3.Piloting import moveBy, Landing, TakeOff

from drone_ioact import Action, DroneOut
from drone_ioact.utils import logger

class OlympeActionsMaker(DroneOut, threading.Thread):
    """OlympeActionsMaker: Takes generic actions and converts them to olympe-specific commands."""
    def __init__(self, drone: olympe.Drone, actions_queue: Queue):
        DroneOut.__init__(self, actions_queue)
        threading.Thread.__init__(self)
        self.drone = drone

    def run(self):
        while True:
            if not self.drone.connected or self.drone.streaming is None:
                logger.info(f"{self.drone.connected=} {self.drone.streaming=}. Stopping thread")
                break
            action: Action = self.actions_queue.get(block=True, timeout=1_000)
            if not isinstance(action, Action):
                logger.debug(f"Did not receive an action: {type(action)}. Skipping")
                continue

            logger.debug(f"Received action: '{action}' (#in queue: {len(self.actions_queue)})")
            if action == "DISCONNECT":
                self.drone.streaming.stop()
                continue

            res = True
            if action == "LIFT":
                res = self.drone(TakeOff()).wait().success()
            if action == "LAND":
                res = self.drone(Landing()).wait().success()
            if action == "FORWARD":
                res = self.drone(
                    moveBy(1, 0, 0, 0) >> # (forward, right, down, rotation)
                    FlyingStateChanged(state="hovering", _timeout=3)
                ).wait()
            if action == "ROTATE":
                res = self.drone(
                    moveBy(0, 0, 0, 0.2) >> # (forward, right, down, rotation)
                    FlyingStateChanged(state="hovering", _timeout=3)
                ).wait()
            if action == "FORWARD_NOWAIT":
                self.drone(
                    moveBy(1, 0, 0, 0) >> # (forward, right, down, rotation)
                    FlyingStateChanged(state="hovering", _timeout=3)
                )
            if action == "ROTATE_NOWAIT":
                self.drone(
                    moveBy(0, 0, 0, 0.2) >> # (forward, right, down, rotation)
                    FlyingStateChanged(state="hovering", _timeout=3)
                )

            if res is False:
                logger.warning(f"Action '{action}' could not be performed")
        logger.warning("OlympeActionsMaker thread stopping")
