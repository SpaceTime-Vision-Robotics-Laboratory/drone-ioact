"""data_interfaces.py - Interfaces for interacting with the data produced by a DataProcuer in a DataChannel"""
from __future__ import annotations
from abc import ABC, abstractmethod
from copy import deepcopy
from typing import Callable
import time
from datetime import datetime
import threading
import numpy as np

from drone_ioact.utils import logger

DataItem = dict[str, np.ndarray | int | str | float]

class DataChannel:
    """DataChannel defines the thread-safe data structure where the data producer writes the data and consumers read"""
    def __init__(self, supported_types: list[str], eq_fn: Callable[[DataItem, DataItem], bool]):
        assert len(supported_types) > 0, "cannot have a data channel that supports no data type (i.e. rgb, pose etc.)"
        self.supported_types = set(supported_types)
        self.eq_fn = eq_fn
        self.timestamp = "1900-01-01" # only used for debugging and logging. Don't use it for equality or logic!

        self._lock = threading.Lock()
        self._data: DataItem = {}
        self._is_closed = False

    def put(self, item: DataItem):
        """Put data into the queue"""
        assert isinstance(item, dict), type(item)
        assert (ks := set(item.keys())) == (st := self.supported_types), f"Data keys: {ks} vs. Supported types: {st}"
        with self._lock:
            assert not self._is_closed, "Cannot put data in a closed chanel"
            if self._data == {} or not self.eq_fn(item, self._data):
                self.timestamp = datetime.now().isoformat()
            self._data = item
            logger.debug3("Received item: "
                          f"'{ {k: v.shape if isinstance(v, np.ndarray) else type(v) for k, v in item.items() } }'")

    def get(self) -> DataItem:
        """Return the item from the channel"""
        with self._lock:
            assert not self._is_closed, "Cannot get data from a closed chanel"
            return deepcopy(self._data)

    def has_data(self) -> bool:
        """Checks if the channel has data"""
        with self._lock:
            return len(self._data) > 0 and not self._is_closed

    def close(self):
        """Closes the channel"""
        assert self.has_data(), "cannot call close before any data was received"
        with self._lock:
            self._is_closed = True

    def __repr__(self) -> str:
        return f"[DataChannel] Types: {self.supported_types}. Timestamp: {self.timestamp}"

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
