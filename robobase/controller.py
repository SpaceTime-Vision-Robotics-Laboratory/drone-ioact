"""controller.py - Interface between the DataConsumer's data and the next best action for the ActionsQueue"""
from __future__ import annotations
from typing import Callable
from overrides import overrides
import time
import threading

from robobase.utils import logger
from robobase.types import DataItem, Action
from robobase.data_channel import DataChannel
from robobase.actions_queue import ActionsQueue

INITIAL_DATA_MAX_DURATION_S = 5
INITIAL_DATA_SLEEP_DURATION_S = 0.1
DATA_POLLING_INTERVAL_S = 1

class Controller(threading.Thread):
    """
    Interface defining the requirements of a data consumer getting data from a DataProducer.
    Users can extend this class and define their scheduling but the default behavior is to provide a controller fn
    and use the default scheduling (data polling) provided in this library.
    """
    def __init__(self, data_channel: DataChannel, actions_queue: ActionsQueue,
                 controller_fn: Callable[[dict[str, DataItem]], Action],
                 initial_data_max_duration_s: float = INITIAL_DATA_MAX_DURATION_S,
                 initial_data_sleep_duration_s: float = INITIAL_DATA_SLEEP_DURATION_S,
                 data_polling_interval_s: float = DATA_POLLING_INTERVAL_S):
        assert isinstance(controller_fn, Callable), type(controller_fn)
        threading.Thread.__init__(self, daemon=True)
        self._data_channel = data_channel
        self._actions_queue = actions_queue
        self.controller_fn = controller_fn
        self.initial_data_max_duration_s = initial_data_max_duration_s
        self.initial_data_sleep_duration_s = initial_data_sleep_duration_s

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

    @overrides
    def run(self):
        """default data polling scheduling"""
        self.wait_for_initial_data(timeout_s=self.initial_data_sleep_duration_s)
        prev_data = curr_data = self.data_channel.get()
        while self.data_channel.has_data():
            curr_data = self.data_channel.get()
            if self.data_channel.eq_fn(prev_data, curr_data):
                logger.log_every_s("Previous data equals to current data. Skipping.")
                time.sleep(DATA_POLLING_INTERVAL_S)
                continue
            action: Action = self.controller_fn(curr_data)
            self.actions_queue.put(action)
