"""olympe_actions.py - defines all the supported actions of an olympe drone from our generic ones to the drone's"""
import olympe
from olympe.messages.ardrone3.PilotingState import FlyingStateChanged
from olympe.messages.ardrone3.Piloting import moveBy, Landing, TakeOff
from drone_ioact.actions_interfaces import Action

from .olympe_actions_consumer import OlympeActionsConsumer

# the list of all supported actions from our generic ones to the drone's internal ones.
OLYMPE_SUPPORTED_ACTIONS: set[str] = {
    "DISCONNECT", "LIFT", "LAND", "FORWARD", "ROTATE", "FORWARD_NOWAIT", "ROTATE_NOWAIT"
}

def olympe_actions_callback(actions_consumer: OlympeActionsConsumer, action: Action) -> bool:
    """the actions callback from generic actions to drone-specific ones"""
    drone: olympe.Drone = actions_consumer.drone
    if action == "DISCONNECT":
        drone.streaming.stop()
        return True
    if action == "LIFT":
        return drone(TakeOff()).wait().success()
    if action == "LAND":
        return drone(Landing()).wait().success()
    if action == "FORWARD":
        return drone(
            moveBy(1, 0, 0, 0) >> # (forward, right, down, rotation)
            FlyingStateChanged(state="hovering", _timeout=3)
        ).wait()
    if action == "ROTATE":
        return drone(
            moveBy(0, 0, 0, 0.2) >> # (forward, right, down, rotation)
            FlyingStateChanged(state="hovering", _timeout=3)
        ).wait()
    if action == "FORWARD_NOWAIT":
        drone(
            moveBy(1, 0, 0, 0) >> # (forward, right, down, rotation)
            FlyingStateChanged(state="hovering", _timeout=3)
        )
        return True
    if action == "ROTATE_NOWAIT":
        drone(
            moveBy(0, 0, 0, 0.2) >> # (forward, right, down, rotation)
            FlyingStateChanged(state="hovering", _timeout=3)
        )
        return True
    return False
