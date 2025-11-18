"""video_data_producer.py - defines the data producer impl that interacts with a video player to produce frames"""
from overrides import overrides
from drone_ioact import DataProducer, DataChannel, DataItem
from .video_player import VideoPlayer

class VideoDataProducer(DataProducer):
    """VideoDataProducer implementation"""
    def __init__(self, video_player: VideoPlayer, data_channel: DataChannel):
        DataProducer.__init__(self, data_channel)
        self.video_player = video_player

    @overrides
    def get_raw_data(self) -> DataItem:
        return self.video_player.get_current_frame()

    @overrides
    def is_streaming(self) -> bool:
        return not self.video_player.is_done
