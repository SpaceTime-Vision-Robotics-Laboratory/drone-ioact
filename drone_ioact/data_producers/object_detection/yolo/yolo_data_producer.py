"""yolo_data_producer.py - produces bounding boxes using a yolo pre-trained checkpoint"""
from datetime import datetime
import numpy as np
import torch as tr
from overrides import overrides
from ultralytics import YOLO # pylint: disable=import-error
from ultralytics.engine.results import Masks # pylint: disable=import-error
from drone_ioact import DataProducer, DataItem
from drone_ioact.utils import log_debug_every_s

Bbox = tuple[int, int, int, int]
START = datetime.now()

class YOLODataProducer(DataProducer):
    """Yolo data producer - returns only a bounding box"""
    def __init__(self, rgb_data_producer: DataProducer, weights_path: str, bbox_threshold: float=0.75,
                 mask_threshold: float=0.5):
        super().__init__(rgb_data_producer.data_channel)
        self.rgb_data_producer = rgb_data_producer
        self.yolo = YOLO(weights_path)
        assert self.yolo.model.task == "segment", "yolo model doesn't support segmentation amd we only use these."
        self.bbox_threshold = bbox_threshold
        self.mask_threshold = mask_threshold

    def _compute_yolo(self, rgb: np.ndarray) -> tuple[list[Bbox], np.ndarray] | None:
        results = self.yolo.predict(rgb)
        boxes = results[0].boxes
        if not boxes or boxes.conf is None or len(boxes.conf) == 0:
            log_debug_every_s(START, "No bounding box was produced.")
            return None

        good_boxes: tr.Tensor = boxes.xyxy[boxes.conf > self.bbox_threshold]
        if len(good_boxes) == 0:
            log_debug_every_s(START, "No bounding box was produced.")
            return None

        good_segmentations: Masks = results[0].masks[boxes.conf > self.bbox_threshold]
        good_segmentations_np = (good_segmentations.data > self.mask_threshold).cpu().numpy()

        log_debug_every_s(START, f"Kept {len(good_boxes)}/{len(boxes)} bounding boxes after applying threshold.")
        return good_boxes.int().tolist(), good_segmentations_np

    @overrides
    def get_raw_data(self) -> DataItem:
        """note: the segmentations are not resized as we may not care about all of them. You resize them!"""
        raw_data = self.rgb_data_producer.get_raw_data()
        yolo_res = self._compute_yolo(raw_data["rgb"])
        bbox, segmentation = yolo_res if yolo_res is not None else (None, None)
        return {**raw_data, "bbox": bbox, "segmentation": segmentation}

    @overrides
    def is_streaming(self) -> bool:
        return self.rgb_data_producer.is_streaming()
