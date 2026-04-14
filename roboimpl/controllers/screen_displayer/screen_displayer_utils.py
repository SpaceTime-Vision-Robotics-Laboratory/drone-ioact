"""screen_displayer_utils.py - common stuff for displayer backends"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from datetime import datetime
import threading
import numpy as np

from roboimpl.utils import logger

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
    F1 = auto()
    F2 = auto()
    F3 = auto()
    F4 = auto()
    F5 = auto()
    F6 = auto()
    F7 = auto()
    F8 = auto()
    F9 = auto()
    F10 = auto()
    F11 = auto()
    F12 = auto()

try:
    from pynput import keyboard
    PYNPUT = True
    _PYNPUT_KEYCODE_MAP: dict[str | keyboard.Key, Key] = {
        **{chr(k): getattr(Key, chr(k)) for k in range(ord("a"), ord("z") + 1)},
        keyboard.Key.left: Key.Left, keyboard.Key.right: Key.Right,
        keyboard.Key.down: Key.Down, keyboard.Key.up: Key.Up,
        keyboard.Key.esc: Key.Esc, keyboard.Key.enter: Key.Enter, keyboard.Key.space: Key.Space,
        keyboard.Key.page_up: Key.PageUp, keyboard.Key.page_down: Key.PageDown,
        keyboard.Key.f1: Key.F1, keyboard.Key.f2: Key.F2, keyboard.Key.f3: Key.F3, keyboard.Key.f4: Key.F4,
        keyboard.Key.f5: Key.F5, keyboard.Key.f6: Key.F6, keyboard.Key.f7: Key.F7, keyboard.Key.f8: Key.F8,
        keyboard.Key.f9: Key.F9, keyboard.Key.f10: Key.F10, keyboard.Key.f11: Key.F11, keyboard.Key.f12: Key.F12,
    }
except ImportError:
    PYNPUT = False
    _PYNPUT_KEYCODE_MAP = None
    logger.error("pynput is not installed. Cannot use keyboard to control")


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
    def poll_events(self) -> set[Key]:
        """Polls the events (key presses/releases) and returns a set. keyboard_fn uses this for multi-key actions"""
    @property
    @abstractmethod
    def key_event(self) -> threading.Event:
        """a property to ensure that there are key events for the main loop"""
    @abstractmethod
    def update_frame(self, frame: np.ndarray):
        """update the screen with the new frame"""
    @abstractmethod
    def close_window(self):
        """closes and cleans up the window"""

def make_keyboard_listener() -> tuple[set[Key], threading.Event]:
    """starts a keyboard listener thread and returns a set attached to this listener"""
    pressed = set()
    event = threading.Event()

    def _on_press(k):
        k_code = k.char if hasattr(k, "char") else k
        if (key := _PYNPUT_KEYCODE_MAP.get(k_code)) is not None:
            pressed.add(key)
            event.set()

    def _on_release(k):
        k_code = k.char if hasattr(k, "char") else k
        if (key := _PYNPUT_KEYCODE_MAP.get(k_code)) is not None:
            pressed.discard(key)
            event.set()

    listener = keyboard.Listener(on_press=_on_press, on_release=_on_release)
    listener.start()
    return pressed, event
