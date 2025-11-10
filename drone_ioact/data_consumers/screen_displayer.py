"""screen_displayer.py - This module reads the data from a drone and prints the RGB. No action is produced"""
import threading
import numpy as np
import cv2

from drone_ioact import DroneIn, DataConsumer
from drone_ioact.utils import logger

class ScreenDisplayer(DataConsumer, threading.Thread):
    """ScreenDisplayer simply prints the current RGB frame with no action to be done."""
    def __init__(self, drone_in: DroneIn, screen_height: int | None = None):
        self.h = screen_height
        DataConsumer.__init__(self, drone_in)
        threading.Thread.__init__(self)

    def run(self):
        prev_frame = None
        while self.drone_in.is_streaming():
            rgb = self.drone_in.get_current_data()["rgb"]
            if prev_frame is None or not np.allclose(prev_frame, rgb):
                aspect_ratio = rgb.shape[1] / rgb.shape[0]
                w = int(self.h * aspect_ratio) if self.h is not None else None
                prev_frame = rgb
                rgb = cv2.resize(rgb, (w, self.h)) if self.h is not None else rgb
                cv2.imshow("img", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
                cv2.waitKey(1)
        logger.warning("ScreenDisplayer thread stopping")
