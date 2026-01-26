"""init file"""

try:
    from .video_player_env import VideoPlayerEnv
    from .video_actions import video_actions_fn, VIDEO_SUPPORTED_ACTIONS
    __all__ = ["VideoPlayerEnv",
               "video_actions_fn", "VIDEO_SUPPORTED_ACTIONS"]
except ImportError as e:
    from roboimpl.utils import logger
    logger.warning(f"video container could not be imported {e}. Did you run 'pip install -r requirements-drones.txt' ?")
