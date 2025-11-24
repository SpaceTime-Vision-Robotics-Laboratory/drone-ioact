#!/usr/bin/env python3
"""
IBVS example using: yolo + mask splitter networks
Usage: ./main.py DRONE_IP --weights_path_yolo 29_05_best__yolo11n-seg_sim_car_bunker__all.pt --weights_path_mask_splitter_network mask_splitter-sim-high-quality-partition-v10-dropout_0-augmentations_multi_scenes.pt # pylint:disable=line-too-long
"""
# pylint: disable=duplicate-code
from __future__ import annotations
from queue import Queue
from argparse import ArgumentParser, Namespace
import time
import logging
import numpy as np
import olympe

from mask_splitter_data_producer import MaskSplitterDataProducer

from drone_ioact.data_producers.object_detection import YOLODataProducer
from drone_ioact import ActionsQueue, DataChannel, DataItem
from drone_ioact.drones.olympe_parrot import (
    OlympeDataProducer, OlympeActionsConsumer, olympe_actions_callback, OLYMPE_SUPPORTED_ACTIONS)
from drone_ioact.data_consumers import ScreenDisplayer
from drone_ioact.utils import (logger, ThreadGroup, image_draw_rectangle, image_paste,
                               image_draw_circle, image_resize, Color)

logging.getLogger("ultralytics").setLevel(logging.CRITICAL)

QUEUE_MAX_SIZE = 30
SCREEN_HEIGHT = 480 # width is auto-scaled
BBOX_THICKNESS = 0.75
CIRCLE_RADIUS = 1

def screen_frame_callback(data: DataItem) -> np.ndarray:
    """produces RGB + semantic segmentation as a single frame"""
    res = data["rgb"].copy()
    shp = res.shape[0:2]

    if data["bbox"] is not None:
        data["bbox"] = data["bbox"][0:1] # plot just top-1 bbox
        for bbox in data["bbox"]:
            x1, y1, x2, y2 = bbox
            image_draw_rectangle(res, (y1, x1), (y2, x2), color=Color.GREEN, thickness=BBOX_THICKNESS, inplace=True)

    if data["segmentation"] is not None:
        all_segmentations = data["segmentation"].sum(0)[..., None].repeat(3, axis=-1) * Color.GREENISH
        img_segmentations = image_resize(all_segmentations.astype(np.uint8), *shp)
        image_paste(res, img_segmentations, inplace=True)

    if data["bbox_oriented"] is not None:
        p1, p2, p3, p4 = [p[::-1] for p in data["bbox_oriented"]]
        image_draw_circle(res, p1, radius=CIRCLE_RADIUS, color=Color.RED, fill=True, inplace=True)
        image_draw_circle(res, p2, radius=CIRCLE_RADIUS, color=Color.GREEN, fill=True, inplace=True)
        image_draw_circle(res, p3, radius=CIRCLE_RADIUS, color=Color.BLUE, fill=True, inplace=True)
        image_draw_circle(res, p4, radius=CIRCLE_RADIUS, color=Color.WHITE, fill=True, inplace=True)

    if data["front_mask"] is not None:
        front_mask = image_resize((data["front_mask"][..., None].repeat(3, axis=-1) * Color.RED).astype(np.uint8), *shp)
        image_paste(res, front_mask, inplace=True)
    if data["back_mask"] is not None:
        back_mask = image_resize((data["back_mask"][..., None].repeat(3, axis=-1) * Color.RED).astype(np.uint8), *shp)
        image_paste(res, back_mask, inplace=True)

    return res

def get_args() -> Namespace:
    """cli args"""
    parser = ArgumentParser()
    parser.add_argument("drone_ip")
    # yolo params
    parser.add_argument("--weights_path_yolo", required=True)
    parser.add_argument("--yolo_threshold", default=0.75, type=float)
    # spliter network params
    parser.add_argument("--weights_path_mask_splitter_network", required=True)
    parser.add_argument("--mask_splitter_network_mask_threshold", default=0.5, type=float)
    parser.add_argument("--mask_splitter_network_bbox_threshold", default=0.5, type=float)
    args = parser.parse_args()
    return args

def main(args: Namespace):
    """main fn"""
    drone = olympe.Drone(args.drone_ip)
    assert drone.connect(), f"could not connect to '{args.drone_ip}'"

    actions_queue = ActionsQueue(Queue(maxsize=QUEUE_MAX_SIZE), actions=OLYMPE_SUPPORTED_ACTIONS)
    supported_types = ["bbox", "rgb", "splitter_segmentation", "metadata", "front_mask",
                       "bbox_oriented", "segmentation_xy", "segmentation", "bbox_confidence", "back_mask"]
    data_channel = DataChannel(supported_types=supported_types,
                               eq_fn=lambda a, b: a["metadata"]["time"] == b["metadata"]["time"])

    # define the threads of the app
    data_producer = OlympeDataProducer(drone=drone, data_channel=data_channel)
    yolo_data_producer = YOLODataProducer(data_producer, weights_path=args.weights_path_yolo,
                                          threshold=args.yolo_threshold)
    mask_splitter_data_producer = MaskSplitterDataProducer(yolo_data_producer, args.weights_path_mask_splitter_network,
                                                           mask_threshold=args.mask_splitter_network_mask_threshold,
                                                           bbox_threshold=args.mask_splitter_network_bbox_threshold)
    key_to_action = {"Escape": "DISCONNECT", "space": "LIFT", "b": "LAND",
                     "w": "FORWARD", "a": "LEFT", "s": "BACKWARD", "d": "RIGHT",
                     "Up": "INCREASE_HEIGHT", "Down": "DECREASE_HEIGHT", "Left": "ROTATE_LEFT", "Right": "ROTATE_RIGHT"}
    screen_displayer = ScreenDisplayer(data_channel, actions_queue, screen_height=SCREEN_HEIGHT,
                                       screen_frame_callback=screen_frame_callback, key_to_action=key_to_action)
    video_actions_consumer = OlympeActionsConsumer(drone=drone, actions_queue=actions_queue,
                                                  actions_callback=olympe_actions_callback)

    # start the threads
    threads = ThreadGroup({
        "Data producer": mask_splitter_data_producer,
        "Screen displayer": screen_displayer,
        "Video actions consumer": video_actions_consumer,
    }).start()

    while not threads.is_any_dead():
        logger.debug2(f"{data_channel}. Actions queue size: {len(actions_queue)}")
        time.sleep(1)

    drone.disconnect()
    threads.join(timeout=1)

if __name__ == "__main__":
    main(get_args())
