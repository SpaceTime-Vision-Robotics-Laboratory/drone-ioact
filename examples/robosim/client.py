#!/usr/bin/env python3
"""A simple TCP client to connect to the simulator server and interact with the robot/UAV"""
from argparse import ArgumentParser, Namespace
import numpy as np
from loggez import make_logger

from robosim_env import RobosimEnv
from trajectory import TrajectoryController

from robobase import Robot, DataChannel, ActionsQueue, Action as Act
from roboimpl.controllers import ScreenDisplayer, Key
from roboimpl.controllers.keyboard_controller import KeyboardController

logger = make_logger("CLIENT", exists_ok=True)
np.set_printoptions(precision=3, linewidth=120)
DT = 1

# utilities

def actions_fn(env: RobosimEnv, action: Act) -> bool:
    """converts generic actions to robosim specific ones"""
    if action.name == "DISCONNECT":
        env.close()
        return True

    msg = None
    if action.name == "MOVE":
        maxes = env.get_maxes()
        msg = {"cmd": "move", "control_input": (action.parameters[0] * maxes).tolist()}

    if action.name == "RESET":
        msg = {"cmd": "reset"}

    if action.name == "LOAD_STATE":
        msg = {"cmd": "load_state", "config_name": action.parameters[0]}

    if action.name == "SAVE_STATE":
        msg = {"cmd": "save_state", "config_name": action.parameters[0]}

    if action.name == "RESET":
        msg = {"cmd": "reset"}

    res = env.send_recv_packet(msg)
    if "error" in res:
        logger.error(res)
        return False
    return True

def keyboard_fn(pressed: set[Key]) -> list[Act]:
    """basic keyboard controller - manuallly control the uav"""
    if len(pressed) == 0:
        return []
    logger.log_every_s(f"Pressed: {pressed}", "DEBUG")
    if Key.Esc in pressed:
        return [Act("DISCONNECT")]

    acts: list[Act] = []
    if Key.r in pressed:
        acts.append(Act("RESET"))
        pressed.discard(Key.r)
    elif Key.F5 in pressed:
        acts.append(Act("SAVE_STATE", ("state.json", )))
        pressed.discard(Key.F5)
    elif Key.F6 in pressed:
        acts.append(Act("LOAD_STATE", ("state.json", )))
        pressed.discard(Key.F6)

    move_vec = np.zeros((6,), dtype="float32")
    move_vec[0] += (Key.a in pressed) - (Key.d in pressed)                                       # left/right (x)
    move_vec[1] += (Key.Up in pressed) - (Key.Down in pressed)                                   # up/down (y)
    move_vec[2] += (Key.w in pressed) - (Key.s in pressed)                                       # forward/backward (z)
    move_vec[3] += (Key.PageDown in pressed) - (Key.PageUp in pressed)                           # pitch
    move_vec[4] += (Key.q in pressed) - (Key.e in pressed)                                       # yaw
    move_vec[5] += (Key.Right in pressed) - (Key.Left in pressed)                                # roll

    if np.abs(move_vec).sum() > 1e-5:
        acts.append(Act("MOVE", (move_vec, )))

    return acts

def get_args() -> Namespace:
    """cli args"""
    parser = ArgumentParser()
    parser.add_argument("host")
    parser.add_argument("--port", "-p", type=int)
    parser.add_argument("--robot", choices=["uav_level1", "uav_level2"])
    args = parser.parse_args()
    return args

def main(args: Namespace):
    """main fn"""
    env = RobosimEnv(args.host, args.port)
    data_channel = DataChannel(supported_types=env.get_modalities(),
                               eq_fn=lambda a, b: a["fpv_frame_id"] == b["fpv_frame_id"])
    action_names = ["MOVE", "DISCONNECT", "RESET", "LOAD_STATE", "SAVE_STATE"]
    actions_queue = ActionsQueue(action_names=action_names)
    robot = Robot(env, data_channel, actions_queue, actions_fn)

    robot.add_controller(ScreenDisplayer(data_channel, actions_queue))
    robot.add_controller(KeyboardController(data_channel, actions_queue, keyboard_fn))
    robot.add_controller(TrajectoryController(data_channel, actions_queue, env))

    robot.run()
    env.close()

if __name__ == "__main__":
    main(get_args())
