"""screen_displayer.py - This module reads the data from a drone and prints the RGB. No action is produced"""
from __future__ import annotations
import os
from datetime import datetime
from typing import Callable
from overrides import overrides
import numpy as np

from robobase import DataChannel, DataItem, BaseController, ActionsQueue, Action
from roboimpl.utils import image_resize, logger

from .screen_displayer_utils import DisplayerState
from .screen_displayer_tkinter import ScreenDisplayerTkinter
from .screen_displayer_cv2 import ScreenDisplayerCV2

INITIAL_TIMEOUT_S = 60
TIMEOUT_S = 0.01
INITIAL_RESOLUTION_FALLBACK = (480, 640)
DEFAULT_BACKEND = os.getenv("ROBOIMPL_SCREEN_DISPLAYER_BACKEND", "cv2")

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
        self.backend_type = backend or DEFAULT_BACKEND
        self.screen_frame_callback = screen_frame_callback or ScreenDisplayer.rgb_only_displayer
        assert all(isinstance(a, Action) for a in k2a.values()), [(a, type(a)) for a in k2a.values()]
        assert all(v.name in actions_queue.action_names for v in k2a.values()), f"\n-{k2a=}\n-Actions: {actions_queue}"
        assert self.toggle_info_key not in k2a, f"{self.toggle_info_key=} clash with {key_to_action=}"
        assert self.backend_type in ("tkinter", "cv2", ), self.backend_type

        self.backend = {
            "tkinter": lambda: ScreenDisplayerTkinter(),
            "cv2": lambda: ScreenDisplayerCV2(),
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

        logger.log_every_s(f"Pressed '{event}'. Pushing: {action} to the actions queue.", "DEBUG", True)
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
        self.data_channel_event.wait(INITIAL_TIMEOUT_S)

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
            data_events = self.data_channel_event.wait(timeout=TIMEOUT_S) # data events: new frame arived
            if not ui_events and not data_events:
                continue
            logger.log_every_s(f"Updating UI: {ui_events=}, {data_events=}", "DEBUG", log_to_next_level=True)

            self.data_channel_event.clear() # if green, make it red again
            curr_data, _ = self.data_channel.get(return_copy=False)

            frame = self.screen_frame_callback(curr_data)
            if frame is None:
                continue
            frame_rsz = image_resize(frame, height=new_state.resolution[0], width=new_state.resolution[1],
                                     interpolation="nearest") # can be noop. 'nearest' for max speed.
            for event in self.backend.poll_events(): # little hack to get more keyboard events polled before this call
                self._on_event(event)
            self.backend.update_frame(frame_rsz)

            old_state = new_state
            fpss.append((datetime.now() - old_state.ts).total_seconds())

        self.backend.close_window()
        logger.warning("ScreenDisplayer thread stopping")
