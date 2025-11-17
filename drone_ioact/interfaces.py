"""
interfaces.py - Interfaces for interacting with the data produced by a drone. The usual flow is like this:
Drone --raw data--> DataPrd --get_current_data()--> DataConsumer1            | <--a_q.pop()-- ActionsC --action-- Drone
                                                    DC2 & ActionsProducer1 --|
                                                    DC3                      |
                                                    DC4 & ActionsProducer2 --|
                                                    ...
DataPrd = Data producer; ActionsC = Actions Consumer.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Callable
from queue import Queue
import threading
import numpy as np

from drone_ioact.utils import logger

Action = str # actions are stored as simple strings for simplicity :)
ActionCallback = Callable[["ActionsConsumer", Action], bool]

class ActionsQueue:
    """Interface defining the actions understandable by a drone and the application. Queue must be thread-safe!"""
    def __init__(self, queue: Queue, actions: list[Action]):
        super().__init__()
        self.queue = queue
        self.actions = actions

    def put(self, item: Action, *args, **kwargs):
        """Put an item into the queue"""
        assert isinstance(item, Action), type(item)
        assert item in (actions := self.actions), f"{item} not in {actions}"
        self.queue.put(item, *args, **kwargs)

    def get(self, *args, **kwargs) -> Action:
        """Remove and return an item from the queue"""
        return self.queue.get(*args, **kwargs)

    def __len__(self):
        return self.queue.qsize()

class DataProducer(ABC):
    """Interface defining the requirements of a drone (real, sym, mock) to produce data for a consumer"""
    @abstractmethod
    def get_current_data(self, timeout_s: int = 10) -> dict[str, np.ndarray]:
        """gets the data (RGB and maybe others) as a dict of numpy arrays"""

    @abstractmethod
    def is_streaming(self) -> bool:
        """checks if the drone is connected and streaming or not"""

    @abstractmethod
    def get_supported_types(self) -> list[str]:
        """returns a list of supported types which will be the keys of get_current_data"""

class DataConsumer(ABC):
    """Interface defining the requirements of a data consumer getting data from a DataProducer"""
    def __init__(self, data_producer: DataProducer):
        self._data_producer = data_producer

    @property
    def data_producer(self) -> DataProducer:
        """The DataProducer instance from which data is created"""
        return self._data_producer

class ActionsProducer(ABC):
    """Interface defining the requirements of an actions producer (i.e. sending to a ActionsConsumer)"""
    def __init__(self, actions_queue: ActionsQueue):
        assert isinstance(actions_queue, ActionsQueue), f"queue must inherit ActionsQueue: {type(actions_queue)}"
        self._actions_queue = actions_queue

    @property
    def actions_queue(self) -> Queue:
        """The actions queue where the actions are inserted"""
        return self._actions_queue

class ActionsConsumer(ABC, threading.Thread):
    """Interface defining the requirements of a drone (real, sym, mock) to receive an action & apply it to the drone"""
    def __init__(self, actions_queue: ActionsQueue, action_callback: ActionCallback):
        threading.Thread.__init__(self, daemon=True)
        assert isinstance(actions_queue, ActionsQueue), f"queue must inherit ActionsQueue: {type(actions_queue)}"
        self._actions_queue = actions_queue
        self._action_callback = action_callback

    @property
    def actions_queue(self) -> ActionsQueue:
        """The actions queue where the actions are inserted"""
        return self._actions_queue

    @property
    def action_callback(self) -> ActionCallback:
        """Given a generic action, communicates it to the drone"""
        return self._action_callback

    @abstractmethod
    def stop_streaming(self):
        """calls the drone to stop sending messages"""

    @abstractmethod
    def is_streaming(self) -> bool:
        """checks if the drone is connected and streaming or not"""

    def run(self):
        while self.is_streaming():
            action: Action = self.actions_queue.get(block=True, timeout=1_000)
            if not isinstance(action, Action):
                logger.debug(f"Did not receive an action: {type(action)}. Skipping")
                continue

            logger.debug(f"Received action: '{action}' (#in queue: {len(self.actions_queue)})")
            if action not in self.actions_queue.actions:
                logger.debug(f"Action '{action}' not in actions={self.actions_queue.actions}. Skipping.")
                continue

            res = self.action_callback(self, action)
            if res is False:
                logger.warning(f"Could not perform action '{action}'")

        logger.info(f"Stopping {self}.")
