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
        threading.Thread(self)
        self.drone = drone
        self.start()

    def run(self):
        while True:
            if not self.drone.connected or self.drone.streaming is None:
                logger.info(f"{self.drone.connected=} {self.drone.streaming=}. Stopping thread")
                break
            action: Action = self.actions_queue.get(block=True, timeout=1_000)
            if not isinstance(action, Action):
                logger.debug("Did not receive an action: {type(action)}. Skipping")
                continue

            logger.info(f"Received action: {action.name} (#in queue: {self.actions_queue.qsize()})")
            if action == Action.DISCONNECT:
                self.drone.streaming.stop()
                continue

            res = True
            if action == Action.LIFT:
                res = self.drone(TakeOff()).wait().success()
            if action == Action.LAND:
                res = self.drone(Landing()).wait().success()
            if action == Action.FORWARD:
                res = self.drone(
                    moveBy(1, 0, 0, 0) >> # (forward, right, down, rotation)
                    FlyingStateChanged(state="hovering", _timeout=3)
                ).wait()
            if action == Action.ROTATE:
                res = self.drone(
                    moveBy(0, 0, 0, 0.2) >> # (forward, right, down, rotation)
                    FlyingStateChanged(state="hovering", _timeout=3)
                ).wait()
            if action == Action.FORWARD_NOWAIT:
                self.drone(
                    moveBy(1, 0, 0, 0) >> # (forward, right, down, rotation)
                    FlyingStateChanged(state="hovering", _timeout=3)
                )
            if action == Action.ROTATE_NOWAIT:
                self.drone(
                    moveBy(0, 0, 0, 0.2) >> # (forward, right, down, rotation)
                    FlyingStateChanged(state="hovering", _timeout=3)
                )

            if res is False:
                logger.warning(f"Action {action.name} could not be performed")
        logger.warning("OlympeActionsMaker thread stopping")
