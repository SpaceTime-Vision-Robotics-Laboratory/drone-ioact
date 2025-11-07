"""drone_in.py - Interface for interacting with the data produced by a drone"""
import numpy as np
from queue import Queue
from abc import ABC, abstractmethod

class DroneIn(ABC):
    """Interface defining the requirements of a drone (real, sym, mock) to produce data for a consumer"""
    @abstractmethod
    def get_current_data(self, timeout_s: int = 10) -> dict[str, np.ndarray]:
        """gets the data (RGB and maybe others) as a dict of numpy arrays"""

    @abstractmethod
    def is_streaming(self) -> bool:
        """checks if the drone is connected and streaming or not"""

    @abstractmethod
    def stop_streaming(self):
        """calls the drone to stop sending messages"""

class DataConsumer(ABC):
    """Interface defining the requirements of a data consumer getting data from a DroneIn"""
    def __init__(self, drone_in: DroneIn):
        super().__init__()
        self._drone_in = drone_in

    @property
    def drone_in(self) -> DroneIn:
        """The DroneIn instance from which data is created"""
        return self._drone_in

class ActionsProducer(ABC):
    """Interface defining the requirements of an actions producer (i.e. sending to a DroneOut)"""
    def __init__(self, actions_queue: Queue):
        super().__init__()
        self._actions_queue = actions_queue

    @property
    def actions_queue(self) -> Queue:
        """The actions queue where the actions are inserted"""
        return self._actions_queue

class DroneOut(ABC):
    """Interface defining the requirements of a drone (real, sym, mock) to receive an action & apply it to the drone"""
    def __init__(self, actions_queue: Queue):
        super().__init__()
        self._actions_queue = actions_queue

    @property
    def actions_queue(self) -> Queue:
        """The actions queue where the actions are inserted"""
        return self._actions_queue
