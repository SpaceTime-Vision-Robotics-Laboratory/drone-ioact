"""screen_displayer.py - This module reads the data from a drone and prints the RGB. No action is produced"""
import threading
from datetime import datetime
import tkinter as tk
from typing import Callable
from PIL import Image, ImageTk
import numpy as np

from drone_ioact import DataChannel, DataConsumer, DataItem, ActionsProducer, ActionsQueue, Action
from drone_ioact.utils import logger, image_resize, log_debug_every_s

class ScreenDisplayer(DataConsumer, ActionsProducer, threading.Thread):
    """ScreenDisplayer provides support for displaying the DataChannel at each frame + support for keyboard actions."""
    def __init__(self, data_channel: DataChannel, actions_queue: ActionsQueue, screen_height: int | None = None,
                 screen_frame_callback: Callable[[DataItem], np.ndarray] | None = None,
                 key_to_action: dict[str, Action] | None = None):
        DataConsumer.__init__(self, data_channel)
        ActionsProducer.__init__(self, actions_queue)
        threading.Thread.__init__(self, daemon=True)
        self.initial_h = screen_height
        self.key_to_action = key_to_action or {}
        self.screen_frame_callback = screen_frame_callback or ScreenDisplayer.rgb_only_displayer
        # state of the canvas: initialized at startup time.
        self.root: tk.Tk | None = None
        self.canvas: tk.Canvas | None = None
        self.photo: ImageTk.PhotoImage | None = None

    @staticmethod
    def rgb_only_displayer(data: DataItem) -> np.ndarray:
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

    def _startup_tk(self, rgb_rsz: np.ndarray):
        """starts the tk window"""
        assert self.root is None, "cannot call twice"
        self.root = tk.Tk(className=" Screen Displayer") # space for capital S
        self.canvas = tk.Canvas(self.root, width=rgb_rsz.shape[1], height=rgb_rsz.shape[0])
        self.canvas.pack(fill="both", expand=True)
        self.canvas.focus_set()
        self.root.bind("<KeyRelease>", self._on_key_release)

    def run(self):
        prev_ts = start = datetime.now()
        self.wait_for_initial_data()
        prev_data = curr_data = self.data_channel.get()
        self._startup_tk(image_resize(curr_data["rgb"], height=self.initial_h or curr_data["rgb"].shape[0], width=None))
        prev_shape = (self.canvas.winfo_height(), self.canvas.winfo_width())

        fpss = []
        while self.data_channel.has_data():
            self.root.update()

            curr_data = self.data_channel.get()
            curr_shape = (self.canvas.winfo_height(), self.canvas.winfo_width())
            if self.data_channel.eq_fn(prev_data, curr_data) and prev_shape == curr_shape:
                logger.debug2(f"Not updating. Prev data equals to curr data and same shape: {curr_shape}")
                continue

            frame = self.screen_frame_callback(curr_data)
            frame_rsz = image_resize(frame, height=curr_shape[0], width=curr_shape[1])
            if prev_shape != curr_shape:
                self.photo = ImageTk.PhotoImage(Image.fromarray(frame_rsz))
                self.canvas.delete("all")
                self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
            else:
                self.photo.paste(Image.fromarray(frame_rsz))

            prev_data = curr_data
            prev_shape = curr_shape
            fpss.append((datetime.now() - prev_ts).total_seconds())
            prev_ts = datetime.now()
            fpss = fpss[-100:] if len(fpss) > 1000 else fpss
            log_debug_every_s(start, f"FPS: {len(fpss) / sum(fpss):.2f}")

        self.root.destroy()
        logger.warning("ScreenDisplayer thread stopping")
