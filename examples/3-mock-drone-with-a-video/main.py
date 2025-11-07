#!/usr/bin/env python3
from queue import Queue
import sys
import time
import numpy as np
from vre_video import VREVideo

# from drone_ioact.olympe import OlympeFrameReader, OlympeActionsMaker
from drone_ioact import DroneIn
from drone_ioact.data_consumers import ScreenDisplayer, KeyboardController
from drone_ioact.utils import logger

QUEUE_MAX_SIZE = 30

class VideoFrameReader(DroneIn):
    def __init__(self, video: VREVideo):
        self.video = video
        self._is_streaming = True
        self._frame_ix = 0

    def get_current_data(self, timeout_s: int = 10) -> dict[str, np.ndarray]:
        data = self.video[self._frame_ix]
        self._frame_ix = (self._frame_ix + 1) % len(self.video)
        return {"rgb": data}

    def is_streaming(self) -> bool:
        return self._is_streaming

    def stop_streaming(self):
        self._is_streaming = False

def main():
    """main fn"""
    video = VREVideo(sys.argv[1])
    logger.info(f"Read video: {video}")
    actions_queue = Queue(maxsize=QUEUE_MAX_SIZE)

    # data producer thread (1) (drone I/O in -> data/RGB out)
    video_frame_reader = VideoFrameReader(video=video)
    # data consumer threads (data/RGB in -> I/O out)
    screen_displayer = ScreenDisplayer(drone_in=video_frame_reader)
    # # data consumer & actions producer threads (data/RGB in -> action out)
    kb_controller = KeyboardController(drone_in=video_frame_reader, actions_queue=actions_queue)
    # # actions consumer thread (1) (action in -> drone I/O out)
    # olympe_actions_maker = OlympeActionsMaker(drone=drone, actions_queue=actions_queue)

    while True:
        threads = {
            "Video frame reader": video_frame_reader.is_streaming(),
            "Keyboard controller": kb_controller.is_alive(),
            "Screen displayer": screen_displayer.is_alive(),
            # "Olympe actions maker": olympe_actions_maker.is_alive(),
        }
        if any(v is False for v in threads.values()):
            logger.info("\n".join(f"- {k}: {v}" for k, v in threads.items()))
            break
        time.sleep(1)
    video_frame_reader.stop_streaming()

if __name__ == '__main__':
    main()
