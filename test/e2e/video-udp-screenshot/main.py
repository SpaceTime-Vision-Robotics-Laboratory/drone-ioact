#!/usr/bin/env python3
"""keyboard controller and display example with frames of a video not a real or simulated drone"""
# pylint: disable=duplicate-code
from __future__ import annotations
from queue import Queue
from pathlib import Path
from argparse import ArgumentParser, Namespace
import time

from drone_ioact import Action, ActionsQueue, ActionsConsumer
from drone_ioact.drones.video import VideoFrameReader
from drone_ioact.data_consumers import UDPController
from drone_ioact.utils import logger, ThreadGroup, image_write

QUEUE_MAX_SIZE = 30
SCREEN_HEIGHT = 420

class VideoActionsMaker(ActionsConsumer):
    """VideoActionsMaker defines the actions taken on the video container based on the actions produced"""
    def __init__(self, video: VideoFrameReader, actions_queue: Queue):
        super().__init__(actions_queue, VideoActionsMaker.video_action_callback)
        self.video = video

    def stop_streaming(self):
        self.video.is_done = True

    def is_streaming(self) -> bool:
        return not self.video.is_done

    @staticmethod
    def video_action_callback(actions_maker: VideoActionsMaker, action: Action) -> bool:
        """the actions callback from generic actions to video-specific ones"""
        video = actions_maker.video
        if action == "DISCONNECT":
            actions_maker.stop_streaming()
        if action == "PLAY_PAUSE":
            video.is_paused = not video.is_paused
        if action == "SKIP_AHEAD_ONE_SECOND":
            video.increment_frame(video.fps)
        if action == "GO_BACK_ONE_SECOND":
            video.increment_frame(-video.fps)
        if action == "TAKE_SCREENSHOT":
            image_write(video.get_current_data()["rgb"], pth := f"{Path.cwd()}/frame.png")
            logger.debug(f"Stored screenshot at '{pth}'")
        return True

def get_args() -> Namespace:
    """cli args"""
    parser = ArgumentParser()
    parser.add_argument("video_path")
    parser.add_argument("--port", type=int, default=42069)
    args = parser.parse_args()
    return args

def main(args: Namespace):
    """main fn"""
    (video_frame_reader := VideoFrameReader(args.video_path)).start() # start the video thread so it produces rt frames
    actions = ["DISCONNECT", "PLAY_PAUSE", "SKIP_AHEAD_ONE_SECOND", "GO_BACK_ONE_SECOND", "TAKE_SCREENSHOT"]
    actions_queue = ActionsQueue(Queue(maxsize=QUEUE_MAX_SIZE), actions=actions)

    udp_controller = UDPController(port=args.port, data_producer=video_frame_reader, actions_queue=actions_queue)
    video_actions_maker = VideoActionsMaker(video=video_frame_reader, actions_queue=actions_queue)

    threads = ThreadGroup({
        "UDP controller": udp_controller,
        "Video actions maker": video_actions_maker,
    })
    threads.start()

    while video_frame_reader.is_streaming() and not threads.is_any_dead():
        logger.debug2(f"Queue size: {len(actions_queue)}")
        time.sleep(1)

    video_actions_maker.stop_streaming()
    threads.join(timeout=1)

if __name__ == "__main__":
    main(get_args())
