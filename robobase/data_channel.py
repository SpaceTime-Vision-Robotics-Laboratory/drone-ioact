"""data_channel.py - Thread-safe channel to place perception data from the data modules"""
from copy import deepcopy
from typing import Callable
from datetime import datetime
import threading
import numpy as np

from robobase.types import DataItem
from robobase.utils import logger

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
            logger.trace("Received item: "
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