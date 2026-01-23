#!/usr/bin/env python3
"""keyboard controller and display example with frames of a video + semantic segmentation"""
# pylint: disable=duplicate-code
from __future__ import annotations
from queue import Queue
from datetime import datetime
import threading
import time
import numpy as np

from robobase import (ActionsQueue, DataChannel, DataItem, ThreadGroup, DataProducerList,
                      Actions2Robot, LambdaDataProducer, Planner, Action)

N_FRAMES = 60
N1 = 0
N2 = 0

class FakeVideo(threading.Thread):
    def __init__(self, frames: np.ndarray, fps: int):
        super().__init__()
        self.frames = frames
        self.fps = fps
        self._frame_ix = 0
        self._current_frame = frames[0]
        self._lock = threading.Lock()

    def get(self) -> dict[str, np.ndarray | int]:
        with self._lock:
            return {"rgb": self._current_frame, "frame_ix": self._frame_ix}

    def run(self):
        while self._frame_ix < len(self.frames):
            now = datetime.now()
            with self._lock:
                self._current_frame = self.frames[self._frame_ix]
                self._frame_ix += 1
            if (diff := (1 / self.fps - (datetime.now() - now).total_seconds())) > 0:
                time.sleep(diff)

def rgb_rev_produce_fn(deps: dict[str, DataItem] | None = None) -> dict[str, DataItem]:
    """fake some lag for the second producer"""
    time.sleep(0.5)
    return {"rgb_rev": deps["rgb"][:, ::-1]}

def planner_fn1(data: dict[str, DataItem]) -> Action:
    global N1
    N1 += 1
    return None

def planner_fn2(data: dict[str, DataItem]) -> Action:
    global N2
    N2 += 1
    return None

def test_i_multiple_data_producer_list():
    """main fn"""
    frames = np.random.randint(0, 255, size=(N_FRAMES, 30, 30, 3), dtype=np.uint8)
    (video_player := FakeVideo(frames, fps=30)).start() # start the video player

    actions_queue = ActionsQueue(Queue(), actions=["a"])
    dc1 = DataChannel(supported_types=["rgb", "frame_ix"], eq_fn=lambda a, b: a["frame_ix"] == b["frame_ix"])
    dc2 = DataChannel(supported_types=["rgb", "frame_ix", "rgb_rev"], eq_fn=lambda a, b: a["frame_ix"] == b["frame_ix"])

    video_dp = LambdaDataProducer(lambda deps: video_player.get(), modalities=["rgb", "frame_ix"], dependencies=[])
    rgb_rev_dp = LambdaDataProducer(rgb_rev_produce_fn, modalities=["rgb_rev"], dependencies=["rgb"])
    dpl1 = DataProducerList(dc1, [video_dp])
    dpl2 = DataProducerList(dc2, [video_dp, rgb_rev_dp])
    ctrl1 = Planner(dc1, actions_queue, planner_fn1)
    ctrl2 = Planner(dc2, actions_queue, planner_fn2)
    action2video = Actions2Robot(actions_queue=actions_queue, action_fn=lambda : None,
                                 termination_fn=lambda: video_player._frame_ix < len(frames))

    # start the threads
    threads = ThreadGroup({
        "Video -> Data1": dpl1,
        "Video -> Data2": dpl2,
        "Ctrl1": ctrl1,
        "Ctrl2": ctrl2,
        "Action -> Video": action2video,
    }).start()

    while not threads.is_any_dead():
        pass

    threads.join(timeout=1)
    assert N1 > 20, N1
    assert N2 < 10, N2

if __name__ == "__main__":
    test_i_multiple_data_producer_list()
