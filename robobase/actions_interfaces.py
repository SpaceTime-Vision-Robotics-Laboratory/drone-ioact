"""actions_interfaces.py - Interfaces for interacting with the actions produced by a ActionProducers"""
from __future__ import annotations
from abc import ABC, abstractmethod
import threading

from robobase.types import Action, ActionsCallback
from robobase.utils import logger
from robobase.actions_queue import ActionsQueue

class ActionConsumer(ABC, threading.Thread):
    """Interface defining the requirements of a drone (real, sym, mock) to receive an action & apply it to the drone"""
    def __init__(self, actions_queue: ActionsQueue, actions_callback: ActionsCallback):
        threading.Thread.__init__(self, daemon=True)
        assert isinstance(actions_queue, ActionsQueue), f"queue must inherit ActionsQueue: {type(actions_queue)}"
        self._actions_queue = actions_queue
        self._actions_callback = actions_callback

    @property
    def actions_queue(self) -> ActionsQueue:
        """The actions queue where the actions are inserted"""
        return self._actions_queue

    @property
    def actions_callback(self) -> ActionsCallback:
        """Given a generic action, communicates it to the drone"""
        return self._actions_callback

    @abstractmethod
    def is_streaming(self) -> bool:
        """checks if the drone is connected and streaming or not"""

    def run(self):
        while self.is_streaming():
            action: Action = self.actions_queue.get(block=True, timeout=1_000)
            logger.debug(f"Received action: '{action}' (#in queue: {len(self.actions_queue)})")
            res = self.actions_callback(self, action)
            if res is False:
                logger.warning(f"Could not perform action '{action}'")

        logger.info(f"Stopping {self}.")
