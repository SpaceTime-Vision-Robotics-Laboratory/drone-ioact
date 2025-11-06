"""keyboard_controller.py - Converts a keyboard key to a drone action"""
import threading
from queue import Queue
from pynput.keyboard import Listener, KeyCode, Key

from drone_ioact.drone_in import DroneIn
from drone_ioact.utils import logger
from drone_ioact.actions import Action

class KeyboardController(threading.Thread):
    """Converts a keyboard key to a drone action"""
    def __init__(self, drone_in: DroneIn, actions_queue: Queue):
        super().__init__()
        self.listener = Listener(on_release=self.on_release)
        self.drone_in = drone_in
        self.actions_queue = actions_queue
        self.start()

    def key_to_action(self, key: KeyCode) -> Action | None:
        """Converts a keyboard key to a drone action. Can be overriden for custom actions."""
        action: Action | None = None
        if key == Key.esc:
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
        return action

    def on_release(self, key: KeyCode) -> bool | None:
        """puts an action in the actions queue based on the key pressed by the user"""
        action = self.key_to_action(key)
        if action is None:
            logger.debug(f"Unused char: {key}")
        else:
            logger.info(f"Pressed {key}. Performing: {action.name}")
            self.actions_queue.put(action, block=True)
            if action == Action.DISCONNECT:
                logger.info("Disconnect was requested. Stopping Keyboard Controller.")
                return False

    def run(self):
        self.listener.start()
        self.listener.join()
        logger.warning("KeyboardController thread stopping")
