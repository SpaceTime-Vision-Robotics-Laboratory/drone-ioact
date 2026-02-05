#!/usr/bin/env python3
"""
yolo + mask splitter example with frames stored during a olympe simulator run
Usage: VIDEO_FPS=15 ./main.py ../frames/ --weights_path_yolo 29_05_best__yolo11n-seg_sim_car_bunker__all.pt --weights_path_mask_splitter_network mask_splitter-sim-high-quality-partition-v10-dropout_0-augmentations_multi_scenes.pt # pylint:disable=line-too-long
"""
# pylint: disable=duplicate-code
from __future__ import annotations
from argparse import ArgumentParser, Namespace
import logging
from vre_video import VREVideo
import numpy as np
from loggez import loggez_logger as logger

from mask_splitter_data_producer import MaskSplitterDataProducer

from robobase import Robot, DataChannel, ActionsQueue, DataItem
from roboimpl.data_producers.object_detection import YOLODataProducer
from roboimpl.envs.video import VideoPlayerEnv, video_action_fn, VIDEO_SUPPORTED_ACTIONS
from roboimpl.controllers import ScreenDisplayer
from roboimpl.utils import image_draw_rectangle, image_paste, image_draw_circle, Color

logging.getLogger("ultralytics").setLevel(logging.CRITICAL)

DEFAULT_SCREEN_RESOLUTION = 480, 640
BBOX_THICKNESS = 0.75
CIRCLE_RADIUS = 1.25
BGR = False # some yolo models may be trained with BGR images instead!

def screen_frame_callback(data: dict[str, DataItem]) -> np.ndarray:
    """produces RGB + semantic segmentation as a single frame"""
    res = data["rgb"].copy()

    if data["segmentation"] is not None:
        all_segmentations = data["segmentation"].sum(0).repeat(3, axis=-1) * Color.GREENISH
        image_paste(res, all_segmentations.astype(np.uint8), inplace=True)

    if data["bbox_oriented"] is not None:
        p1, p2, p3, p4 = [p[::-1] for p in data["bbox_oriented"]]
        image_draw_circle(res, p1, radius=CIRCLE_RADIUS, color=Color.RED, fill=True, inplace=True)
        image_draw_circle(res, p2, radius=CIRCLE_RADIUS, color=Color.GREEN, fill=True, inplace=True)
        image_draw_circle(res, p3, radius=CIRCLE_RADIUS, color=Color.BLUE, fill=True, inplace=True)
        image_draw_circle(res, p4, radius=CIRCLE_RADIUS, color=Color.WHITE, fill=True, inplace=True)

    if data["front_mask"] is not None:
        image_paste(res, (data["front_mask"].repeat(3, axis=-1) * Color.RED).astype(np.uint8), inplace=True)
    if data["back_mask"] is not None:
        image_paste(res, (data["back_mask"].repeat(3, axis=-1) * Color.GREEN).astype(np.uint8), inplace=True)

    if data["bbox"] is not None:
        data["bbox"] = data["bbox"][0:1]
        for bbox in data["bbox"]: # plot all bboxes
            x1, y1, x2, y2 = bbox
            image_draw_rectangle(res, (y1, x1), (y2, x2), color=Color.BLACK, thickness=BBOX_THICKNESS, inplace=True)

    return res

def get_args() -> Namespace:
    """cli args"""
    parser = ArgumentParser()
    parser.add_argument("video_path")
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
    # from auto_follow_logs_frame_reader import AutoFollowLogsFrameReader # for debug only
    # video_player = VideoPlayerEnv(VREVideo(AutoFollowLogsFrameReader(args.video_path)), loop=False)
    # BGR = True
    video_player = VideoPlayerEnv(VREVideo(args.video_path), loop=True)
    logger.info(f"{video_player}")

    supported_types = ["bbox", "rgb", "splitter_segmentation", "frame_ix", "front_mask",
                       "bbox_oriented", "segmentation_xy", "segmentation", "bbox_confidence", "back_mask"]
    data_channel = DataChannel(supported_types=supported_types, eq_fn=lambda a, b: a["frame_ix"] == b["frame_ix"])
    actions_queue = ActionsQueue(actions=VIDEO_SUPPORTED_ACTIONS)

    robot = Robot(env=video_player, data_channel=data_channel, actions_queue=actions_queue, action_fn=video_action_fn)
    yolo_data_producer = YOLODataProducer(weights_path=args.weights_path_yolo, threshold=args.yolo_threshold, bgr=BGR)
    mask_splitter_data_producer = MaskSplitterDataProducer(splitter_model_path=args.weights_path_mask_splitter_network,
                                                           mask_threshold=args.mask_splitter_network_mask_threshold,
                                                           bbox_threshold=args.mask_splitter_network_bbox_threshold)
    robot.add_data_producer(yolo_data_producer)
    robot.add_data_producer(mask_splitter_data_producer)

    key_to_action = {"space": "PLAY_PAUSE", "q": "DISCONNECT", "Right": "SKIP_AHEAD_ONE_SECOND",
                     "Left": "GO_BACK_ONE_SECOND"}
    screen_displayer = ScreenDisplayer(data_channel, actions_queue, resolution=DEFAULT_SCREEN_RESOLUTION,
                                       screen_frame_callback=screen_frame_callback, key_to_action=key_to_action)
    robot.add_controller(screen_displayer, name="Screen displayer")
    robot.add_other_thread(video_player, name="Video player")

    robot.run()
    video_player.stop_video()
    data_channel.close()

if __name__ == "__main__":
    main(get_args())
