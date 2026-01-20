"""olympe_actions_maker.py: Takes generic actions and converts them to olympe-specific commands"""
import olympe
from olympe.video.pdraw import PdrawState

from robobase import ActionConsumer, ActionsQueue, ActionsFn

class OlympeActionConsumer(ActionConsumer):
    """OlympeActionsMaker: Takes generic actions and converts them to olympe-specific commands."""
    def __init__(self, drone: olympe.Drone, actions_queue: ActionsQueue, actions_fn: ActionsFn):
        super().__init__(actions_queue, actions_fn, termination_fn=self._is_streaming)
        self.drone = drone

    def _is_streaming(self) -> bool:
        return self.drone.connected and self.drone.streaming.state == PdrawState.Playing
