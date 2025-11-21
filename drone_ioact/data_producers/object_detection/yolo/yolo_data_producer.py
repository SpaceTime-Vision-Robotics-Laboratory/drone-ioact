"""yolo_data_producer.py - produces bounding boxes using a yolo pre-trained checkpoint"""
from datetime import datetime
import numpy as np
import torch as tr
from overrides import overrides
from ultralytics import YOLO # pylint: disable=import-error
from drone_ioact import DataProducer, DataItem
from drone_ioact.utils import log_debug_every_s

Bbox = tuple[int, int, int, int]
START = datetime.now()

class YOLODataProducer(DataProducer):
    """Yolo data producer - returns only a bounding box"""
    def __init__(self, rgb_data_producer: DataProducer, weights_path: str, confidence_threshold: float=0.75):
        super().__init__(rgb_data_producer.data_channel)
        self.rgb_data_producer = rgb_data_producer
        self.yolo = YOLO(weights_path)
        self.confidence_threshold = confidence_threshold

    def _compute_yolo(self, image: np.ndarray) -> list[Bbox] | None:
        results = self.yolo.predict(image)
        boxes = results[0].boxes
        if not boxes or boxes.conf is None or len(boxes.conf) == 0:
            log_debug_every_s(START, "No bounding box was produced.")
            return None

        good_boxes: list[tr.Tensor] = boxes.xyxy[boxes.conf >= self.confidence_threshold]
        if len(good_boxes) == 0:
            log_debug_every_s(START, "No bounding box was produced.")
            return None

        log_debug_every_s(START, f"Kept {len(good_boxes)}/{len(boxes)} bounding boxes after applying threshold.")
        return good_boxes.int().tolist()

    @overrides
    def get_raw_data(self) -> DataItem:
        raw_data = self.rgb_data_producer.get_raw_data()
        bbox = self._compute_yolo(raw_data["rgb"])
        return {**raw_data, "bbox": bbox}

    @overrides
    def is_streaming(self) -> bool:
        return self.rgb_data_producer.is_streaming()
