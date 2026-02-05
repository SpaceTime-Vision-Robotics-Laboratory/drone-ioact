#!/usr/bin/env python3
"""basic minimal example to create and env, a data channel/actions queue and the middle part: dp, controller etc."""
import shutil
import threading
from pathlib import Path
from copy import deepcopy
from datetime import datetime
from robobase import Robot, Environment, DataChannel, ActionsQueue

TARGET = "helloworld"

class BasicEnv(Environment):
    """minimal environment"""
    def __init__(self):
        Environment.__init__(self, frequency=30)
        self._state = []
        self._lock = threading.Lock()
    def push(self, action):
        """updates the state of the env in a thread-safe way"""
        with self._lock:
            self._state.append(action)
    def is_running(self) -> bool:
        return len(self._state) != len(TARGET)
    def get_state(self) -> dict:
        with self._lock:
            return {"ts": datetime.now().isoformat(), "state": deepcopy(self._state)} # important to deepcopy :)
    def get_modalities(self) -> list[str]:
        return ["ts", "state"]

def main(tmp_path: Path):
    """main fn"""
    env = BasicEnv()
    shutil.rmtree(tmp_path, ignore_errors=True)
    data_channel = DataChannel(supported_types=["ts", "state"], eq_fn=lambda a, b: a["state"] == b["state"],
                               log_path=tmp_path)
    actions_queue = ActionsQueue(actions=list(map(chr, range(ord("a"), ord("z") + 1)))) # from 'a' to 'z'
    action_fn = lambda env, action: env.push(action)

    robot = Robot(env, data_channel, actions_queue, action_fn)
    # push 'h' if env._state==[], 'e' if env._state==['h'] and so on until helloworld
    robot.add_controller(lambda data: TARGET[len(data["state"])] if len(data["state"]) < len(TARGET) else None)

    robot.run()
    data_channel.close()
    print(f"Final state: '{''.join(env.get_state()['state'])}'")
    assert "".join(env.get_state()["state"]) == TARGET

if __name__ == "__main__":
    main(Path(__file__).parent / Path(__file__).stem)
