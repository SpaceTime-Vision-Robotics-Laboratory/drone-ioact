"""generic utils file"""
from pathlib import Path
from datetime import datetime
import threading
from loggez import make_logger

def get_project_root() -> Path:
    """returns the project root"""
    return Path(__file__).parents[1]

logger = make_logger("DRONE", log_file=Path.cwd() / f"{get_project_root()}/logs/{datetime.now().isoformat()[0:-6]}.txt")

class ThreadGroup(dict):
    """Thread group is a utility dictionary container (str->thread) for managing many threads at once"""
    def __init__(self, threads: dict[str, threading.Thread]):
        super().__init__(**threads)
        assert all(isinstance(v, threading.Thread) for v in self.values()), f"Not all are threads: {self.items()}"
        assert len(self) > 0, "no threads provided"

    def start(self):
        """starts all the threads"""
        for k, v in self.items():
            logger.debug(f"Starting thread '{k}'")
            v.start()

    def status(self) -> list[bool]:
        """Returns the status (is alive) of all threads"""
        return [t.is_alive() for t in self.values()]

    def is_any_dead(self) -> bool:
        """checks if any thread is dead"""
        return any(not t.is_alive() for t in self.values())

    def join(self, timeout: float | None=None):
        """joins all the threads"""
        for k, v in self.items():
            logger.debug(f"Joining thread '{k}' (timeout: {timeout})")
            v.join(timeout)

    def items(self) -> list[tuple[str, threading.Thread]]:
        """override to return the items as a list for simplicity and type hints"""
        return list(super().items())

    def values(self) -> list[threading.Thread]:
        """override to return the values as a list for simplicity and type hints"""
        return list(super().values())

    def __repr__(self):
        return f"ThreadGroup ({len(self)}): {'|'.join(f'- {k}: {v.is_alive()}' for k, v in self.items())}"

    def __str__(self):
        return "\n".join(f"- {k}: {v.is_alive()}" for k, v in self.items())
