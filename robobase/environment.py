"""environment.py - Script defining an interface for environments where a robot exists in"""
from abc import ABC, abstractmethod
import time
from datetime import datetime

class Environment(ABC):
    """Generic environment for robots."""
    def __init__(self, frequency: float | None = None):
        frequency = frequency or 2**31 # none is used in case we wrap other env, like olympe or gym
        assert frequency > 0 and isinstance(frequency, (int, float)), frequency
        self.frequency = frequency
        self._prev_time = datetime(1900, 1, 1)

    def freq_barrier(self):
        """sleeps for the amount of time required between two consuecitive runs to ensure at least 1/freq has passed"""
        diff = (1 / self.frequency) - ((now := datetime.now()) - self._prev_time).total_seconds()
        time.sleep(diff if diff > 0 else 0)
        self._prev_time = now

    @abstractmethod
    def get_state(self) -> dict:
        """
        Returns the state of this environment at the some time. A few very important aspects to consider:
        - Ensure that this call is blocking and you manage how it's updated. For example in GymEnvironment we use Events
        - Remember to deepcopy() the returned object or ensure immutability some other way so it's safe 'outside'
        """

    @abstractmethod
    def is_running(self) -> bool:
        """returns true if this environment is running"""

    @abstractmethod
    def get_modalities(self) -> list[str]:
        """The list of raw modalities produced by this environment"""
