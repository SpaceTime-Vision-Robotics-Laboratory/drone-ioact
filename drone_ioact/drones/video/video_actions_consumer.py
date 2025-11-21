"""video_actions_consumer.py - defines the actions consumer interacting with a video player"""
from pathlib import Path
from drone_ioact import ActionsConsumer, ActionsQueue, ActionsCallback
from .video_player import VideoPlayer

class VideoActionsConsumer(ActionsConsumer):
    """VideoActionsConsumer defines the actions taken on the video container based on the actions produced"""
    def __init__(self, video_player: VideoPlayer, actions_queue: ActionsQueue, actions_callback: ActionsCallback,
                 write_path: Path | None = None):
        super().__init__(actions_queue, actions_callback)
        self.video_player = video_player
        self.write_path = write_path or Path.cwd()

    def is_streaming(self):
        return not self.video_player.is_done
