"""keyboard_controller.py - Converts a keyboard key to a drone action"""
import threading
from pynput.keyboard import Listener, KeyCode

from drone_ioact import DroneIn, DataConsumer, ActionsProducer, ActionsQueue, Action
from drone_ioact.utils import logger

class KeyboardController(DataConsumer, ActionsProducer, threading.Thread):
    """Converts a keyboard key to a drone action. Has support for a few standard actions."""
    def __init__(self, drone_in: DroneIn, actions_queue: ActionsQueue, key_to_action: dict[str, str]):
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
        action: Action | None = self.key_to_action.get(getattr(key, "char", str(key))) # key.char if a key else str(key)
        if action is None:
            logger.debug(f"Unused char: {key}")
            return True

        logger.info(f"Pressed {key}. Pushing: {action}")
        self.add_to_queue(action)

        if action == "DISCONNECT": # Note: the actual action may be called different, but it's easier to hardcode it.
            logger.info("Disconnect was requested. Stopping Keyboard Controller.")
            return False
        return True

    def run(self):
        self.listener.start()
        self.listener.join()
        logger.warning("KeyboardController thread stopping")
