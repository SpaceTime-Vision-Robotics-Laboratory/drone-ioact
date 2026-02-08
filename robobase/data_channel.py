"""data_channel.py - Thread-safe channel to place perception data from the data modules"""
from __future__ import annotations
from copy import deepcopy
import os
from typing import Any
from datetime import datetime
import threading
import time
from pathlib import Path
import numpy as np

from robobase.types import DataItem, DataEqFn
from robobase.utils import logger, DataStorer

SLEEP_INTERVAL = 0.01

def _fmt(v: np.ndarray | Any) -> tuple | type:
    return v.shape if isinstance(v, np.ndarray) else type(v)

class DataChannelClosedError(ValueError): pass # pylint: disable=all # noqa

class DataChannel:
    """DataChannel defines the thread-safe data structure where the data producer writes the data and consumers read"""
    def __init__(self, supported_types: list[str], eq_fn: DataEqFn, log_path: Path | None = None):
        assert len(supported_types) > 0, "cannot have a data channel that supports no data type (i.e. rgb, pose etc.)"
        self.supported_types = set(supported_types)
        self.eq_fn = eq_fn
        self.log_path = DataChannel._make_log_path(log_path)

        self._lock = threading.Lock()
        self._data: dict[str, DataItem] = {}
        self._data_ts: datetime = datetime(1900, 1, 1)
        self._is_closed = False

        self._subscribers_events: list[threading.Event] = [] # a list of subscribers that are notified on data change

        self._data_storer = None
        if self.log_path is not None:
            logger.info(f"Storing DataChannel logs at '{self.log_path}'")
            self._data_storer = DataStorer(self.log_path)
            self._data_storer.start()

    def is_open(self) -> bool:
        """check is the channel is open. Used by other data producers to whether they can continue or not"""
        return not self._is_closed

    def put(self, item: dict[str, DataItem]):
        """Put data into the queue"""
        item_ts = datetime.now()
        assert isinstance(item, dict), type(item)
        assert (ks := set(item.keys())) == (st := self.supported_types), f"Data keys: {ks} vs. Supported types: {st}"
        with self._lock:
            if not self.is_open():
                raise DataChannelClosedError("Channel is closed, cannot put data.")

            if self._data == {} or (self._data != {} and not self.eq_fn(item, self._data)): # new data
                logger.log_every_s(f"New data ({item_ts}): '{ {k: _fmt(v) for k, v in item.items() } }'", "DEBUG")
                if self._data_storer is not None: # for logging
                    self._data_storer.push(item, item_ts) # only push differnt items according to eq_fn

                for subscriber_event in self._subscribers_events: # announce each 'subscriber' of new data too
                    subscriber_event.set()

            self._data = item
            self._data_ts = item_ts

    def get(self) -> tuple[dict[str, DataItem], datetime]:
        """Return the current item from the channel + its the timestamp when it was received"""
        with self._lock:
            assert self.is_open(), "Cannot get data from a closed chanel"
            return deepcopy(self._data), deepcopy(self._data_ts)

    def has_data(self) -> bool:
        """Checks if the channel has data"""
        with self._lock:
            return len(self._data) > 0 and self.is_open()

    def close(self):
        """Closes the channel"""
        with self._lock:
            self._is_closed = True
            for subscriber_event in self._subscribers_events:
                subscriber_event.set() # set green light so the subscribers don't block forever
        if self._data_storer is not None:
            if (n := self._data_storer.data_queue.qsize()) > 0:
                logger.info(f"Waiting for DataChannel to write {n} left data logs to '{self._data_storer.path}'")
                while self._data_storer.data_queue.qsize() > 0:
                    time.sleep(SLEEP_INTERVAL)
            self._data_storer.close()

    def subscribe(self) -> threading.Event:
        """subscribe to this data channel, receiving a threading.Event object"""
        with self._lock:
            self._subscribers_events.append(res := threading.Event())
        return res

    def _make_log_path(log_path: Path | None) -> Path | None:
        if log_path is None:
            res = None
            if os.getenv("DATA_CHANNEL_STORE_LOGS", "0") == "1":
                res = Path(logger.get_file_handler().file_path).parent / "DataChannel"
                logger.debug("DATA_CHANNEL_STORE_LOGS=1 detected. Storing logs.")
            return res
        return log_path / "DataChannel" if log_path.name != "DataChannel" else log_path

    def __repr__(self) -> str:
        return f"[DataChannel] Types: {self.supported_types}. Has data: {self.has_data()}. Open: {self.is_open()}."
