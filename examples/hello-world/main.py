#!/usr/bin/env python3
"""basic minimal example to create and env, a data channel/actions queue and the middle part: dp, controller etc."""
import time
import shutil
import threading
from pathlib import Path
from queue import Queue
from copy import deepcopy
from datetime import datetime
from robobase import DataChannel, RawDataProducer, Environment, ThreadGroup, Controller, ActionsQueue, Actions2Robot
from robobase.data_producers2channels import DataProducers2Channels

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
    """the main function"""
    env = BasicEnv()
    shutil.rmtree(tmp_path, ignore_errors=True)
    channel = DataChannel(supported_types=["ts", "state"], eq_fn=lambda a, b: a["state"] == b["state"],
                          log_path=tmp_path)
    actions_queue = ActionsQueue(Queue(), actions=list(map(chr, range(ord("a"), ord("z") + 1)))) # from 'a' to 'z'

    raw_dp = RawDataProducer(env)
    env2data = DataProducers2Channels([raw_dp], [channel])
    # push 'h' if env._state==[], 'e' if env._state==['h'] and so on until helloworld
    controller_fn = lambda data: TARGET[len(data["state"])] if len(data["state"]) < len(TARGET) else None # pylint: disable=all #noqa
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

    print(f"Final state: '{''.join(env.get_state()['state'])}'")
    assert "".join(env.get_state()['state']) == TARGET

if __name__ == "__main__":
    main(Path(__file__).parent / Path(__file__).stem)
