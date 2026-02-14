#!/usr/bin/env python3
"""basic minimal example to create and env, a data channel/actions queue and the middle part: dp, controller etc."""
import shutil
import threading
from pathlib import Path
from copy import deepcopy
from datetime import datetime
import pytest
import numpy as np
from robobase import Robot, Environment, DataChannel, ActionsQueue
from robobase.utils import wait_and_clear, DataStorer

TARGET = "helloworld"

class BasicEnv(Environment):
    """minimal environment"""
    def __init__(self):
        super().__init__()
        self._state = []
        self._lock = threading.Lock()
        self.data_ready.set() # first data is available from the beginning
    def push(self, action):
        """updates the state of the env in a thread-safe way"""
        with self._lock:
            self._state.append(action)
        self.data_ready.set() # upon pushing, we signal that data is ready
    def is_running(self) -> bool:
        return len(self._state) != len(TARGET)
    def get_state(self) -> dict:
        wait_and_clear(self.data_ready) # you can only get the data once from the env: wait for 'green' light + clear.
        with self._lock:
            return {"ts": datetime.now().isoformat(), "state": deepcopy(self._state)} # important to deepcopy :)
    def get_modalities(self) -> list[str]:
        return ["ts", "state"]

def test_i_Robot_replay_from_logs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    env = BasicEnv()
    monkeypatch.setenv("ROBOBASE_STORE_LOGS", "2")
    monkeypatch.setenv("ROBOBASE_LOGS_DIR", str(tmp_path))
    shutil.rmtree(tmp_path, ignore_errors=True)
    data_channel = DataChannel(supported_types=["ts", "state"], eq_fn=lambda a, b: a["state"] == b["state"])
    actions_queue = ActionsQueue(actions=[chr(x) for x in range(ord("a"), ord("z") + 1)]) # from 'a' to 'z'

    robot = Robot(env, data_channel, actions_queue, action_fn=lambda env, action: env.push(action.name))
    # push 'h' if env._state==[], 'e' if env._state==['h'] and so on until helloworld
    robot.add_controller(lambda data: TARGET[len(data["state"])] if len(data["state"]) < len(TARGET) else None)

    robot.run()
    data_channel.close()
    print(f"Final state: '{''.join(env._state)}'") # pylint: disable=protected-access
    assert "".join(env._state) == TARGET # pylint: disable=protected-access

    DataStorer.get_instance().close()
    data_files = sorted(list((tmp_path / "DataChannel").iterdir()), key=lambda p: p.name)
    data = [np.load(x, allow_pickle=True).item() for x in data_files]
    for i in range(len(data)):
        assert "".join(data[i]["state"]) == TARGET[0:i]

    actions_files = sorted(list((tmp_path / "ActionsQueue").iterdir()), key=lambda p: p.name)
    actions = [np.load(x, allow_pickle=True).item() for x in actions_files]
    for i in range(len(actions)):
        assert actions[i]["action"] == TARGET[i], (actions[i], TARGET[i])
        assert actions[i]["data_ts"] == data_files[i].stem

if __name__ == "__main__":
    test_i_Robot_replay_from_logs(Path(__file__).parent / Path(__file__).stem)
