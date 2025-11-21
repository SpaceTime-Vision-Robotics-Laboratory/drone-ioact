"""init file"""

try:
    from .video_player import VideoPlayer
    from .video_data_producer import VideoDataProducer
    from .video_actions_consumer import VideoActionsConsumer
    from .video_actions import video_actions_callback, VIDEO_SUPPORTED_ACTIONS
    __all__ = ["VideoPlayer", "VideoDataProducer", "VideoActionsConsumer",
               "video_actions_callback", "VIDEO_SUPPORTED_ACTIONS"]
except ImportError as e:
    from drone_ioact.utils import logger
    logger.warning(f"video container could not be imported {e}. Did you run 'pip install -r requirements-drones.txt' ?")
