"""video_data_producer.py - defines the data producer impl that interacts with a video player to produce frames"""
from overrides import overrides
from robobase import DataProducer, DataItem
from .video_player import VideoPlayer

class VideoDataProducer(DataProducer):
    """VideoDataProducer implementation"""
    def __init__(self, video_player: VideoPlayer):
        DataProducer.__init__(self)
        self.video_player = video_player

    @overrides
    def produce(self, deps: dict[str, DataItem] | None = None) -> dict[str, DataItem]:
        return self.video_player.get_current_frame()
