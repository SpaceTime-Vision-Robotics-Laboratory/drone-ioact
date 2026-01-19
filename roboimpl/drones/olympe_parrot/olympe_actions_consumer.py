"""olympe_actions_maker.py: Takes generic actions and converts them to olympe-specific commands"""
import olympe
from olympe.video.pdraw import PdrawState
from overrides import overrides

from robobase import ActionConsumer, ActionsQueue, ActionsCallback

class OlympeActionConsumer(ActionConsumer):
    """OlympeActionsMaker: Takes generic actions and converts them to olympe-specific commands."""
    def __init__(self, drone: olympe.Drone, actions_queue: ActionsQueue, actions_callback: ActionsCallback):
        super().__init__(actions_queue, actions_callback)
        self.drone = drone

    @overrides
    def is_streaming(self) -> bool:
        return self.drone.connected and self.drone.streaming.state == PdrawState.Playing
