"""
interfaces.py - Interfaces for interacting with the data produced by a drone. The usual flow is like this:
Drone --raw data--> DroneIn --get_current_data()--> DataConsumer1            | <--a_q.pop()-- DroneOut --action-- Drone
                                                    DC2 & ActionsProducer1 --|
                                                    DC3                      |
                                                    DC4 & ActionsProducer2 --|
                                                    ...
DroneIn can be seen as DataProducer and DroneOut as ActionsConsumer, so it's two producer-consumers on each side.
"""
from abc import ABC, abstractmethod
from queue import Queue
import numpy as np

Action = str # actions are stored as simple strings for simplicity :)

class ActionsQueue(ABC):
    """Interface defining the actions understandable by a drone and the application. Queue must be thread-safe!"""
    def __init__(self, queue: Queue):
        super().__init__()
        self.queue = queue

    @abstractmethod
    def get_actions(self) -> list[Action]:
        """the valid actions defined for this application"""

    def put(self, item: Action, *args, **kwargs):
        """Put an item into the queue"""
        assert isinstance(item, Action), type(item)
        assert item in (actions := self.get_actions()), f"{item} not in {actions}"
        self.queue.put(item, *args, **kwargs)

    def get(self, *args, **kwargs) -> Action:
        """Remove and return an item from the queue"""
        return self.queue.get(*args, **kwargs)

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
        self._drone_in = drone_in

    @property
    def drone_in(self) -> DroneIn:
        """The DroneIn instance from which data is created"""
        return self._drone_in

class ActionsProducer(ABC):
    """Interface defining the requirements of an actions producer (i.e. sending to a DroneOut)"""
    def __init__(self, actions_queue: ActionsQueue):
        assert isinstance(actions_queue, ActionsQueue), f"queue must inherit ActionsQueue: {type(actions_queue)}"
        self._actions_queue = actions_queue

    @property
    def actions_queue(self) -> Queue:
        """The actions queue where the actions are inserted"""
        return self._actions_queue

class DroneOut(ABC):
    """Interface defining the requirements of a drone (real, sym, mock) to receive an action & apply it to the drone"""
    def __init__(self, actions_queue: ActionsQueue):
        assert isinstance(actions_queue, ActionsQueue), f"queue must inherit ActionsQueue: {type(actions_queue)}"
        self._actions_queue = actions_queue

    @property
    def actions_queue(self) -> Queue:
        """The actions queue where the actions are inserted"""
        return self._actions_queue
