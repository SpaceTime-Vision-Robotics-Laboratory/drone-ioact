"""olympe_actions.py - defines all the supported actions of an olympe drone from our generic ones to the drone's"""
from olympe.messages.ardrone3.Piloting import Landing, TakeOff
from olympe.messages import gimbal
from robobase import Action
from roboimpl.utils import logger
from .olympe_env import OlympeEnv

# the list of all supported actions from our generic ones to the drone's internal ones.
OLYMPE_SUPPORTED_ACTIONS: set[str] = {
    "DISCONNECT", "LIFT", "LAND", "FORWARD", "BACKWARD", "LEFT", "RIGHT", "ROTATE_LEFT", "ROTATE_RIGHT",
    "INCREASE_HEIGHT", "DECREASE_HEIGHT", "TILT_DOWN", "TILT_UP",
}

def olympe_actions_fn(env: OlympeEnv, action: Action) -> bool:
    """the actions callback from generic actions to drone-specific ones"""
    drone = env.drone
    if action == "DISCONNECT":
        drone.streaming.stop()
        return True
    if action == "LIFT":
        return drone(TakeOff()).wait().success()
    if action == "LAND":
        return drone(Landing()).wait().success()
    # (x, y, z, z_rot, time)
    if action == "FORWARD":
        return drone.piloting(0, 50, 0, 0, 0.15)
    if action == "BACKWARD":
        return drone.piloting(0, -50, 0, 0, 0.15)
    if action == "LEFT":
        return drone.piloting(-50, 0, 0, 0, 0.15)
    if action == "RIGHT":
        return drone.piloting(50, 0, 0, 0, 0.15)
    if action == "ROTATE_LEFT":
        return drone.piloting(0, 0, -50, 0, 0.15)
    if action == "ROTATE_RIGHT":
        return drone.piloting(0, 0, 50, 0, 0.15)
    if action == "INCREASE_HEIGHT":
        return drone.piloting(0, 0, 0, 20, 0.15)
    if action == "DECREASE_HEIGHT":
        return drone.piloting(0, 0, 0, -20, 0.15)
    # gimbal stuff
    gimbal_kwargs = {"gimbal_id": 0, "control_mode": "position", "yaw_frame_of_reference": "none", "yaw": 0,
                     "roll_frame_of_reference": "none", "roll": 0, "pitch_frame_of_reference": "absolute"}
    # TODO: should be at sensors level and we parametrize the action.
    # TODO: wait for tilt degree?
    current_pitch = drone.get_state(gimbal.attitude)[0]["pitch_absolute"]
    logger.debug(f"Current pitch: {current_pitch}")
    if action == "TILT_UP":
        return drone(gimbal.set_target(pitch=current_pitch + 10, **gimbal_kwargs)).wait().success()
    if action == "TILT_DOWN":
        return drone(gimbal.set_target(pitch=current_pitch - 10, **gimbal_kwargs)).wait().success()

    return False
