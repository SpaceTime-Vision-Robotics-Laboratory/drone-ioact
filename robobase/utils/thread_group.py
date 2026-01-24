"""thread_group.py"""
from __future__ import annotations
import threading

from .utils import logger

class ThreadGroup(dict):
    """Thread group is a utility dictionary container (str->thread) for managing many threads at once"""
    def __init__(self, threads: dict[str, threading.Thread] | None = None):
        super().__init__(**(threads or {}))
        assert all(isinstance(v, threading.Thread) for v in self.values()), f"Not all are threads: {self.items()}"

    def start(self) -> ThreadGroup:
        """starts all the threads"""
        for k, v in self.items():
            assert isinstance(v, threading.Thread), f"{k=}, {type(v)=}"
            if not v.daemon:
                logger.warning(f"Thread '{k}' is not a daemon. This is needed to kill it from main. Setting to true")
                v.daemon = True
            logger.debug(f"Starting thread '{k}'")
            v.start()
        return self

    def status(self) -> list[bool]:
        """Returns the status (is alive) of all threads"""
        return [t.is_alive() for t in self.values()]

    def is_any_dead(self) -> bool:
        """checks if any thread is dead"""
        return any(not t.is_alive() for t in self.values())

    def join(self, timeout: float | None=1.0):
        """joins all the threads"""
        logger.debug(f"Joining threads:\n{self}")
        for k, v in self.items():
            logger.debug(f"Joining thread '{k}' (timeout: {timeout})")
            if hasattr(v, "close"):
                v.close()
            v.join(timeout)

    def items(self) -> list[tuple[str, threading.Thread]]:
        """override to return the items as a list for simplicity and type hints"""
        return list(super().items())

    def values(self) -> list[threading.Thread]:
        """override to return the values as a list for simplicity and type hints"""
        return list(super().values())

    def __repr__(self):
        return f"ThreadGroup ({len(self)}): {'|'.join(f'- {k}: Is alive? {v.is_alive()}' for k, v in self.items())}"

    def __str__(self):
        return "\n".join(f"- {k}: Is alive? {v.is_alive()}" for k, v in self.items())
