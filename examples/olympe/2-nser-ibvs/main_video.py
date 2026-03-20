#!/usr/bin/env python3
"""
yolo + mask splitter example with frames stored during a olympe simulator run
Usage: VIDEO_FPS=15 ./main.py ../frames/ --weights_path_yolo 29_05_best__yolo11n-seg_sim_car_bunker__all.pt --weights_path_mask_splitter_network mask_splitter-sim-high-quality-partition-v10-dropout_0-augmentations_multi_scenes.pt # pylint:disable=line-too-long
"""
# pylint: disable=duplicate-code
from __future__ import annotations
from argparse import ArgumentParser, Namespace
from pathlib import Path
from vre_video import VREVideo
import numpy as np
from loggez import loggez_logger as logger

from detection.mask_splitter_data_producer import MaskSplitterDataProducer
from auto_follow_logs_frame_reader import AutoFollowLogsFrameReader

from robobase import Robot, DataChannel, ActionsQueue, DataItem, Action as A
from roboimpl.data_producers.yolo import YOLODataProducer
from roboimpl.envs.video import VideoPlayerEnv, video_action_fn, VIDEO_ACTION_NAMES
from roboimpl.controllers import ScreenDisplayer, Key
from roboimpl.utils import image_draw_rectangle, image_paste, image_draw_circle, Color

DEFAULT_SCREEN_RESOLUTION = 480, 640
BBOX_THICKNESS = 0.75
CIRCLE_RADIUS = 1.25

def screen_frame_callback(data: dict[str, DataItem]) -> np.ndarray:
    """produces RGB + semantic segmentation as a single frame"""
    res = data["rgb"].copy()

    # if data["segmentation"] is not None:
    #     all_segmentations = data["segmentation"].sum(0).repeat(3, axis=2) * Color.GREENISH
    #     image_paste(res, all_segmentations.astype(np.uint8), inplace=True)

    if data.get("bbox_oriented") is not None:
        p1, p2, p3, p4 = [p[::-1] for p in data["bbox_oriented"]]
        image_draw_circle(res, p1, radius=CIRCLE_RADIUS, color=Color.RED, fill=True, inplace=True)
        image_draw_circle(res, p2, radius=CIRCLE_RADIUS, color=Color.GREEN, fill=True, inplace=True)
        image_draw_circle(res, p3, radius=CIRCLE_RADIUS, color=Color.BLUE, fill=True, inplace=True)
        image_draw_circle(res, p4, radius=CIRCLE_RADIUS, color=Color.WHITE, fill=True, inplace=True)

    if data.get("front_mask") is not None:
        image_paste(res, (data["front_mask"].repeat(3, axis=2) * Color.RED).astype(np.uint8), inplace=True)

    if data.get("back_mask") is not None:
        image_paste(res, (data["back_mask"].repeat(3, axis=2) * Color.GREEN).astype(np.uint8), inplace=True)

    if data.get("bbox") is not None:
        data["bbox"] = data["bbox"][0:1]
        for bbox in data["bbox"]: # plot all bboxes
            x1, y1, x2, y2 = bbox
            image_draw_rectangle(res, (y1, x1), (y2, x2), color=Color.BLACK, thickness=BBOX_THICKNESS, inplace=True)

    return res

def get_args() -> Namespace:
    """cli args"""
    parser = ArgumentParser()
    parser.add_argument("video_path", type=Path)
    # yolo params
    parser.add_argument("--yolo_weights_path")
    parser.add_argument("--yolo_threshold", default=0.75, type=float)
    # spliter network params
    parser.add_argument("--mask_splitter_network_weights_path")
    parser.add_argument("--mask_splitter_network_mask_threshold", default=0.5, type=float)
    parser.add_argument("--mask_splitter_network_bbox_threshold", default=0.5, type=float)
    args = parser.parse_args()
    return args

def main(args: Namespace):
    """main fn"""
    # TODO: make sure that the returned RGB is exactly IMAGE_SIZE_SPLITTER_NET in size.
    if args.video_path.name == "res": # TODO: we should get rid of this once we are done comparing with the orig. code
        env = VideoPlayerEnv(VREVideo(AutoFollowLogsFrameReader(args.video_path)), loop=True)
        # TODO? env = NullEnv(); env.add_data_producer(ReplayDataProducer(output/res))
    else:
        env = VideoPlayerEnv(VREVideo(args.video_path), loop=True)
    bgr = isinstance(env.video.reader, AutoFollowLogsFrameReader)
    logger.info(f"{env}")

    dps = []
    supported_types = env.get_modalities()
    if args.yolo_weights_path is not None:
        dps.append(YOLODataProducer(args.yolo_weights_path, threshold=args.yolo_threshold, bgr=bgr))
        supported_types.extend(dps[-1].modalities)
    if args.mask_splitter_network_weights_path is not None:
        dps.append(MaskSplitterDataProducer(args.mask_splitter_network_weights_path,
                                            mask_threshold=args.mask_splitter_network_mask_threshold,
                                            bbox_threshold=args.mask_splitter_network_bbox_threshold))
        supported_types.extend(dps[-1].modalities)

    data_channel = DataChannel(supported_types=supported_types, eq_fn=lambda a, b: a["frame_ix"] == b["frame_ix"])
    actions_queue = ActionsQueue(action_names=VIDEO_ACTION_NAMES)

    robot = Robot(env=env, data_channel=data_channel, actions_queue=actions_queue, action_fn=video_action_fn)
    for dp in dps:
        robot.add_data_producer(dp)

    key_to_action = {Key.Space: A("PLAY_PAUSE"), Key.Esc: A("DISCONNECT"), Key.Left: A("GO_BACK", (env.fps, )),
                     Key.Right: A("GO_FORWARD", (env.fps, )), Key.Comma: A("GO_BACK", (1, )),
                     Key.Period: A("GO_FORWARD", (1, ))}
    screen_displayer = ScreenDisplayer(data_channel, actions_queue, resolution=DEFAULT_SCREEN_RESOLUTION,
                                       screen_frame_callback=screen_frame_callback, key_to_action=key_to_action)
    robot.add_controller(screen_displayer, name="Screen displayer")
    robot.add_other_thread(env, name="Video player")

    robot.run()
    env.close()
    data_channel.close()

if __name__ == "__main__":
    main(get_args())
