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
from copy import deepcopy
import time
from queue import Queue
from datetime import datetime
import threading
import numpy as np

from drone_ioact.utils import logger, lo

Action = str # actions are stored as simple strings for simplicity :)
ActionsCallback = Callable[["ActionsConsumer", Action], bool]
DataItem = dict[str, np.ndarray | int | str | float]

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

class DataChannel:
    """DataChannel defines the thread-safe data structure where the data producer writes the data and consumers read"""
    def __init__(self, supported_types: list[str]):
        self.supported_types = set(supported_types)
        assert len(supported_types) > 0, "cannot have a data channel that supports no data type (i.e. rgb, pose etc.)"

        self._lock = threading.Lock()
        self._data: DataItem = {}
        self._is_closed = False
        self.timestamp: str = "1900-01-01"

    def put(self, item: DataItem):
        """Put data into the queue"""
        assert isinstance(item, dict), type(item)
        assert (ks := set(item.keys())) == (st := self.supported_types), f"Data keys: {ks} vs. Supported types: {st}"
        with self._lock:
            assert not self._is_closed, "Cannot put data in a closed chanel"
            self._data = item
            self.timestamp = datetime.now().isoformat()

    def get(self) -> DataItem:
        """Return the item from the channel"""
        with self._lock:
            assert not self._is_closed, "Cannot get data from a closed chanel"
            return deepcopy({**self._data, "timestamp": self.timestamp})

    def has_data(self) -> bool:
        """Checks if the channel has data"""
        with self._lock:
            return len(self._data) > 0 and not self._is_closed

    def close(self):
        """Closes the channel"""
        assert self.has_data(), "cannot call close before any data was received"
        with self._lock:
            self._is_closed = True

class DataProducer(ABC, threading.Thread):
    """Interface defining the requirements of a drone (real, sym, mock) to produce data for a consumer"""
    def __init__(self, data_channel: DataChannel):
        threading.Thread.__init__(self, daemon=True)
        assert isinstance(data_channel, DataChannel), f"queue must inherit ActionsQueue: {type(data_channel)}"
        self._data_channel = data_channel

    @property
    def data_channel(self) -> DataChannel:
        """The data queue where the data is inserted"""
        return self._data_channel

    @abstractmethod
    def get_raw_data(self) -> DataItem:
        """gets the raw data from the actual drone"""

    @abstractmethod
    def is_streaming(self) -> bool:
        """checks if the drone is connected and streaming or not"""

    def run(self):
        while self.is_streaming():
            raw_data = self.get_raw_data()
            logger.debug2("Received raw_data: "
                          f"'{ {k: lo(v) if isinstance(v, np.ndarray) else v for k, v in raw_data.items() } }' ")
            self.data_channel.put(raw_data)

class DataConsumer(ABC):
    """Interface defining the requirements of a data consumer getting data from a DataProducer"""
    def __init__(self, data_channel: DataChannel):
        self._data_channel = data_channel

    @property
    def data_channel(self) -> DataChannel:
        """The data queue where the data is inserted"""
        return self._data_channel

    def wait_for_initial_data(self, timeout_s: float = 5, sleep_duration_s: float = 0.1):
        """wait for the data channel to be populated by a data producer"""
        n_waits = 0
        while not self.data_channel.has_data():
            time.sleep(sleep_duration_s)
            n_waits += 1
            if n_waits > timeout_s / sleep_duration_s:
                raise ValueError(f"Data was not produced for {timeout_s} seconds")

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
