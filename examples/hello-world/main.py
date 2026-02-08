#!/usr/bin/env python3
"""basic minimal example to create and env, a data channel/actions queue and the middle part: dp, controller etc."""
import shutil
import threading
from pathlib import Path
from copy import deepcopy
from datetime import datetime
from robobase import Robot, Environment, DataChannel, ActionsQueue
from robobase.utils import wait_and_clear

TARGET = "helloworld"

class BasicEnv(Environment):
    """minimal environment"""
    def __init__(self):
        super().__init__()
        self._state = []
        self._lock = threading.Lock()
        self.data_ready.set()
    def push(self, action):
        """updates the state of the env in a thread-safe way"""
        with self._lock:
            self._state.append(action)
        self.data_ready.set()
    def is_running(self) -> bool:
        return len(self._state) != len(TARGET)
    def get_state(self) -> dict:
        wait_and_clear(self.data_ready)
        with self._lock:
            return {"ts": datetime.now().isoformat(), "state": deepcopy(self._state)} # important to deepcopy :)
    def get_modalities(self) -> list[str]:
        return ["ts", "state"]

def main(tmp_path: Path):
    """main fn"""
    env = BasicEnv()
    shutil.rmtree(tmp_path, ignore_errors=True) if tmp_path is not None else None
    data_channel = DataChannel(supported_types=["ts", "state"], eq_fn=lambda a, b: a["state"] == b["state"],
                               log_path=tmp_path)
    actions_queue = ActionsQueue(actions=list(map(chr, range(ord("a"), ord("z") + 1)))) # from 'a' to 'z'
    action_fn = lambda env, action: env.push(action)

    robot = Robot(env, data_channel, actions_queue, action_fn)
    # push 'h' if env._state==[], 'e' if env._state==['h'] and so on until helloworld
    robot.add_controller(lambda data: TARGET[len(data["state"])] if len(data["state"]) < len(TARGET) else None)

    robot.run()
    data_channel.close()
    print(f"Final state: '{''.join(env._state)}'") # pylint: disable=protected-access
    assert "".join(env._state) == TARGET, env._state # pylint: disable=protected-access

if __name__ == "__main__":
    main(None)
