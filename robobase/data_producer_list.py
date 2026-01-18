"""data_producer_list.py - data structure to manage a list of data producers as a thread"""
import threading

from .utils import logger
from .types import DataItem
from .data_producer import DataProducer
from .data_channel import DataChannel, DataChannelIsClosed

class DataProducerList(threading.Thread):
    """Interface defining the requirements of a drone (real, sym, mock) to produce data for a consumer"""
    def __init__(self, data_channel: DataChannel, data_producers: list[DataProducer]):
        threading.Thread.__init__(self, daemon=True)
        assert isinstance(data_channel, DataChannel), f"data_channel is of wrong type: {type(data_channel)}"
        self._data_channel = data_channel
        self.data_producers = data_producers

    @property
    def data_channel(self) -> DataChannel:
        """The data queue where the data is inserted"""
        return self._data_channel

    def run(self):
        while True:
            try:
                data: dict[str, DataItem] = {}
                for data_producer in self.data_producers: # TODO: topo-sort
                    data |= data_producer.produce(deps=data)
                self.data_channel.put(data)
            except DataChannelIsClosed: # in case it closes between is_open() check and put(data)
                break
            except Exception as e:
                logger.error(e)
                break
