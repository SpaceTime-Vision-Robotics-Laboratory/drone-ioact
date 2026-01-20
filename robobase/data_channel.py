"""data_channel.py - Thread-safe channel to place perception data from the data modules"""
from __future__ import annotations
from copy import deepcopy
import os
from typing import Callable
from datetime import datetime
import threading
import time
from queue import Queue, Empty
from pathlib import Path
import numpy as np

from robobase.types import DataItem
from robobase.utils import logger

DATA_STORER_QUEUE_MAXSIZE = 100
SLEEP_INTERVAL = 0.01

class DataChannelClosedError(ValueError): pass # pylint: disable=all # noqa

class _DataStorer(threading.Thread):
    """internal thread for storing DataChannel data"""
    def __init__(self, data_channel: DataChannel, path: Path):
        threading.Thread.__init__(self, daemon=True)
        assert not path.exists() or len(list(path.iterdir())) == 0, f"Path '{path}' exists."
        path.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.data_queue = Queue(maxsize=DATA_STORER_QUEUE_MAXSIZE)
        self.data_channel = data_channel

    def push(self, data: dict[str, DataItem]):
        """push a data item to the data storer queue so it's later stored on disk"""
        self.data_queue.put({"data": data, "timestamp": datetime.now().isoformat()})

    def run(self):
        while True:
            try:
                x = self.data_queue.get_nowait()
                np.save(pth := f"{self.path}/{x['timestamp']}", x["data"])
                logger.trace(f"Stored at '{pth}'")
            except Empty:
                time.sleep(SLEEP_INTERVAL)
                logger.trace("Empty queue on DataStorer")

class DataChannel:
    """DataChannel defines the thread-safe data structure where the data producer writes the data and consumers read"""
    def __init__(self, supported_types: list[str], eq_fn: Callable[[DataItem, DataItem], bool],
                 log_path: Path | None = None, store_logs: bool = os.getenv("DATA_CHANNEL_STORE_LOGS", "0") == "1"):
        assert len(supported_types) > 0, "cannot have a data channel that supports no data type (i.e. rgb, pose etc.)"
        self.supported_types = set(supported_types)
        self.eq_fn = eq_fn
        self.log_path = log_path or Path(logger.get_file_handler().file_path).parent / "DataChannel"
        self.store_logs = store_logs

        self._lock = threading.Lock()
        self._data: dict[str, DataItem] = {}
        self._is_closed = False

        self._data_storer = None
        if store_logs:
            logger.info(f"Storing DataChannel logs at '{self.log_path}'")
            self._data_storer = _DataStorer(self, self.log_path)
            self._data_storer.start()

    def is_open(self) -> bool:
        """check is the channel is open. Used by other data producers to whether they can continue or not"""
        return not self._is_closed

    def put(self, item: dict[str, DataItem]):
        """Put data into the queue"""
        assert isinstance(item, dict), type(item)
        assert (ks := set(item.keys())) == (st := self.supported_types), f"Data keys: {ks} vs. Supported types: {st}"
        with self._lock:
            if not self.is_open():
                raise DataChannelClosedError("Channel is closed, cannot put data.")
            if self._data_storer is not None: # for logging
                if self._data == {} or (self._data != {} and not self.eq_fn(item, self._data)):
                    self._data_storer.push(item) # only push differnt items according to eq_fn
                    logger.trace(
                        "Received new item: "
                        f"'{ {k: v.shape if isinstance(v, np.ndarray) else type(v) for k, v in item.items() } }'"
                    )
            self._data = item

    def get(self) -> dict[str, DataItem]:
        """Return the item from the channel"""
        with self._lock:
            assert self.is_open(), "Cannot get data from a closed chanel"
            return deepcopy(self._data)

    def has_data(self) -> bool:
        """Checks if the channel has data"""
        with self._lock:
            return len(self._data) > 0 and self.is_open()

    def close(self):
        """Closes the channel"""
        with self._lock:
            self._is_closed = True
        if self._data_storer is not None and (n := self._data_storer.data_queue.qsize()) > 0:
            logger.info(f"Waiting for DataChannel to write {n} left data logs to '{self._data_storer.path}'")
            while self._data_storer.data_queue.qsize() > 0:
                time.sleep(SLEEP_INTERVAL)

    def __repr__(self) -> str:
        return f"[DataChannel] Types: {self.supported_types}. Has data: {self.has_data()}. Open: {self.is_open()}."
