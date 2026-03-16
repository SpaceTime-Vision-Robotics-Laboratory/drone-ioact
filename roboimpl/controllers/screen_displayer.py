"""screen_displayer.py - This module reads the data from a drone and prints the RGB. No action is produced"""
from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import datetime
import tkinter as tk
from typing import Callable
from dataclasses import dataclass
from PIL import Image, ImageTk
from overrides import overrides
import numpy as np

from robobase import DataChannel, DataItem, BaseController, ActionsQueue, Action
from roboimpl.utils import image_resize, logger

TIMEOUT_S = 1000
TKINTER_SLEEP_S = 0.01
INITIAL_RESOLUTION_FALLBACK = (480, 640)

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
    def poll_events(self) -> list[str]: # TODO: only supports key_release. We need a KeyEvent dataclass for more.
        """Polls the events (key presses) and returns them. In tkinter it calls update() + collects events manually"""
    @abstractmethod
    def update_frame(self, frame: np.ndarray):
        """update the screen with the new frame"""
    @abstractmethod
    def close_window(self):
        """closes and cleans up the window"""

class TkinterBackend(DisplayerBackend):
    """Tkinter-based screen displayer. The OG one, but lags unfortunetely on larger environments (kb drops)"""
    def __init__(self):
        # state of the canvas: initialized at startup time.
        self.root: tk.Tk | None = None
        self.canvas: tk.Canvas | None = None
        self.photo: ImageTk.PhotoImage | None = None
        self._pending_events: list[str] = []
        self._previous_resolution: tuple[int, int] = (0, 0)

    def initialize_window(self, height: int, width: int, title: str):
        """starts the tk window"""
        assert self.root is None, "cannot call twice"
        self.root = tk.Tk(className=f" {title}") # space for capital S
        self.canvas = tk.Canvas(self.root, height=height, width=width)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.focus_set()
        self.root.bind("<KeyRelease>", self._on_key_release)

    def get_current_size(self) -> tuple[int, int]:
        return self.canvas.winfo_height(), self.canvas.winfo_width()

    def poll_events(self) -> list[str]:
        self.root.update()
        events = self._pending_events
        self._pending_events = []
        return events

    def update_frame(self, frame: np.ndarray):
        if self._previous_resolution != (current_resolution := self.get_current_size()):
            self.photo = ImageTk.PhotoImage(Image.fromarray(frame))
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
        else:
            self.photo.paste(Image.fromarray(frame))
        self._previous_resolution = current_resolution

    def close_window(self):
        self.root.destroy()

    def _on_key_release(self, event: tk.Event):
        self._pending_events.append(event.keysym)

class ScreenDisplayer(BaseController):
    """ScreenDisplayer provides support for displaying the DataChannel at each frame + support for keyboard actions."""
    def __init__(self, data_channel: DataChannel, actions_queue: ActionsQueue,
                 resolution: tuple[int, int] | None = None,
                 screen_frame_callback: Callable[[DataItem], np.ndarray | None] | None = None,
                 key_to_action: dict[str, Action] | None = None,
                 toggle_info_key: str | None = None, backend: str | None = None):
        super().__init__(data_channel=data_channel, actions_queue=actions_queue)
        self.initial_resolution = resolution
        self.key_to_action = k2a = key_to_action or {}
        self.toggle_info_key = toggle_info_key or "i"
        self.backend_type = backend or "tkinter"
        self.screen_frame_callback = screen_frame_callback or ScreenDisplayer.rgb_only_displayer
        assert all(isinstance(a, Action) for a in k2a.values()), [(a, type(a)) for a in k2a.values()]
        assert all(v.name in actions_queue.action_names for v in k2a.values()), f"\n-{k2a=}\n-Actions: {actions_queue}"
        assert self.toggle_info_key not in k2a, f"{self.toggle_info_key=} clash with {key_to_action=}"
        assert self.backend_type in ("tkinter", )

        self.backend = {
            "tkinter": lambda: TkinterBackend(),
        }[self.backend_type]()

    @staticmethod
    def rgb_only_displayer(data: dict[str, DataItem]) -> np.ndarray:
        """returns the final frame as RGB from the current data (rgb, semantic etc.)"""
        return data["rgb"]

    def add_to_queue(self, action: Action):
        """pushes an action to queue. Separate method so we can easily override it (i.e. priority queue put)"""
        self.actions_queue.put(action, data_ts=None, block=True)

    def _on_event(self, event: str): # Note: only key_release events, see todo.
        if event == self.toggle_info_key:
            logger.debug(f"Pressed '{event}' (key info). TODO: not implemented")
            return

        action: Action | None = self.key_to_action.get(event)
        if action is None:
            logger.debug(f"Unused char: {event}")
            return

        logger.debug(f"Pressed '{event}'. Pushing: {action} to the actions queue.")
        self.add_to_queue(action)

    def _get_initial_height_width(self, prev_data: dict[str, DataItem]) -> tuple[int, int]:
        """try hard to get the initial h,w. Either provided in ctor, from data (if 'rgb' is found) or default"""
        if self.initial_resolution is not None:
            return self.initial_resolution
        if "rgb" in prev_data:
            return prev_data["rgb"].shape[0:2]
        return INITIAL_RESOLUTION_FALLBACK

    @overrides
    def run(self):
        self.data_channel_event.wait(TIMEOUT_S)

        height, width = self._get_initial_height_width(prev_data=self.data_channel.get()[0])
        self.backend.initialize_window(height, width, title="Screen Displayer")

        old_state = DisplayerState(self.backend.get_current_size(), hud=False)
        fpss = [1 / 30] # start with default value to not skew the results.

        while self.data_channel.has_data():
            for event in self.backend.poll_events():
                self._on_event(event)
            fpss = fpss[-100:] if len(fpss) > 1000 else fpss # poor man's circular buffer
            logger.log_every_s(f"FPS: {len(fpss) / sum(fpss):.2f}", "INFO")
            new_state = DisplayerState(resolution=self.backend.get_current_size(), hud=False)

            ui_events = new_state != old_state # UI events i.e. resize or toggle info
            data_events = self.data_channel_event.wait(timeout=TKINTER_SLEEP_S) # data events: new frame arived
            if not ui_events and not data_events:
                continue
            logger.log_every_s(f"Updating UI: {ui_events=}, {data_events=}", "DEBUG", log_to_next_level=True)

            self.data_channel_event.clear() # if green, make it red again
            curr_data, _ = self.data_channel.get(return_copy=False)

            frame = self.screen_frame_callback(curr_data)
            if frame is None:
                continue
            frame_rsz = image_resize(frame, height=new_state.resolution[0], width=new_state.resolution[1]) # can be noop
            self.backend.update_frame(frame_rsz)

            old_state = new_state
            fpss.append((datetime.now() - old_state.ts).total_seconds())

        self.backend.close_window()
        logger.warning("ScreenDisplayer thread stopping")
