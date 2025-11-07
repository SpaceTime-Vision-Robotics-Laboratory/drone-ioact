"""screen_displayer.py - This module reads the data from a drone and prints the RGB. No action is produced"""
import threading
import numpy as np
import cv2

from drone_ioact import DroneIn, DataConsumer
from drone_ioact.utils import logger

class ScreenDisplayer(DataConsumer, threading.Thread):
    """ScreenDisplayer simply prints the current RGB frame with no action to be done."""
    def __init__(self, drone_in: DroneIn):
        DataConsumer.__init__(self, drone_in)
        threading.Thread(self)
        self.start()

    def run(self):
        prev_frame = None
        while self.drone_in.is_streaming():
            rgb = self.drone_in.get_current_data()["rgb"]
            if prev_frame is None or not np.allclose(prev_frame, rgb):
                cv2.imshow("img", rgb)
                cv2.waitKey(1)
            prev_frame = rgb
        logger.warning("ScreenDisplayer thread stopping")
