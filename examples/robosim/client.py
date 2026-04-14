#!/usr/bin/env python3
"""A simple TCP client to connect to the simulator server and interact with the robot/UAV"""
from argparse import ArgumentParser, Namespace
import socket
import zlib
import numpy as np
import threading
from loggez import make_logger
import matplotlib

from robobase import Environment, Robot, DataChannel, ActionsQueue, Action as Act
from roboimpl.controllers import ScreenDisplayer, Key
#from robosim.utils import Point6D, Pose4x4, fmt, pose_to_trans_euler, relative_velocity_from_poses
from robosim.network import send_packet, recv_packet # noqa pylint: disable=all

logger = make_logger("CLIENT")
matplotlib.rcParams["keymap.quit"] = []
np.set_printoptions(precision=3, linewidth=120)
DT = 1

class Robosim(Environment):
    """wrapper for thread-safe client->server conn"""
    def __init__(self, host: str, port: int):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
        self.sock_lock = threading.Lock()
        assert (recv := self.send_recv_packet({"cmd": "robot_claim_control"})) == {"status": "connected"}, recv
        logger.info(f"Connected to '{host}:{port}'")

    def send_recv_packet(self, data: dict) -> dict:
        """send a packet and returns an answer"""
        with self.sock_lock:
            if data["cmd"] != "robot_get_state_with_camera":
                logger.debug(f"Sending: {data}")
            send_packet(self.sock, data)
            res = recv_packet(self.sock)
            if "fpv_compressed" not in res:
                logger.debug(f"Received: {res}")
            return res

    def send_recv_packets(self, data: list[dict]) -> list[dict]:
        """sends many packets and returns the answers"""
        if len(data) == 0:
            return []
        res = []
        logger.log_every_s(f"Sending {len(data)} messages", "DEBUG", log_to_next_level=True)
        with self.sock_lock:
            for msg in data:
                send_packet(self.sock, msg)
            for _ in range(len(data)):
                res.append(recv_packet(self.sock))
        return res

    def get_state(self):
        res = self.send_recv_packet({"cmd": "robot_get_state_with_camera"})
        frame_bytes = zlib.decompress(res["fpv_compressed"])
        proc = len(res["fpv_compressed"]) / np.prod(res["fpv_shape"]) * 100
        logger.log_every_s(f"Recv: {len(res['fpv_compressed'])} -> "
                           f"{np.prod(res['fpv_shape'])} bytes ({proc:.2f}%)", "TRACE")
        res["rgb"] = np.frombuffer(frame_bytes, dtype=np.uint8).reshape(res["fpv_shape"])
        return res

    def is_running(self):
        try:
            self.sock.getpeername()
            return True
        except Exception as e:
            logger.error(e)
            return False

    def get_modalities(self):
        return ["robot", "rgb", "fpv_frame_id", "fpv_compressed", "fpv_shape"]

    def get_maxes(self) -> np.ndarray:
        """return the max allowed by this uav"""
        state = self.send_recv_packet({"cmd": "robot_get_state"})
        uav_type = state["robot"]["type"]

        if uav_type == "UAVLevel1":
            maxes = np.array(state["robot"]["max_velocities"], "float32")
        elif uav_type == "UAVLevel2":
            maxes = np.array(state["robot"]["max_accelerations"], "float32")
        else:
            raise ValueError(uav_type)
        return maxes

    def close(self):
        self.sock.close()

# utilities

def actions_fn(env: Robosim, action: Act) -> bool:
    """converts generic actions to robosim specific ones"""
    if action.name == "DISCONNECT":
        env.close()
        return True

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
    logger.info(pressed)
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
    env = Robosim(args.host, args.port)
    data_channel = DataChannel(supported_types=env.get_modalities(),
                               eq_fn=lambda a, b: a["fpv_frame_id"] == b["fpv_frame_id"])
    action_names = ["MOVE", "DISCONNECT", "RESET", "LOAD_STATE", "SAVE_STATE"]
    actions_queue = ActionsQueue(action_names=action_names)
    robot = Robot(env, data_channel, actions_queue, actions_fn)

    robot.add_controller(ScreenDisplayer(data_channel, actions_queue, keyboard_fn=keyboard_fn))
    robot.run()
    env.close()

if __name__ == "__main__":
    main(get_args())
