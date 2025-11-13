"""keyboard_controller.py - Converts a keyboard key to a drone action"""
import threading
import time
from pynput.keyboard import Listener, KeyCode

from drone_ioact import DroneIn, DataConsumer, ActionsProducer, ActionsQueue, Action
from drone_ioact.utils import logger

class KeyboardController(DataConsumer, ActionsProducer, threading.Thread):
    """
    Converts a keyboard key to a drone action. Has support for a few standard actions.
    Parameters:
    - drone_in The DroneIn object with which this controller communicates
    - actions_queue The queue of possible actions this controller can send to the drone_in object
    - key_to_action The dictionary between keyboard keys and actions to take. Must be a subset of possible actions.
    - stop_key (optional) If set, defines the name of the key that can close this keyboard controller.
    """
    def __init__(self, drone_in: DroneIn, actions_queue: ActionsQueue, key_to_action: dict[str, Action]):
        DataConsumer.__init__(self, drone_in)
        ActionsProducer.__init__(self, actions_queue)
        threading.Thread.__init__(self)
        self.listener = Listener(on_release=self.on_release)
        self.key_to_action = key_to_action
        assert all(v in (acts := actions_queue.actions) for v in key_to_action.values()), (key_to_action, acts)

    def add_to_queue(self, action: Action):
        """pushes an action to queue. Separate method so we can easily override it (i.e. priority queue put)"""
        self.actions_queue.put(action, block=True)

    def on_release(self, key: KeyCode) -> bool:
        """puts an action in the actions queue based on the key pressed by the user"""
        key_str: str = getattr(key, "char", str(key)) # key.char if a key else str(key)
        action: Action | None = self.key_to_action.get(key_str)

        if action is None:
            logger.debug(f"Unused char: {key}")
            return True

        logger.debug(f"Pressed {key}. Pushing: {action} to the actions queue.")
        self.add_to_queue(action)
        return True

    def run(self):
        self.listener.start()
        while self.drone_in.is_streaming():
            time.sleep(1)
        self.listener.stop()
        self.listener.join()
        logger.warning("KeyboardController thread stopping")
