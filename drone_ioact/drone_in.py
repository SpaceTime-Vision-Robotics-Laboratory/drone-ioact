"""drone_in.py - Interface for interacting with the data produced by a drone"""
import numpy as np
from abc import ABC, abstractmethod

class DroneIn(ABC):
    @abstractmethod
    def get_current_data(self, timeout_s: int = 10) -> dict[str, np.ndarray]:
        """gets the data (RGB and maybe others) as a dict of numpy arrays"""

    @abstractmethod
    def is_streaming(self) -> bool:
        """checks if the drone is connected and streaming or not"""

    @abstractmethod
    def stop_streaming(self):
        """calls the drone to stop sending messages"""
