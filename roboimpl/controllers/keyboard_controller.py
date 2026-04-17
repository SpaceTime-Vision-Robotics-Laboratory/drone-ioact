"""keyboard_controller.py - Generic multi-key keyboard controller for robobase"""
from typing import Callable
from enum import Enum, auto
from datetime import datetime
import time
from robobase import BaseController, Action, ActionsQueue, DataChannel
from robobase.controller import INITIAL_DATA_MAX_DURATION_S
from roboimpl.utils import logger

FREQ = 30 # poll keyboard events 30 times per second.

# pylint: disable=invalid-name
class Key(Enum):
    """Generic robobase keys across multiple backends (pynput now, SDL2 later)"""
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

KeyboardFn = Callable[[set[Key]], list[Action]] # keys -> (generic) actions

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

def make_keyboard_listener() -> set[Key]:
    """starts a keyboard listener thread and returns a set attached to this listener"""
    pressed = set()

    def _on_press(k):
        k_code = k.char if hasattr(k, "char") else k
        if (key := _PYNPUT_KEYCODE_MAP.get(k_code)) is not None:
            pressed.add(key)

    def _on_release(k):
        k_code = k.char if hasattr(k, "char") else k
        if (key := _PYNPUT_KEYCODE_MAP.get(k_code)) is not None:
            pressed.discard(key)

    keyboard.Listener(on_press=_on_press, on_release=_on_release).start()
    return pressed

class KeyboardController(BaseController):
    """Generic multi-key keyboard controller for robobase"""
    def __init__(self, data_channel: DataChannel, actions_queue: ActionsQueue, keyboard_fn: KeyboardFn = None,
                 key_to_action: dict[Key, Action] | None = None):
        self.pressed = None
        if key_to_action is not None:
            assert keyboard_fn is None, f"key_to_action cannot be set if keyboard_fn is also set"
        super().__init__(data_channel, actions_queue)
        self.keyboard_fn = keyboard_fn or self._keyboard_fn
        self.key_to_action = key_to_action or {}

    def run(self):
        """default data polling scheduling"""
        assert PYNPUT, "cannot run KeyboardController if pynput is not installed" # like this so we can test it
        self.pressed = make_keyboard_listener()
        self.data_channel_event.wait(INITIAL_DATA_MAX_DURATION_S) # wait for initial data
        prev = datetime.now()
        while self.data_channel.has_data():
            now = datetime.now()
            diff = (now - prev).total_seconds()
            prev = now

            actions: list[Action] = self.keyboard_fn(self.pressed)
            for action in actions:
                self.actions_queue.put(action, data_ts=None)

            time.sleep(max(0, (1 / FREQ) - diff))

    def _keyboard_fn(self, pressed: set[Key]) -> list[Action]:
        res: list[Action] = []
        for key in pressed:
            if (action := self.key_to_action.get(key)) is not None:
                res.append(action)
        if len(pressed) > 0:
            logger.log_every_s(f"Pressed '{pressed}'. Returning: {res}", "INFO", True)
        return res
