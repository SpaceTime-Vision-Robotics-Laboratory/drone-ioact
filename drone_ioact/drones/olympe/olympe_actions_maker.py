"""olympe_actions_maker.py: Takes generic actions and converts them to olympe-specific commands"""
import threading
from queue import Queue
import olympe

from drone_ioact import DroneOut, ActionCallback

class OlympeActionsMaker(DroneOut, threading.Thread):
    """OlympeActionsMaker: Takes generic actions and converts them to olympe-specific commands."""
    def __init__(self, drone: olympe.Drone, actions_queue: Queue, action_callback: ActionCallback):
        DroneOut.__init__(self, actions_queue, action_callback)
        threading.Thread.__init__(self, daemon=True)
        self.drone = drone

    def stop_streaming(self):
        return self.drone.streaming.stop()
