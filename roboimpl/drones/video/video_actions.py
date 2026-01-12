"""video_actions.py - defines all the supported actions of an video player from our generic ones to the video's"""
from robobase import Action
from roboimpl.utils import logger, image_write
from .video_actions_consumer import VideoActionsConsumer

VIDEO_SUPPORTED_ACTIONS: set[str] = {
    "DISCONNECT", "PLAY_PAUSE", "SKIP_AHEAD_ONE_SECOND", "GO_BACK_ONE_SECOND", "TAKE_SCREENSHOT"
}

def video_actions_callback(actions_maker: VideoActionsConsumer, action: Action) -> bool:
    """the actions callback from generic actions to video-specific ones"""
    video_player = actions_maker.video_player
    if action == "DISCONNECT":
        video_player.stop_video()
    if action == "PLAY_PAUSE":
        video_player.is_paused = not video_player.is_paused
    if action == "SKIP_AHEAD_ONE_SECOND":
        video_player.increment_frame(video_player.fps)
    if action == "GO_BACK_ONE_SECOND":
        video_player.increment_frame(-video_player.fps)
    if action == "TAKE_SCREENSHOT":
        image_write(video_player.get_current_frame()["rgb"], pth := f"{actions_maker.write_path}/frame.png")
        logger.debug(f"Stored screenshot at '{pth}'")
    return True
