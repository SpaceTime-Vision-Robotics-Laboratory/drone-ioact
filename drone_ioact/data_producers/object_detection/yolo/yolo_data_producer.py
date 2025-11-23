"""yolo_data_producer.py - produces bounding boxes using a yolo pre-trained checkpoint"""
import logging
from datetime import datetime
import numpy as np
from overrides import overrides
from ultralytics import YOLO # pylint: disable=import-error
from ultralytics.engine.results import Masks, Boxes # pylint: disable=import-error
from drone_ioact import DataProducer, DataItem
from drone_ioact.utils import log_debug_every_s

logging.getLogger("ultralytics").setLevel(logging.CRITICAL)

Bbox = tuple[int, int, int, int]
Segmentation = np.ndarray
START = datetime.now()

class YOLODataProducer(DataProducer):
    """Yolo data producer - returns only a bounding box"""
    def __init__(self, rgb_data_producer: DataProducer, weights_path: str, threshold: float):
        super().__init__(rgb_data_producer.data_channel)
        self.rgb_data_producer = rgb_data_producer
        self.yolo = YOLO(weights_path)
        self.threshold = threshold

    def _compute_yolo(self, rgb: np.ndarray) \
            -> tuple[list[Bbox], list[float], list[Segmentation] | None, list[np.ndarray] | None] | None:
        """returns 4 lists: bounding boxes (over thr), confidences of bboxes, segmentation masks and segmentations xy"""
        results = self.yolo.predict(rgb)[0]
        boxes = good_boxes = results.boxes
        masks = good_masks = results.masks

        if no_bbox := (boxes is None or boxes.conf is None or len(boxes.conf) == 0 or len(good_boxes) == 0):
            log_debug_every_s(START, f"No bounding box was produced or none above threshold {self.threshold}")
        else:
            good_boxes: Boxes = boxes[boxes.conf > self.threshold]
            log_debug_every_s(START, f"Kept {len(good_boxes)}/{len(boxes)} bounding boxes after applying threshold.")
            no_bbox = no_bbox and (len(good_boxes) == 0)

        if no_segm := (masks is None or len(masks.data) == 0):
            log_debug_every_s(START, "No segmentation masks were produced.")
        else:
            good_masks: Masks = masks[boxes.conf > self.threshold] if boxes.conf is not None else masks
            no_segm = no_segm and (len(good_masks) == 0)

        bbox = good_boxes.xyxy.int().tolist() if not no_bbox else None
        bbox_confidennce = good_boxes.conf.tolist() if not no_bbox else None
        segmentation = good_masks.data.cpu().numpy() if not no_segm else None
        segmentation_xy = good_masks.xy if not no_segm else None
        return bbox, bbox_confidennce, segmentation, segmentation_xy

    @overrides
    def get_raw_data(self) -> DataItem:
        """note: the segmentations are not resized as we may not care about all of them. You resize them!"""
        raw_data = self.rgb_data_producer.get_raw_data()
        yolo_res = self._compute_yolo(raw_data["rgb"])
        bbox, bbox_confidence, segmentation, segmentation_xy = yolo_res if yolo_res is not None else [None] * 4
        return {**raw_data, "bbox": bbox, "bbox_confidence": bbox_confidence,
                "segmentation": segmentation, "segmentation_xy": segmentation_xy}

    @overrides
    def is_streaming(self) -> bool:
        return self.rgb_data_producer.is_streaming()
