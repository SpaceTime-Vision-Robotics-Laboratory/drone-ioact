"""screen_displayer_utils.py - common stuff for displayer backends"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from datetime import datetime
import numpy as np

# pylint: disable=invalid-name
class Key(Enum):
    """Generic ScreenDisplayer keys across multiple backends (tkinter/cv2)"""
    locals().update({chr(c): auto() for c in range(ord("a"), ord("z") + 1)}) # generated a-z
    # add supported keys here!
    Left = auto()
    Up = auto()
    Right = auto()
    Down = auto()
    Esc = auto()
    Enter = auto()
    Space = auto()
    PageUp = auto()
    PageDown = auto()
    Comma = auto()
    Period = auto()

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
    def poll_events(self) -> list[Key]: # TODO: only supports key_release. We need a KeyEvent dataclass for more.
        """Polls the events (key presses) and returns them. In tkinter it calls update() + collects events manually"""
    @abstractmethod
    def update_frame(self, frame: np.ndarray):
        """update the screen with the new frame"""
    @abstractmethod
    def close_window(self):
        """closes and cleans up the window"""
