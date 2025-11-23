#!/usr/bin/env python3
"""keyboard controller and display example with frames of a video + semantic segmentation"""
# pylint: disable=duplicate-code
from __future__ import annotations
from queue import Queue
from functools import partial
from argparse import ArgumentParser, Namespace
import time
import logging
from vre_video import VREVideo
import numpy as np

from drone_ioact.data_producers.semantic_segmentation import PHGMAESemanticDataProducer
from drone_ioact.data_producers.object_detection import YOLODataProducer
from drone_ioact import ActionsQueue, DataChannel, DataItem
from drone_ioact.drones.video import (
    VideoPlayer, VideoActionsConsumer, VideoDataProducer, video_actions_callback, VIDEO_SUPPORTED_ACTIONS)
from drone_ioact.data_consumers import ScreenDisplayer, KeyboardController
from drone_ioact.utils import (logger, ThreadGroup, semantic_map_to_image, image_draw_rectangle,
                               image_resize, image_paste)

logging.getLogger("ultralytics").setLevel(logging.CRITICAL)
QUEUE_MAX_SIZE = 30
SCREEN_HEIGHT = 480 # width is auto-scaled
Color = tuple[int, int, int]

COLOR_GREEN = (0, 255, 0)
COLOR_GREENISH = (0, 200, 0)
BBOX_THICKNES = 1

def screen_frame_callback(data: DataItem, color_map: list[Color], only_top1_bbox: bool) -> np.ndarray:
    """produces RGB + semantic segmentation as a single frame"""
    if "bbox" in data and data["bbox"] is not None:
        data["bbox"] = data["bbox"][0:1] if only_top1_bbox else data["bbox"]
        for bbox in data["bbox"]:
            x1, y1, x2, y2 = bbox
            data["rgb"] = image_draw_rectangle(data["rgb"], top_left=(y1, x1), bottom_right=(y2, x2),
                                               color=COLOR_GREEN, thickness=BBOX_THICKNES)

    if "segmentation" in data and data["segmentation"] is not None:
        # merge all segmentation masks together (as bools)
        data["segmentation"] = data["segmentation"][0:1] if only_top1_bbox else data["segmentation"]
        all_segmentations = data["segmentation"].sum(0)[..., None].repeat(3, axis=-1)
        all_segmentations = (all_segmentations * COLOR_GREENISH).astype(np.uint8)
        img_segmentations = image_resize(all_segmentations, *data["rgb"].shape[0:2])
        data["rgb"] = image_paste(data["rgb"], img_segmentations)

    res = data["rgb"]
    if "semantic" in data:
        sema_rgb = semantic_map_to_image(data["semantic"].argmax(-1), color_map)
        res = np.concatenate([data["rgb"], sema_rgb], axis=1)

    return res

def get_args() -> Namespace:
    """cli args"""
    parser = ArgumentParser()
    parser.add_argument("video_path")
    # yolo params
    parser.add_argument("--weights_path_yolo")
    parser.add_argument("--yolo_bbox_threshold", default=0.75, type=float)
    parser.add_argument("--yolo_only_top1_bbox", action="store_true")
    # phg-mae params
    parser.add_argument("--weights_path_phg")
    args = parser.parse_args()
    return args

def main(args: Namespace):
    """main fn"""
    (video_player := VideoPlayer(VREVideo(args.video_path))).start() # start the video player

    actions_queue = ActionsQueue(Queue(maxsize=QUEUE_MAX_SIZE), actions=VIDEO_SUPPORTED_ACTIONS)
    supported_types = ["rgb", "frame_ix"]
    supported_types = supported_types if args.weights_path_phg is None else [*supported_types, "semantic"]
    if args.weights_path_yolo:
        supported_types.extend(["bbox", "bbox_confidence"])

    data_channel = DataChannel(supported_types=supported_types, eq_fn=lambda a, b: a["frame_ix"] == b["frame_ix"])

    # define the threads of the app
    data_producer = VideoDataProducer(video_player=video_player, data_channel=data_channel)
    if args.weights_path_phg is not None:
        data_producer = PHGMAESemanticDataProducer(data_producer, weights_path=args.weights_path_phg)
    if args.weights_path_yolo is not None:
        data_producer = YOLODataProducer(data_producer, weights_path=args.weights_path_yolo,
                                         bbox_threshold=args.yolo_bbox_threshold)
        if data_producer.has_segmentation:
            data_channel.supported_types.update(["segmentation", "segmentation_xy"])

    f_screen_frame_callback = partial(screen_frame_callback, color_map=PHGMAESemanticDataProducer.COLOR_MAP,
                                      only_top1_bbox=args.yolo_only_top1_bbox)
    screen_displayer = ScreenDisplayer(data_channel, SCREEN_HEIGHT, screen_frame_callback=f_screen_frame_callback)
    key_to_action = {"Key.space": "PLAY_PAUSE", "q": "DISCONNECT", "Key.right": "SKIP_AHEAD_ONE_SECOND",
                     "Key.left": "GO_BACK_ONE_SECOND"}
    kb_controller = KeyboardController(data_channel=data_channel, actions_queue=actions_queue,
                                       key_to_action=key_to_action)
    video_actions_consumer = VideoActionsConsumer(video_player=video_player, actions_queue=actions_queue,
                                                  actions_callback=video_actions_callback)

    # start the threads
    threads = ThreadGroup({
        "Semantic data producer": data_producer,
        "Semantic screen displayer": screen_displayer,
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
