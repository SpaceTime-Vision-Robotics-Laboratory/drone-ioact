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
from loggez import loggez_logger as logger

from robobase import ActionsQueue, DataChannel, DataItem, ThreadGroup, DataProducerList, ActionConsumer
from roboimpl.data_producers.semantic_segmentation import PHGMAESemanticDataProducer
from roboimpl.data_producers.object_detection import YOLODataProducer
from roboimpl.drones.video import VideoPlayer, VideoDataProducer, video_actions_fn, VIDEO_SUPPORTED_ACTIONS
from roboimpl.controllers import ScreenDisplayer
from roboimpl.utils import semantic_map_to_image, image_draw_rectangle, image_resize, image_paste, Color

logging.getLogger("ultralytics").setLevel(logging.CRITICAL)
QUEUE_MAX_SIZE = 30
SCREEN_HEIGHT = 480 # width is auto-scaled

BBOX_THICKNES = 1

def screen_frame_callback(data: dict[str, DataItem], color_map: list[Color], only_top1_bbox: bool) -> np.ndarray:
    """produces RGB + semantic segmentation as a single frame"""
    if "bbox" in data and data["bbox"] is not None:
        data["bbox"] = data["bbox"][0:1] if only_top1_bbox else data["bbox"]
        for bbox in data["bbox"]:
            x1, y1, x2, y2 = bbox
            data["rgb"] = image_draw_rectangle(data["rgb"], top_left=(y1, x1), bottom_right=(y2, x2),
                                               color=Color.GREEN, thickness=BBOX_THICKNES)

    if "segmentation" in data and data["segmentation"] is not None:
        # merge all segmentation masks together (as bools)
        data["segmentation"] = data["segmentation"][0:1] if only_top1_bbox else data["segmentation"]
        all_segmentations = data["segmentation"].sum(0)[..., None].repeat(3, axis=-1)
        all_segmentations = (all_segmentations * Color.GREENISH).astype(np.uint8)
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
    parser.add_argument("--yolo_threshold", default=0.75, type=float, help="applied to both bbox and segmentation")
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
        supported_types.extend(["bbox", "bbox_confidence", "segmentation", "segmentation_xy"])

    data_channel = DataChannel(supported_types=supported_types, eq_fn=lambda a, b: a["frame_ix"] == b["frame_ix"])

    # define the threads of the app
    dps = [VideoDataProducer(video_player=video_player)]
    if args.weights_path_phg is not None:
        dps.append(PHGMAESemanticDataProducer(weights_path=args.weights_path_phg))
    if args.weights_path_yolo is not None:
        dps.append(YOLODataProducer(weights_path=args.weights_path_yolo, threshold=args.yolo_threshold))
    data_producers = DataProducerList(data_channel, dps)

    f_screen_frame_callback = partial(screen_frame_callback, color_map=PHGMAESemanticDataProducer.COLOR_MAP,
                                      only_top1_bbox=args.yolo_only_top1_bbox)
    key_to_action = {"space": "PLAY_PAUSE", "q": "DISCONNECT", "Right": "SKIP_AHEAD_ONE_SECOND",
                     "Left": "GO_BACK_ONE_SECOND"}
    screen_displayer = ScreenDisplayer(data_channel, actions_queue, screen_height=SCREEN_HEIGHT,
                                       screen_frame_callback=f_screen_frame_callback, key_to_action=key_to_action)
    action2video = ActionConsumer(actions_queue=actions_queue, termination_fn=lambda: video_player.is_done,
                                  actions_fn=partial(video_actions_fn, video_player=video_player))

    # start the threads
    threads = ThreadGroup({
        "Video -> Data": data_producers,
        "Semantic screen displayer": screen_displayer,
        "Action -> Video": action2video,
    }).start()

    while not threads.is_any_dead():
        logger.trace(f"{data_channel}. Actions queue size: {len(actions_queue)}")
        time.sleep(1)

    video_player.stop_video()
    threads.join(timeout=1)

if __name__ == "__main__":
    main(get_args())
