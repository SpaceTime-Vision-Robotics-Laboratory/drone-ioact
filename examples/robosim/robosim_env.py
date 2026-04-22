"""wrapper for thread-safe client->server conn"""
import socket
import zlib
import threading
import numpy as np
from overrides import overrides
from loggez import make_logger
from robosim.network import send_packet, recv_packet # noqa pylint: disable=all

from robobase import Environment

logger = make_logger("ROBOSIM_ENV")

class RobosimEnv(Environment):
    """wrapper for thread-safe client->server conn"""
    def __init__(self, host: str, port: int, robot_id: int):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
        self.sock_lock = threading.Lock()
        self.robot_id = robot_id
        self._init_connection_to_robot(host, port, robot_id)

    @overrides
    def is_running(self) -> bool: # noqa
        try:
            self.sock.getpeername()
            return True
        except Exception as e:
            logger.error(e)
            return False

    @overrides
    def get_modalities(self) -> list[str]: # noqa
        return ["robot", "rgb", "fpv_frame_id", "fpv_compressed", "fpv_shape"]

    @overrides
    def close(self): # noqa
        self.sock.close()

    @overrides
    def get_state(self) -> dict: # noqa
        res = self.send_recv_packet({"cmd": "robot_get_state_with_camera"})
        frame_bytes = zlib.decompress(res["fpv_compressed"])
        proc = len(res["fpv_compressed"]) / np.prod(res["fpv_shape"]) * 100
        logger.log_every_s(f"Recv: {len(res['fpv_compressed'])} -> "
                           f"{np.prod(res['fpv_shape'])} bytes ({proc:.2f}%)", "TRACE")
        res["rgb"] = np.frombuffer(frame_bytes, dtype=np.uint8).reshape(res["fpv_shape"])
        return res

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

    def _init_connection_to_robot(self, host: str, port: int, robot_id: int):
        msg = {"cmd": "robot_claim_control", "robot_id": robot_id}
        assert (recv := self.send_recv_packet(msg)) == {"status": "connected"}, recv
        logger.info(f"Connected to '{host}:{port}'")

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
