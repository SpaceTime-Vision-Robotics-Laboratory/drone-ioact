"""controller.py - This module defines all the generic controllers and simple data consumers (i.e. display to screen)"""
import threading
from multiprocessing import Queue
import numpy as np
from pynput.keyboard import Listener, KeyCode, Key
import cv2

from .drone_in import DroneIn
from .utils import logger
from .actions import Action

class ScreenDisplayer(threading.Thread):
    """ScreenDisplayer simply prints the current RGB frame with no action to be done."""
    def __init__(self, drone_in: DroneIn):
        super().__init__()
        self.drone_in = drone_in
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

class KeyboardController(threading.Thread):
    def __init__(self, drone_in: DroneIn, actions_queue: Queue):
        super().__init__()
        self.listener = Listener(on_release=self.action_from_key_release)
        self.drone_in = drone_in
        self.actions_queue = actions_queue
        self.start()

    def action_from_key_release(self, key: KeyCode) -> bool | None:
        """puts an action in the actions queue based on the key pressed by the user"""
        action: Action | None = None
        if key == Key.esc:
            logger.info("ESC pressed. Stopping Keyboard Controller.")
            action = Action.DISCONNECT
        if key == KeyCode.from_char("T"):
            action = Action.LIFT
        if key == KeyCode.from_char("L"):
            action = Action.LAND
        if key == KeyCode.from_char("i"):
            action = Action.FORWARD
        if key == KeyCode.from_char("o"):
            action = Action.ROTATE
        if key == KeyCode.from_char("w"):
            action = Action.FORWARD_NOWAIT
        if key == KeyCode.from_char("e"):
            action = Action.ROTATE_NOWAIT

        if action is None:
            logger.debug(f"Unused char: {key}")
        else:
            logger.info(f"Pressed {key}. Performing: {action.name}")
            self.actions_queue.put(action, block=True)
            if action == Action.DISCONNECT:
                return False

    def run(self):
        self.listener.start()
        self.listener.join()
        logger.warning("KeyboardController thread stopping")
