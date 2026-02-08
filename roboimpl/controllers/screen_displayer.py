"""screen_displayer.py - This module reads the data from a drone and prints the RGB. No action is produced"""
from datetime import datetime
import tkinter as tk
from typing import Callable
from PIL import Image, ImageTk
from overrides import overrides
import numpy as np

from robobase import DataChannel, DataItem, BaseController, ActionsQueue, Action
from roboimpl.utils import image_resize, logger

TIMEOUT_S = 1000
TKINTER_SLEEP_S = 0.01
INITIAL_RESOLUTION_FALLBACK = (480, 640)

class ScreenDisplayer(BaseController):
    """ScreenDisplayer provides support for displaying the DataChannel at each frame + support for keyboard actions."""
    def __init__(self, data_channel: DataChannel, actions_queue: ActionsQueue,
                 resolution: tuple[int, int] | None = None,
                 screen_frame_callback: Callable[[DataItem], np.ndarray] | None = None,
                 key_to_action: dict[str, Action] | None = None):
        super().__init__(data_channel=data_channel, actions_queue=actions_queue)
        self.initial_resolution = resolution
        self.key_to_action = key_to_action = key_to_action or {}
        assert all(v in actions_queue.actions for v in self.key_to_action.values()), (key_to_action, actions_queue)
        self.screen_frame_callback = screen_frame_callback or ScreenDisplayer.rgb_only_displayer
        # state of the canvas: initialized at startup time.
        self.root: tk.Tk | None = None
        self.canvas: tk.Canvas | None = None
        self.photo: ImageTk.PhotoImage | None = None

    @staticmethod
    def rgb_only_displayer(data: dict[str, DataItem]) -> np.ndarray:
        """returns the final frame as RGB from the current data (rgb, semantic etc.)"""
        return data["rgb"]

    def add_to_queue(self, action: Action):
        """pushes an action to queue. Separate method so we can easily override it (i.e. priority queue put)"""
        self.actions_queue.put(action, block=True)

    def _on_key_release(self, event: tk.Event):
        action: Action | None = self.key_to_action.get(key := event.keysym)
        if action is None:
            logger.debug(f"Unused char: {key}")
            return
        logger.debug(f"Pressed '{key}'. Pushing: {action} to the actions queue.")
        self.add_to_queue(action)

    def _get_initial_height_width(self, prev_data: dict[str, DataItem]) -> tuple[int, int]:
        """try hard to get the initial h,w. Either provided in ctor, from data (if 'rgb' is found) or default"""
        if self.initial_resolution is not None:
            return self.initial_resolution
        if "rgb" in prev_data:
            return prev_data["rgb"].shape[0:2]
        return INITIAL_RESOLUTION_FALLBACK

    def _startup_tk(self, height: int, width: int):
        """starts the tk window"""
        assert self.root is None, "cannot call twice"
        self.root = tk.Tk(className=" Screen Displayer") # space for capital S
        self.canvas = tk.Canvas(self.root, height=height, width=width)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.focus_set()
        self.root.bind("<KeyRelease>", self._on_key_release)

    @overrides
    def run(self):
        self.data_channel_event.wait(TIMEOUT_S)

        prev_ts = datetime.now()
        height, width = self._get_initial_height_width(prev_data=self.data_channel.get()[0])
        self._startup_tk(height=height, width=width)
        prev_shape = (self.canvas.winfo_height(), self.canvas.winfo_width())

        fpss = [1 / 30] # start with default value to not skew the results.
        while self.data_channel.has_data():
            self.root.update()
            fpss = fpss[-100:] if len(fpss) > 1000 else fpss
            logger.log_every_s(f"FPS: {len(fpss) / sum(fpss):.2f}")

            if not self.data_channel_event.wait(timeout=TKINTER_SLEEP_S): # if red light (but non-blocking)
                continue

            self.data_channel_event.clear() # if green, make it red again
            curr_data, _ = self.data_channel.get()
            curr_shape = self.canvas.winfo_height(), self.canvas.winfo_width()

            frame = self.screen_frame_callback(curr_data)
            frame_rsz = image_resize(frame, height=curr_shape[0], width=curr_shape[1])
            if prev_shape != curr_shape:
                self.photo = ImageTk.PhotoImage(Image.fromarray(frame_rsz))
                self.canvas.delete("all")
                self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
            else:
                self.photo.paste(Image.fromarray(frame_rsz))

            prev_shape = curr_shape
            fpss.append((datetime.now() - prev_ts).total_seconds())
            prev_ts = datetime.now()

        self.root.destroy()
        logger.warning("ScreenDisplayer thread stopping")
