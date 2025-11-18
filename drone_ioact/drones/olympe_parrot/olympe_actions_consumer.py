"""olympe_actions_maker.py: Takes generic actions and converts them to olympe-specific commands"""
import olympe
from overrides import overrides

from drone_ioact import ActionsConsumer, ActionsQueue, ActionsCallback

class OlympeActionsConsumer(ActionsConsumer):
    """OlympeActionsMaker: Takes generic actions and converts them to olympe-specific commands."""
    def __init__(self, drone: olympe.Drone, actions_queue: ActionsQueue, actions_callback: ActionsCallback):
        super().__init__(actions_queue, actions_callback)
        self.drone = drone

    @overrides
    def is_streaming(self) -> bool:
        return self.drone.connected and self.drone.streaming is not None
