"""screen_displayer.py - This module reads the data from a drone and prints the RGB. No action is produced"""
import threading
from datetime import datetime
import numpy as np
import cv2

from drone_ioact import DataProducer, DataConsumer
from drone_ioact.utils import logger

class ScreenDisplayer(DataConsumer, threading.Thread):
    """ScreenDisplayer simply prints the current RGB frame with no action to be done."""
    def __init__(self, data_producer: DataProducer, screen_height: int | None = None):
        self.h = screen_height
        DataConsumer.__init__(self, data_producer)
        threading.Thread.__init__(self, daemon=True)

    def get_current_frame(self) -> np.ndarray:
        """gets the current RGB frame. Useful for overwriting if we have more representations, like sem. segmentation"""
        return self.data_producer.get_current_data()["rgb"]

    def run(self):
        assert self.data_producer.is_streaming()
        prev_frame = self.get_current_frame()
        fpss = []
        while self.data_producer.is_streaming():
            now = datetime.now()
            rgb = self.get_current_frame()
            if np.allclose(rgb, prev_frame):
                continue

            aspect_ratio = rgb.shape[1] / rgb.shape[0]
            w = int(self.h * aspect_ratio) if self.h is not None else None
            rgb_rsz = cv2.resize(rgb, (w, self.h)) if self.h is not None else rgb

            cv2.imshow("img", cv2.cvtColor(rgb_rsz, cv2.COLOR_RGB2BGR))
            cv2.waitKey(1)

            fpss.append((datetime.now() - now).total_seconds())
            fpss = fpss[-100:] if len(fpss) > 1000 else fpss
            prev_frame = rgb
            getattr(logger, "debug" if len(fpss) % 10 == 0 else "debug2")(f"FPS: {len(fpss) / sum(fpss):.2f}")
        logger.warning("ScreenDisplayer thread stopping")
