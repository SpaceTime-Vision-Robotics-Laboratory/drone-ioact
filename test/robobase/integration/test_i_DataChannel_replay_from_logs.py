#!/usr/bin/env python3
import time
import shutil
import threading
from pathlib import Path
from queue import Queue
from copy import deepcopy
from datetime import datetime
import numpy as np
from robobase import DataChannel, RawDataProducer, Environment, ThreadGroup, Controller, ActionsQueue, Actions2Robot
from robobase.data_producers2channels import DataProducers2Channels

TARGET = "helloworld"

class BasicEnv(Environment):
    def __init__(self):
        Environment.__init__(self, frequency=30)
        self._state = []
        self._lock = threading.Lock()
    def push(self, action):
        with self._lock:
            self._state.append(action)
    def is_running(self) -> bool:
        return len(self._state) != len(TARGET)
    def get_state(self) -> dict:
        with self._lock:
            return {"ts": datetime.now().isoformat(), "state": deepcopy(self._state)} # important to deepcopy :)
    def get_modalities(self) -> list[str]:
        return ["ts", "state"]

def test_i_DataChannel_replay_from_logs(tmp_path: Path):
    env = BasicEnv()
    shutil.rmtree(tmp_path, ignore_errors=True)
    channel = DataChannel(supported_types=["ts", "state"], eq_fn=lambda a, b: a["state"] == b["state"],
                          log_path=tmp_path)
    actions_queue = ActionsQueue(Queue(), actions=list(map(chr, range(ord("a"), ord("z") + 1)))) # from 'a' to 'z'

    raw_dp = RawDataProducer(env)
    env2data = DataProducers2Channels([raw_dp], [channel])
    # push 'h' if env._state==[], 'e' if env._state==['h'] and so on until helloworld
    controller_fn = lambda data: TARGET[len(data["state"])] if len(data["state"]) < len(TARGET) else None # noqa
    data2actions = Controller(channel, actions_queue, controller_fn)
    actions2env = Actions2Robot(env, actions_queue, action_fn=lambda env, action: env.push(action))

    tg = ThreadGroup({
        "env2data": env2data,
        "data2actions": data2actions,
        "actions2env": actions2env,
    }).start()

    while not tg.is_any_dead():
        time.sleep(0.1)
    tg.join(timeout=0.1)
    channel.close()

    print(f"Final state: '{''.join(env._state)}'")
    assert "".join(env._state) == TARGET

    time.sleep(0.1)
    files = sorted(list(Path(channel.log_path).iterdir()), key=lambda p: p.name)
    data = [np.load(x, allow_pickle=True).item() for x in files]
    for i in range(len(data)):
        assert "".join(data[i]["state"]) == TARGET[0:i]

if __name__ == "__main__":
    test_i_DataChannel_replay_from_logs(Path(__file__).parent / Path(__file__).stem)
