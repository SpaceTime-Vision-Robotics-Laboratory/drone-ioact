"""yolo_data_producer.py - produces bounding boxes using a yolo pre-trained checkpoint"""
import numpy as np
from ultralytics import YOLO # pylint: disable=import-error
from drone_ioact import DataProducer, DataItem

CONFIFENCE_THRESHOLD = 0.75

class YOLODataProducer(DataProducer):
    """Yolo data producer - returns only a bounding box"""
    def __init__(self, rgb_data_producer: DataProducer, weights_path: str):
        super().__init__(rgb_data_producer.data_channel)
        self.rgb_data_producer = rgb_data_producer
        self.yolo = YOLO(weights_path)

    def _compute_yolo(self, image: np.ndarray) -> tuple[int, int, int, int] | None:

        results = self.yolo.predict(image)
        boxes = results[0].boxes
        if not (boxes and boxes.conf is not None and len(boxes.conf) > 0 and boxes.conf.max() >= CONFIFENCE_THRESHOLD):
            return None

        best_conf_index = boxes.conf.argmax()
        coords = boxes.xyxy[best_conf_index].int().tolist()
        return coords

    def get_raw_data(self) -> DataItem:
        raw_data = self.rgb_data_producer.get_raw_data()
        bbox = self._compute_yolo(raw_data["rgb"])
        return {**raw_data, "bbox": bbox}

    def is_streaming(self) -> bool:
        return self.rgb_data_producer.is_streaming()
