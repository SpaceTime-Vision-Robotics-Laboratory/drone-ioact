"""screen_displayer.py - This module reads the data from a drone and prints the RGB. No action is produced"""
import threading
from datetime import datetime
import tkinter as tk
from PIL import Image, ImageTk
import numpy as np

from drone_ioact import DataProducer, DataConsumer
from drone_ioact.utils import logger, image_resize

class ScreenDisplayer(DataConsumer, threading.Thread):
    """ScreenDisplayer simply prints the current RGB frame with no action to be done."""
    def __init__(self, data_producer: DataProducer, screen_height: int | None = None):
        assert "rgb" in (st := data_producer.get_supported_types()), f"'rgb' not in {st}"
        DataConsumer.__init__(self, data_producer)
        threading.Thread.__init__(self, daemon=True)
        self.initial_h = screen_height
        # state of the canvas: initialized at startup time.
        self.root: tk.Tk | None = None
        self.canvas: tk.Canvas | None = None
        self.photo: ImageTk.PhotoImage | None = None

    def get_current_frame(self) -> np.ndarray:
        """returns the current frame as RGB"""
        return self.data_producer.get_current_data()["rgb"]

    def _startup_tk(self, rgb_rsz: np.ndarray):
        """starts the tk window"""
        assert self.root is None, "cannot call twice"
        self.root = tk.Tk(className=" Screen Displayer")
        self.canvas = tk.Canvas(self.root, width=rgb_rsz.shape[1], height=rgb_rsz.shape[0])
        self.canvas.pack(fill="both", expand=True)
        self.canvas.focus_set()

    def run(self):
        assert self.data_producer.is_streaming(), "data producer is not streaming"
        prev_frame = rgb = self.get_current_frame()
        self._startup_tk(image_resize(rgb, height=self.initial_h or rgb.shape[0], width=None))
        prev_shape = (self.canvas.winfo_height(), self.canvas.winfo_width())

        fpss = []
        while self.data_producer.is_streaming():
            now = datetime.now()
            self.root.update()
            rgb = self.get_current_frame()

            curr_shape = (self.canvas.winfo_height(), self.canvas.winfo_width())
            if np.allclose(prev_frame, rgb) and prev_shape == curr_shape:
                continue

            rgb_rsz = image_resize(rgb, height=curr_shape[0], width=curr_shape[1])
            if prev_shape != curr_shape:
                self.photo = ImageTk.PhotoImage(Image.fromarray(rgb_rsz))
                self.canvas.delete("all")
                self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
            else:
                self.photo.paste(Image.fromarray(rgb_rsz))

            prev_frame = rgb
            prev_shape = curr_shape
            fpss.append((datetime.now() - now).total_seconds())
            fpss = fpss[-100:] if len(fpss) > 1000 else fpss
            getattr(logger, "debug" if len(fpss) % 10 == 0 else "debug2")(f"FPS: {len(fpss) / sum(fpss):.2f}")

        self.root.destroy()
        logger.warning("ScreenDisplayer thread stopping")
