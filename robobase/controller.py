"""controller.py - Interface between the DataConsumer's data and the next best action for the ActionsQueue"""
from __future__ import annotations
from abc import ABC
import time
import threading

from robobase.data_channel import DataChannel
from robobase.actions_queue import ActionsQueue, Action

class Controller(ABC, threading.Thread):
    """Interface defining the requirements of a data consumer getting data from a DataProducer"""
    def __init__(self, data_channel: DataChannel, actions_queue: ActionsQueue):
        threading.Thread.__init__(self, daemon=True)
        self._data_channel = data_channel
        self._actions_queue = actions_queue

    @property
    def data_channel(self) -> DataChannel:
        """The data queue where the data taken from"""
        return self._data_channel

    @property
    def actions_queue(self) -> ActionsQueue:
        """The actions where where the action is sent to"""
        return self._actions_queue

    def wait_for_initial_data(self, timeout_s: float = 5, sleep_duration_s: float = 0.1):
        """wait for the data channel to be populated by a data producer"""
        n_waits = 0
        while not self.data_channel.has_data():
            time.sleep(sleep_duration_s)
            n_waits += 1
            if n_waits > timeout_s / sleep_duration_s:
                raise ValueError(f"Data was not produced for {timeout_s} seconds")
