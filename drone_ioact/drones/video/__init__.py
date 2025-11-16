"""init file"""

try:
    from .video_container import VideoContainer
    __all__ = ["VideoContainer"]
except ImportError as e:
    from drone_ioact.utils import logger
    logger.warning(f"video container could not be imported {e}. Did you run 'pip install -r requirements-drones.txt' ?")
