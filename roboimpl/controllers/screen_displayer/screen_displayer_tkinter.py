"""screen_displayer_tkinter.py - Tkinter-based screen displayer"""
import tkinter as tk
from PIL import Image, ImageTk
import numpy as np
from overrides import overrides

from roboimpl.utils import logger
from .screen_displayer_utils import DisplayerBackend

class ScreenDisplayerTkinter(DisplayerBackend):
    """Tkinter-based screen displayer. The OG one, but lags unfortunetely on larger environments (keyboard drops)"""
    def __init__(self):
        # state of the canvas: initialized at startup time.
        self.root: tk.Tk | None = None
        self.canvas: tk.Canvas | None = None
        self.photo: ImageTk.PhotoImage | None = None
        self._pending_events: list[str] = []
        self._previous_resolution: tuple[int, int] = (0, 0)

    @overrides
    def initialize_window(self, height: int, width: int, title: str):
        """starts the tk window"""
        assert self.root is None, "cannot call twice"
        self.root = tk.Tk(className=f" {title}") # space for capital S
        self.canvas = tk.Canvas(self.root, height=height, width=width)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.focus_set()
        self.root.bind("<KeyRelease>", self._on_key_release)

    @overrides
    def get_current_size(self) -> tuple[int, int]:
        return self.canvas.winfo_height(), self.canvas.winfo_width()

    @overrides
    def poll_events(self) -> list[str]:
        self.root.update()
        events = self._pending_events
        self._pending_events = []
        if len(events) > 0:
            logger.log_every_s(f"Returning {len(events)} events", "DEBUG", True)
            if len(events) > 1:
                logger.error(f"Returning {len(events)} events")
        return events

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

    def _on_key_release(self, event: tk.Event):
        self._pending_events.append(event.keysym)
