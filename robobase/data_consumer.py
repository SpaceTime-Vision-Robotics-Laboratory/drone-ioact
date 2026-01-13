"""data_consumer.py - Interfaces for DataConsumer which takes data from the DataChannel to be processed into Actions"""
from __future__ import annotations
from abc import ABC
import time

from robobase.data_channel import DataChannel

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
