#!/usr/bin/env python3
"""A simple TCP client to connect to the simulator server and interact with the robot/UAV"""
from argparse import ArgumentParser, Namespace
from pathlib import Path
import sys
import numpy as np
import json
from loggez import make_logger

from robobase import Robot, DataChannel, ActionsQueue, Action as Act
from roboimpl.controllers import ScreenDisplayer, Key
from roboimpl.controllers.keyboard_controller import KeyboardController

from robosim.robosim_env import RobosimEnv
sys.path.append(str(Path(__file__).parent))
from trajectory import TrajectoryController

logger = make_logger("CLIENT", exists_ok=True)
np.set_printoptions(precision=3, linewidth=120)
MAXES: np.ndarray = None

# utilities

def actions_fn(env: RobosimEnv, actions: list[Act]) -> bool:
    """converts generic actions to robosim specific ones"""
    global MAXES # pylint: disable=global-statement
    MAXES = env.get_maxes() if MAXES is None else MAXES
    msgs = []
    for action in actions:
        if action.name == "DISCONNECT":
            env.close()
            return True

        if action.name == "MOVE":
            msgs.append({"cmd": "move", "control_input": (action.parameters[0] * MAXES).tolist()})

        if action.name == "RESET":
            msgs.append({"cmd": "sim_reset"})

        if action.name == "LOAD_STATE":
            assert (pth := Path(__file__).parent / "state.json").exists(), pth
            with open(pth, "r") as fp:
                state = json.load(fp)
            msgs.append({"cmd": "sim_load_state", "state": state})
            logger.log_every_s(f"Loading state from '{pth}'")

        if action.name == "GET_STATE":
            msgs.append({"cmd": "sim_get_state"})

    resps = env.send_recv_packets(msgs)
    had_errors = False
    for resp in resps:
        if "error" in resp:
            logger.error(resp)
            had_errors = True
            if "robot" in resp:
                MAXES = env.get_maxes()
        if {"robots", "state"}.issubset(resp.keys()):
            with open(pth := Path(__file__).parent / "state.json", "w") as fp:
               logger.log_every_s(f"Saved state at: '{pth}'")
               json.dump(resp, fp)
    return not had_errors

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
        acts.append(Act("GET_STATE"))
        pressed.discard(Key.F5)
    elif Key.F6 in pressed:
        if not (Path(__file__).parent / "state.json").exists():
            logger.error("Cannot load state before saving one.")
        else:
            acts.append(Act("LOAD_STATE"))
        pressed.discard(Key.F6)

    move_vec = np.zeros((6,), dtype="float32")
    move_vec[0] += (Key.a in pressed) - (Key.d in pressed)                # left/right (x)
    move_vec[1] += (Key.Up in pressed) - (Key.Down in pressed)            # up/down (y)
    move_vec[2] += (Key.w in pressed) - (Key.s in pressed)                # forward/backward (z)
    move_vec[3] += (Key.PageDown in pressed) - (Key.PageUp in pressed)    # pitch
    move_vec[4] += (Key.q in pressed) - (Key.e in pressed)                # yaw
    move_vec[5] += (Key.Right in pressed) - (Key.Left in pressed)         # roll

    if np.abs(move_vec).sum() > 1e-5:
        acts.append(Act("MOVE", (move_vec, )))

    return acts

def get_args() -> Namespace:
    """cli args"""
    parser = ArgumentParser()
    parser.add_argument("host")
    parser.add_argument("--port", "-p", type=int)
    parser.add_argument("--robot_id", type=int, default=0)
    args = parser.parse_args()
    return args

def main(args: Namespace):
    """main fn"""
    env = RobosimEnv(args.host, args.port, args.robot_id)
    data_channel = DataChannel(supported_types=env.get_modalities(),
                               eq_fn=lambda a, b: a["fpv_frame_id"] == b["fpv_frame_id"])
    action_names = ["MOVE", "DISCONNECT", "RESET", "LOAD_STATE", "GET_STATE"]
    actions_queue = ActionsQueue(action_names=action_names)
    robot = Robot(env, data_channel, actions_queue, actions_fn)

    robot.add_controller(sd := ScreenDisplayer(data_channel, actions_queue))
    robot.add_controller(KeyboardController(data_channel, actions_queue, sd.backend, keyboard_fn))
    robot.add_controller(TrajectoryController(data_channel, actions_queue, env))

    robot.run()
    env.close()

if __name__ == "__main__":
    main(get_args())
