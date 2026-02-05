#!/usr/bin/env python3
"""keyboard controller and display example with frames of a video + semantic segmentation"""
# pylint: disable=duplicate-code
from __future__ import annotations
from queue import Queue
from functools import partial
from argparse import ArgumentParser, Namespace
import logging
from vre_video import VREVideo
import numpy as np

from robobase import Robot, ActionsQueue, DataChannel, DataItem
from roboimpl.data_producers.semantic_segmentation import PHGMAESemanticDataProducer
from roboimpl.data_producers.object_detection import YOLODataProducer
from roboimpl.envs.video import VideoPlayerEnv, video_action_fn, VIDEO_SUPPORTED_ACTIONS
from roboimpl.controllers import ScreenDisplayer
from roboimpl.utils import semantic_map_to_image, image_draw_rectangle, image_paste, Color

logging.getLogger("ultralytics").setLevel(logging.CRITICAL)
QUEUE_MAX_SIZE = 30
BBOX_THICKNES = 1
DEFAULT_SCREEN_RESOLUTION = (600, 800)

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
        all_segmentations = (data["segmentation"].sum(0).repeat(3, axis=-1) * Color.GREENISH).astype(np.uint8)
        data["rgb"] = image_paste(data["rgb"], all_segmentations)

    res = data["rgb"]
    if "semantic" in data:
        sema_rgb = semantic_map_to_image(data["semantic"].argmax(-1), color_map)
        res = np.concatenate([data["rgb"], sema_rgb], axis=1)

    return res

def get_args() -> Namespace:
    """cli args"""
    parser = ArgumentParser()
    parser.add_argument("video_path")
    parser.add_argument("--frame_resolution", type=int, nargs=2, help="optional, only for video_path='-'")
    parser.add_argument("--fps", type=float, help="optional only for video_path='-'")
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
    reader_kwargs = {} if args.video_path != "-" else {"resolution": args.frame_resolution, "fps": args.fps}
    (video_player := VideoPlayerEnv(VREVideo(args.video_path, **reader_kwargs))).start() # start the video player

    supported_types = ["rgb", "frame_ix"]
    supported_types = supported_types if args.weights_path_phg is None else [*supported_types, "semantic"]
    if args.weights_path_yolo:
        supported_types.extend(["bbox", "bbox_confidence", "segmentation", "segmentation_xy"])
    data_channel = DataChannel(supported_types=supported_types, eq_fn=lambda a, b: a["frame_ix"] == b["frame_ix"])
    actions_queue = ActionsQueue(Queue(maxsize=QUEUE_MAX_SIZE), actions=VIDEO_SUPPORTED_ACTIONS)

    robot = Robot(env=video_player, data_channel=data_channel, actions_queue=actions_queue, action_fn=video_action_fn)
    if args.weights_path_phg is not None:
        robot.add_data_producer(PHGMAESemanticDataProducer(weights_path=args.weights_path_phg))
    if args.weights_path_yolo is not None:
        robot.add_data_producer(YOLODataProducer(weights_path=args.weights_path_yolo, threshold=args.yolo_threshold))

    f_screen_frame_callback = partial(screen_frame_callback, color_map=PHGMAESemanticDataProducer.COLOR_MAP,
                                      only_top1_bbox=args.yolo_only_top1_bbox)
    key_to_action = {"space": "PLAY_PAUSE", "q": "DISCONNECT", "Right": "SKIP_AHEAD_ONE_SECOND",
                     "Left": "GO_BACK_ONE_SECOND"}
    screen_displayer = ScreenDisplayer(data_channel, actions_queue, resolution=DEFAULT_SCREEN_RESOLUTION,
                                       screen_frame_callback=f_screen_frame_callback, key_to_action=key_to_action)
    robot.add_controller(screen_displayer, "Screen Displayer")

    robot.run()
    video_player.stop_video()
    data_channel.close()

if __name__ == "__main__":
    main(get_args())
