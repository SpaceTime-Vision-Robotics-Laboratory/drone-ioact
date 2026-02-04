#!/usr/bin/env python3
"""most minimal end to end example from environment (state) to controller and back to environment (action->new state)"""
# TODO: make a test out of this too.
import time
import threading
from queue import Queue
from datetime import datetime
from robobase import DataChannel, RawDataProducer, Environment, ThreadGroup, Controller, ActionsQueue, Actions2Robot
from robobase.data_producers2channels import DataProducers2Channels
from robobase.utils import logger

TARGET = "helloworld"

class TestEnv(Environment):
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
        return {"ts": datetime.now().isoformat(), "state": self._state}
    def get_modalities(self) -> list[str]:
        return ["ts", "state"]

def test_i_DataChannel_replay_from_logs():
    env = TestEnv()
    channel = DataChannel(supported_types=["ts", "state"], eq_fn=lambda a, b: a["state"] == b["state"])
    actions_queue = ActionsQueue(Queue(), actions=list(map(chr, range(ord("a"), ord("z")+1)))) # from 'a' to 'z'

    raw_dp = RawDataProducer(env)
    env2data = DataProducers2Channels([raw_dp], [channel])
    # push 'h' if env._state==[], 'e' if env._state==['h'] and so on until helloworld
    controller_fn = lambda data: TARGET[len(data["state"])] if len(data["state"]) < len(TARGET) else None
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
    assert "".join(env._state) == "helloworld"

if __name__ == "__main__":
    test_i_DataChannel_replay_from_logs()
