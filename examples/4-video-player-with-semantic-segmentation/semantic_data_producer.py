"""semantic_data_producer.py produces both RGB and semantic segmentation using a PHG-MAE-Distil model"""
import numpy as np
from drone_ioact import DroneIn

from video_container import VideoContainer

class SemanticDataProducer(DroneIn):
    """VideoFrameReader gets data from a video container (producing frames in real time)"""
    def __init__(self, video: VideoContainer, model_path: str):
        self.video = video
        self.model_path = model_path

    def get_current_data(self, timeout_s: int = 10) -> dict[str, np.ndarray]:
        return {"rgb": self.video.get_current_frame()}

    def is_streaming(self) -> bool:
        return not self.video.is_done

    def stop_streaming(self):
        self.video.is_done = True
