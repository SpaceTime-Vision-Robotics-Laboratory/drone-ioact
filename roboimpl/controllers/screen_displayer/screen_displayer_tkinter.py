"""screen_displayer_tkinter.py - Tkinter-based screen displayer. Uses pynput for multi-key support. Sadly global."""
import tkinter as tk
from PIL import Image, ImageTk
import numpy as np
from overrides import overrides

from .screen_displayer_utils import DisplayerBackend, Key

_TKINTER_KEY_MAP: dict[str, Key] = {
    **{chr(c): getattr(Key, chr(c)) for c in range(ord("a"), ord("z") + 1)},
    "Left": Key.Left, "Right": Key.Right, "Up": Key.Up, "Down": Key.Down,
    "Escape": Key.Esc, "Return": Key.Enter, "space": Key.Space,
    "Prior": Key.PageUp, "Next": Key.PageDown,
    "comma": Key.Comma, "period": Key.Period,
    "F1": Key.F1, "F2": Key.F2, "F3": Key.F3, "F4": Key.F4, "F5": Key.F5, "F6": Key.F6,
    "F7": Key.F7, "F8": Key.F8, "F9": Key.F9, "F10": Key.F10, "F11": Key.F11, "F12": Key.F12,
}

class ScreenDisplayerTkinter(DisplayerBackend):
    """Tkinter-based screen displayer. The OG one, but lags unfortunetely on larger environments (keyboard drops)"""
    def __init__(self):
        # state of the canvas: initialized at startup time.
        self.root: tk.Tk | None = None
        self.canvas: tk.Canvas | None = None
        self.photo: ImageTk.PhotoImage | None = None
        self._previous_resolution: tuple[int, int] = (0, 0)
        self._pressed_key = None

    @overrides
    def initialize_window(self, height: int, width: int, title: str):
        assert self.root is None, "cannot call twice"
        self.root = tk.Tk(className=f" {title}") # space for capital S
        self.canvas = tk.Canvas(self.root, height=height, width=width)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.focus_set()

        self.canvas.bind("<KeyPress>", self._on_key_press)
        self.canvas.bind("<KeyRelease>", self._on_key_release)

    @overrides
    def get_current_size(self) -> tuple[int, int]:
        return self.canvas.winfo_height(), self.canvas.winfo_width()

    @overrides
    def poll_events(self):
        self.root.update()

    @overrides
    def get_pressed_keys(self) -> set[Key]:
        return {self._pressed_key} if self._pressed_key is not None else set()

    @overrides
    def update_frame(self, frame: np.ndarray):
        if self._previous_resolution != (current_resolution := self.get_current_size()):
            self.photo = ImageTk.PhotoImage(Image.fromarray(frame))
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
        else:
            self.photo.paste(Image.fromarray(frame))
        self._previous_resolution = current_resolution

    @overrides
    def close_window(self):
        self.root.destroy()

    def _on_key_press(self, event):
        if (key := _TKINTER_KEY_MAP.get(event.keysym)) is not None:
            self._pressed_key = key

    def _on_key_release(self, event):
        if _TKINTER_KEY_MAP.get(event.keysym) == self._pressed_key:
            self._pressed_key = None
