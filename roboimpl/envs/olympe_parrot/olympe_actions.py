"""olympe_actions.py - defines all the supported actions of an olympe drone from our generic ones to the drone's"""
import threading
from olympe.messages.ardrone3.Piloting import Landing, TakeOff
from olympe.messages import gimbal
from robobase import Action
from .olympe_env import OlympeEnv

# the list of all supported actions from our generic ones to the drone's internal ones.
OLYMPE_SUPPORTED_ACTIONS: set[str] = {
    "DISCONNECT", "LIFT", "LAND", "FORWARD", "BACKWARD", "LEFT", "RIGHT", "ROTATE_LEFT", "ROTATE_RIGHT",
    "INCREASE_HEIGHT", "DECREASE_HEIGHT", "TILT_UP", "TILT_DOWN", "PILOTING"
}

def olympe_actions_fn(env: OlympeEnv, action: Action) -> bool:
    """the actions callback from generic actions to drone-specific ones. Note: all actions are in (velocity, time) !"""
    drone = env.drone
    if action == "DISCONNECT":
        drone.streaming.stop()
        return True
    if action == "LIFT":
        return drone(TakeOff()).wait().success()
    if action == "LAND":
        return drone(Landing()).wait().success()
    if action == "PILOTING":
        roll, pitch, yaw, gaz, piloting_time = action.parameters
        return drone.piloting(roll, pitch, yaw, gaz, piloting_time)

    # All actions below are in (velocity, time), meaning we apply that velocity for some time. drone.piloting() does
    # this for us, but for gimbal, we do it ourselves (blocking for now).
    velocity, piloting_time = action.parameters
    # (x, y, z, z_rot, time)
    if action == "FORWARD":
        return drone.piloting(roll=0, pitch=velocity, yaw=0, gaz=0, piloting_time=piloting_time)
    if action == "BACKWARD":
        return drone.piloting(roll=0, pitch=-velocity, yaw=0, gaz=0, piloting_time=piloting_time)
    if action == "LEFT":
        return drone.piloting(roll=-velocity, pitch=0, yaw=0, gaz=0, piloting_time=piloting_time)
    if action == "RIGHT":
        return drone.piloting(roll=velocity, pitch=0, yaw=0, gaz=0, piloting_time=piloting_time)
    if action == "ROTATE_LEFT":
        return drone.piloting(roll=0, pitch=0, yaw=-velocity, gaz=0, piloting_time=piloting_time)
    if action == "ROTATE_RIGHT":
        return drone.piloting(roll=0, pitch=0, yaw=velocity, gaz=0, piloting_time=piloting_time)
    if action == "INCREASE_HEIGHT":
        return drone.piloting(roll=0, pitch=0, yaw=0, gaz=velocity, piloting_time=piloting_time)
    if action == "DECREASE_HEIGHT":
        return drone.piloting(roll=0, pitch=0, yaw=0, gaz=-velocity, piloting_time=piloting_time)
    # gimbal stuff
    gimbal_kwargs = {"gimbal_id": 0, "control_mode": "velocity", "yaw_frame_of_reference": "none", "yaw": 0,
                     "roll_frame_of_reference": "none", "roll": 0, "pitch_frame_of_reference": "absolute"}
    if action == "TILT_UP":
        drone(gimbal.set_target(pitch=velocity, **gimbal_kwargs))
        threading.Timer(piloting_time, lambda: drone(gimbal.set_target(pitch=0, **gimbal_kwargs))).start()
        return True
    if action == "TILT_DOWN":
        drone(gimbal.set_target(pitch=-velocity, **gimbal_kwargs))
        threading.Timer(piloting_time, lambda: drone(gimbal.set_target(pitch=0, **gimbal_kwargs))).start()
        return True

    return False
