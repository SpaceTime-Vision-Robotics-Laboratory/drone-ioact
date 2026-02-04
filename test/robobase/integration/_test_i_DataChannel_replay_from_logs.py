import time
import random
import threading
import shutil
from pathlib import Path
from queue import Queue
from datetime import datetime
import numpy as np
from robobase import DataChannel, RawDataProducer, Environment, ThreadGroup, Controller, ActionsQueue, Actions2Robot
from robobase.data_producers2channels import DataProducers2Channels

class TestEnv(Environment):
    def __init__(self):
        Environment.__init__(self, frequency=30)
        self._state = []
        self._lock = threading.Lock()
    def push(self, action):
        with self._lock:
            self._state.append(action)
    def is_running(self) -> bool:
        return len(self._state) < 100
    def get_state(self) -> dict:
        return {"ts": datetime.now().isoformat()[0:-4], "state": self._state}
    def get_modalities(self) -> list[str]:
        return ["ts", "state"]

def test_i_DataChannel_replay_from_logs():
    env = TestEnv()
    log_path = Path(__file__).parent / "test_i_DataChannel_replay_from_logs/"
    shutil.rmtree(log_path, ignore_errors=True)
    channel = DataChannel(supported_types=["ts", "state"], eq_fn=lambda a, b: a["ts"] == b["ts"], log_path=log_path)
    actions_queue = ActionsQueue(Queue(), actions=["a1", "a2"])

    raw_dp = RawDataProducer(env)
    env2data = DataProducers2Channels([raw_dp], [channel])

    data2actions = Controller(channel, actions_queue, lambda data: random.choice(["a1", "a2"]))
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

    files = sorted(list(Path(channel.log_path).iterdir()), key=lambda p: p.name)
    data = [np.load(x, allow_pickle=True).item() for x in files]
    print(f"Loaded {len(data)} items. Keys: {data[0].keys()}.")
    for i in range(len(data)):
        if len(data[i]["state"]) > i:
            breakpoint()

if __name__ == "__main__":
    test_i_DataChannel_replay_from_logs()
