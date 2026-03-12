"""init file"""

try:
    from .video_player_env import VideoPlayerEnv
    from .video_actions import video_action_fn, VIDEO_ACTION_NAMES
    __all__ = ["VideoPlayerEnv",
               "video_action_fn", "VIDEO_ACTION_NAMES"]
except ImportError as e:
    from roboimpl.utils import logger
    logger.warning(f"video container could not be imported {e}. Did you run 'pip install -r requirements-extra.txt' ?")
