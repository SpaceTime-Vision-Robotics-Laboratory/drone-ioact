"""screen_displayer_tkinter.py - Tkinter-based screen displayer. Uses pynput for multi-key support. Sadly global."""
import threading
import tkinter as tk
from PIL import Image, ImageTk
import numpy as np
from overrides import overrides

from .screen_displayer_utils import DisplayerBackend, Key, PYNPUT, make_keyboard_listener

class ScreenDisplayerTkinter(DisplayerBackend):
    """Tkinter-based screen displayer. The OG one, but lags unfortunetely on larger environments (keyboard drops)"""
    def __init__(self):
        # state of the canvas: initialized at startup time.
        self.root: tk.Tk | None = None
        self.canvas: tk.Canvas | None = None
        self.photo: ImageTk.PhotoImage | None = None
        self._previous_resolution: tuple[int, int] = (0, 0)
        self._pressed: set[Key] = set()
        self._key_event: threading.Event = None

    @overrides
    def initialize_window(self, height: int, width: int, title: str):
        """starts the tk window"""
        assert self.root is None, "cannot call twice"
        self.root = tk.Tk(className=f" {title}") # space for capital S
        self.canvas = tk.Canvas(self.root, height=height, width=width)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.focus_set()

        if PYNPUT:
            self._pressed, self._key_event = make_keyboard_listener()

    @overrides
    def get_current_size(self) -> tuple[int, int]:
        return self.canvas.winfo_height(), self.canvas.winfo_width()

    @overrides
    def poll_events(self) -> set[Key]:
        self.root.update()
        if not PYNPUT:
            return set()
        return self._pressed

    @property
    @overrides
    def key_event(self) -> threading.Event:
        return self._key_event

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
