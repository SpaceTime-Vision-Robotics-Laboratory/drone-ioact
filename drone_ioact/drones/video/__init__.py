"""init file"""

try:
    from .video_frame_reader import VideoFrameReader
    __all__ = ["VideoFrameReader"]
except ImportError as e:
    from drone_ioact.utils import logger
    logger.warning(f"video container could not be imported {e}. Did you run 'pip install -r requirements-drones.txt' ?")
