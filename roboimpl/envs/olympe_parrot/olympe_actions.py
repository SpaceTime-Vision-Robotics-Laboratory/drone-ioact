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
        y, time = action.parameters
        return drone.piloting(0, y, 0, 0, time)
    if action == "BACKWARD":
        y, time = action.parameters
        return drone.piloting(0, -y, 0, 0, time)
    if action == "LEFT":
        x, time = action.parameters
        return drone.piloting(-x, 0, 0, 0, time)
    if action == "RIGHT":
        x, time = action.parameters
        return drone.piloting(x, 0, 0, 0, time)
    if action == "ROTATE_LEFT":
        z, time = action.parameters
        return drone.piloting(0, 0, -z, 0, time)
    if action == "ROTATE_RIGHT":
        z, time = action.parameters
        return drone.piloting(0, 0, z, 0, time)
    if action == "INCREASE_HEIGHT":
        z_rot, time = action.parameters
        return drone.piloting(0, 0, 0, z_rot, time)
    if action == "DECREASE_HEIGHT":
        z_rot, time = action.parameters
        return drone.piloting(0, 0, 0, -z_rot, time)
    # gimbal stuff
    gimbal_kwargs = {"gimbal_id": 0, "control_mode": "position", "yaw_frame_of_reference": "none", "yaw": 0,
                     "roll_frame_of_reference": "none", "roll": 0, "pitch_frame_of_reference": "absolute"}
    current_pitch = drone.get_state(gimbal.attitude)[0]["pitch_absolute"]
    logger.debug(f"Action={action}. Current pitch: {current_pitch:.3f}.")
    if action == "TILT_UP":
        delta_pitch = action.parameters[0]
        return drone(gimbal.set_target(pitch=current_pitch + delta_pitch, **gimbal_kwargs))
    if action == "TILT_DOWN":
        delta_pitch = action.parameters[0]
        return drone(gimbal.set_target(pitch=current_pitch - delta_pitch, **gimbal_kwargs))

    return False
