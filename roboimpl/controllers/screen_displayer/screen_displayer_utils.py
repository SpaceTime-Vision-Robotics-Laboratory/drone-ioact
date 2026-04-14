"""screen_displayer_utils.py - common stuff for displayer backends"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
import numpy as np

@dataclass
class DisplayerState:
    """internal class representing the internal state of the UI to differentiate between data/actions updates and UI"""
    resolution: tuple[int, int]
    hud: bool
    ts: datetime = None

    def __post_init__(self):
        self.ts = datetime.now()

    def __eq__(self, other: DisplayerState):
        return self.resolution == other.resolution and self.hud == other.hud

class DisplayerBackend(ABC):
    """internal class representing the possible backends to display stuff to a windows from the controller thread"""
    @abstractmethod
    def initialize_window(self, height: int, width: int, title: str):
        """initializes the windows from within the running thread (not constructor from main thread)"""
    @abstractmethod
    def get_current_size(self) -> tuple[int, int]:
        """returns current (height, width) as a tuple"""
    @abstractmethod
    def poll_events(self):
        """Polls the events (key presses/releases) for displaying next frames."""
    @abstractmethod
    def update_frame(self, frame: np.ndarray):
        """update the screen with the new frame"""
    @abstractmethod
    def close_window(self):
        """closes and cleans up the window"""
