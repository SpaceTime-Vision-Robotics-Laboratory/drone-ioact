"""action2robot.py - the module that interfaces bewteen the action and the robot/drone"""
from __future__ import annotations
import threading
from queue import Empty

from robobase.types import Action, ActionFn, TerminationFn
from robobase.utils import logger
from robobase.actions_queue import ActionsQueue

class Actions2Robot(threading.Thread):
    """Interface defining the requirements of a robot (real, sym, mock) to receive an action & apply it to the robot"""
    def __init__(self, actions_queue: ActionsQueue, action_fn: ActionFn, termination_fn: TerminationFn):
        threading.Thread.__init__(self, daemon=True)
        assert isinstance(actions_queue, ActionsQueue), f"queue must inherit ActionsQueue: {type(actions_queue)}"
        self._actions_queue = actions_queue
        self._action_fn = action_fn
        self._termination_fn = termination_fn

    @property
    def actions_queue(self) -> ActionsQueue:
        """The actions queue where the actions are inserted"""
        return self._actions_queue

    @property
    def action_fn(self) -> ActionFn:
        """Given a generic action, communicates it to the robot"""
        return self._action_fn

    @property
    def termination_fn(self) -> TerminationFn:
        """The termination function. If this returns true then the connection to the robot (drone, sim.) ended"""
        return self._termination_fn

    def run(self):
        while not self.termination_fn():
            try:
                action: Action = self.actions_queue.get(block=True, timeout=1_000)
            except Empty:
                continue
            logger.debug(f"Received action: '{action}' (#in queue: {len(self.actions_queue)})")
            res = self.action_fn(action)
            if res is False:
                logger.warning(f"Could not perform action '{action}'")

        logger.debug(f"Stopping {self}. {self.termination_fn()=}")
