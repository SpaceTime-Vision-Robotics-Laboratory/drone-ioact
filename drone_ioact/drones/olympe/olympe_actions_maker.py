"""olympe_actions_maker.py: Takes generic actions and converts them to olympe-specific commands"""
from queue import Queue
import olympe

from drone_ioact import DroneOut, ActionCallback
from drone_ioact.utils import logger

class OlympeActionsMaker(DroneOut):
    """OlympeActionsMaker: Takes generic actions and converts them to olympe-specific commands."""
    def __init__(self, drone: olympe.Drone, actions_queue: Queue, action_callback: ActionCallback):
        DroneOut.__init__(self, actions_queue, action_callback)
        self.drone = drone

    def stop_streaming(self):
        logger.info("Stopping streaming...")
        try:
            self.drone.streaming.stop()
        except Exception as e:
            logger.error("Unable to properly stop the streaming...")
            logger.critical(e, exc_info=True)

        return self.drone.streaming.stop()

    def is_streaming(self) -> bool:
        connected = self.drone.connected
        streaming = self.drone.streaming is not None
        return connected and streaming
