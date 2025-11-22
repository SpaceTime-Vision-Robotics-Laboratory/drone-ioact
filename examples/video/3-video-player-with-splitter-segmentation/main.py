#!/usr/bin/env python3
"""keyboard controller and display example with frames of a video + semantic segmentation"""
# pylint: disable=duplicate-code
from __future__ import annotations
from queue import Queue
from argparse import ArgumentParser, Namespace
import time
import logging
from vre_video import VREVideo
import numpy as np

from mask_splitter_data_producer import MaskSplitterDataProducer

from drone_ioact.data_producers.object_detection import YOLODataProducer
from drone_ioact import ActionsQueue, DataChannel, DataItem
from drone_ioact.drones.video import (
    VideoPlayer, VideoActionsConsumer, VideoDataProducer, video_actions_callback, VIDEO_SUPPORTED_ACTIONS)
from drone_ioact.data_consumers import ScreenDisplayer, KeyboardController
from drone_ioact.utils import (logger, ThreadGroup, image_draw_rectangle, image_paste, image_draw_circle)

Color = tuple[int, int, int]
logging.getLogger("ultralytics").setLevel(logging.CRITICAL)

COLOR_RED = (255, 0, 0)
COLOR_GREEN = (0, 255, 0)
COLOR_BLUE = (0, 0, 255)
COLOR_WHITE = (255, 255, 255)

QUEUE_MAX_SIZE = 30
SCREEN_HEIGHT = 480 # width is auto-scaled
SEGMENTATION_COLOR = (0, 200, 0)
BBOX_COLOR = COLOR_GREEN
BBOX_THICKNESS = 2

def screen_frame_callback(data: DataItem) -> np.ndarray:
    """produces RGB + semantic segmentation as a single frame"""
    res = data["rgb"]
    if data["bbox"] is not None:
        for bbox in data["bbox"]: # plot all bboxes
            x1, y1, x2, y2 = bbox
            res = image_draw_rectangle(res, (x1, y1), (x2, y2), color=BBOX_COLOR, thickness=BBOX_THICKNESS)

    # if data["segmentation"] is not None:
    #     all_segmentations = data["segmentation"].sum(0)[..., None].repeat(3, axis=-1) * SEGMENTATION_COLOR
    #     img_segmentations = image_resize(all_segmentations.astype(np.uint8), *res.shape[0:2])
    #     res = image_paste(res, img_segmentations)

    if data["bbox_oriented"] is not None:
        p1, p2, p3, p4 = data["bbox_oriented"]
        res = image_draw_circle(res, p1, radius=5, color=COLOR_RED, thickness=-1)
        res = image_draw_circle(res, p2, radius=5, color=COLOR_GREEN, thickness=-1)
        res = image_draw_circle(res, p3, radius=5, color=COLOR_BLUE, thickness=-1)
        res = image_draw_circle(res, p4, radius=5, color=COLOR_WHITE, thickness=-1)

    if data["front_mask"] is not None:
        res = image_paste(res, (data["front_mask"][..., None].repeat(3, axis=-1) * COLOR_RED).astype(np.uint8))
    if data["back_mask"] is not None:
        res = image_paste(res, (data["back_mask"][..., None].repeat(3, axis=-1) * COLOR_GREEN).astype(np.uint8))

    return res

def get_args() -> Namespace:
    """cli args"""
    parser = ArgumentParser()
    parser.add_argument("video_path")
    # yolo params
    parser.add_argument("--weights_path_yolo", required=True)
    parser.add_argument("--yolo_bbox_threshold", default=0.75, type=float)
    # spliter network params
    parser.add_argument("--weights_path_mask_splitter_network", required=True)
    parser.add_argument("--mask_splitter_network_mask_threshold", default=0.5, type=float)
    parser.add_argument("--mask_splitter_network_bbox_threshold", default=0.5, type=float)
    args = parser.parse_args()
    return args

def main(args: Namespace):
    """main fn"""
    (video_player := VideoPlayer(VREVideo(args.video_path))).start() # start the video player

    actions_queue = ActionsQueue(Queue(maxsize=QUEUE_MAX_SIZE), actions=VIDEO_SUPPORTED_ACTIONS)
    supported_types = ["bbox", "rgb", "splitter_segmentation", "frame_ix", "front_mask",
                       "bbox_oriented", "segmentation_xy", "segmentation", "bbox_confidence", "back_mask"]
    data_channel = DataChannel(supported_types=supported_types, eq_fn=lambda a, b: a["frame_ix"] == b["frame_ix"])

    # define the threads of the app
    rgb_data_producer = VideoDataProducer(video_player=video_player, data_channel=data_channel)
    yolo_data_producer = YOLODataProducer(rgb_data_producer, weights_path=args.weights_path_yolo,
                                          bbox_threshold=args.yolo_bbox_threshold)
    mask_splitter_data_producer = MaskSplitterDataProducer(yolo_data_producer, args.weights_path_mask_splitter_network,
                                                           mask_threshold=args.mask_splitter_network_mask_threshold,
                                                           bbox_threshold=args.mask_splitter_network_bbox_threshold)

    screen_displayer = ScreenDisplayer(data_channel, SCREEN_HEIGHT, screen_frame_callback=screen_frame_callback)
    key_to_action = {"Key.space": "PLAY_PAUSE", "q": "DISCONNECT", "Key.right": "SKIP_AHEAD_ONE_SECOND",
                     "Key.left": "GO_BACK_ONE_SECOND"}
    kb_controller = KeyboardController(data_channel=data_channel, actions_queue=actions_queue,
                                       key_to_action=key_to_action)
    video_actions_consumer = VideoActionsConsumer(video_player=video_player, actions_queue=actions_queue,
                                                  actions_callback=video_actions_callback)

    # start the threads
    threads = ThreadGroup({
        "Data producer": mask_splitter_data_producer,
        "Screen displayer": screen_displayer,
        "Keyboard controller": kb_controller,
        "Video actions consumer": video_actions_consumer,
    }).start()

    while not threads.is_any_dead():
        logger.debug2(f"{data_channel}. Actions queue size: {len(actions_queue)}")
        time.sleep(1)

    video_player.stop_video()
    threads.join(timeout=1)

if __name__ == "__main__":
    main(get_args())
