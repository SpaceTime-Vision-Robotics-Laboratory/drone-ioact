"""video_actions.py - defines all the supported actions of an video player from our generic ones to the video's"""
from pathlib import Path
from robobase import Action
from roboimpl.utils import logger, image_write
from .video_player_env import VideoPlayerEnv

VIDEO_SUPPORTED_ACTIONS: set[str] = {
    "DISCONNECT", "PLAY_PAUSE", "SKIP_AHEAD_ONE_SECOND", "GO_BACK_ONE_SECOND", "TAKE_SCREENSHOT"
}

def video_action_fn(video_player: VideoPlayerEnv, action: Action, write_path: Path | None = None) -> bool:
    """the actions callback from generic actions to video-specific ones"""
    write_path = write_path or Path.cwd()
    if action == "DISCONNECT":
        video_player.close()
    if action == "PLAY_PAUSE":
        video_player.is_paused = not video_player.is_paused
    if action == "SKIP_AHEAD_ONE_SECOND":
        video_player.increment_frame(video_player.fps)
    if action == "GO_BACK_ONE_SECOND":
        video_player.increment_frame(-video_player.fps)
    if action == "TAKE_SCREENSHOT":
        image_write(video_player.get_state()["rgb"], pth := f"{write_path}/frame.png")
        logger.debug(f"Stored screenshot at '{pth}'")
    return True
