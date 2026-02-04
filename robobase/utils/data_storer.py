"""data_storer.py A thread with a queue for storing data on disk as npz files"""
import threading
from typing import Any
from pathlib import Path
from datetime import datetime
from queue import Queue, Empty
import time
import numpy as  np

from .utils import logger

SLEEP_INTERVAL = 0.01
DATA_STORER_QUEUE_MAXSIZE = 100

class DataStorer(threading.Thread):
    """Thread that operates a queue for storing data from other threads i.e. DataChannel or ActionsQueue"""
    def __init__(self, path: Path):
        threading.Thread.__init__(self, daemon=True)
        assert not path.exists() or len(list(path.iterdir())) == 0, f"Path '{path}' exists."
        path.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.data_queue = Queue(maxsize=DATA_STORER_QUEUE_MAXSIZE)

    def push(self, data: Any, timestamp: datetime):
        """push a data item to the data storer queue so it's later stored on disk"""
        self.data_queue.put({"data": data, "timestamp": timestamp.isoformat()})

    def get_and_store(self):
        """gets one item fro mthe data queue and stores it to the disk"""
        x = self.data_queue.get_nowait()
        np.save(pth := f"{self.path}/{x['timestamp']}", x["data"])
        logger.trace(f"Stored at '{pth}'")

    def run(self):
        while True:
            try:
                self.get_and_store()
            except Empty:
                time.sleep(SLEEP_INTERVAL)
                logger.trace("Empty queue on DataStorer")
