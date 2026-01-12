"""data_interfaces.py - Interfaces for interacting with the data produced by a DataProcuer in a DataChannel"""
from __future__ import annotations
from abc import ABC, abstractmethod
import time
import threading

from robobase.types import DataItem
from robobase.data_channel import DataChannel

class DataProducer(ABC, threading.Thread):
    """Interface defining the requirements of a drone (real, sym, mock) to produce data for a consumer"""
    def __init__(self, data_channel: DataChannel):
        threading.Thread.__init__(self, daemon=True)
        assert isinstance(data_channel, DataChannel), f"data_channel is of wrong type: {type(data_channel)}"
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
