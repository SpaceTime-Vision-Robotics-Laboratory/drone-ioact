"""data_producer_list.py - data structure to manage a list of data producers as a thread"""
from typing import Callable
import threading

from .utils import logger
from .types import DataItem
from .data_producer import DataProducer
from .data_channel import DataChannel, DataChannelIsClosed

class DataProducerList(threading.Thread):
    """Interface defining the requirements of a drone (real, sym, mock) to produce data for a consumer"""
    def __init__(self, data_channel: DataChannel, data_producers: list[DataProducer],
                 producer_fn: Callable[[list[DataProducer]], dict[str, DataItem]] | None = None):
        threading.Thread.__init__(self, daemon=True)
        assert isinstance(data_channel, DataChannel), f"data_channel is of wrong type: {type(data_channel)}"
        self._data_channel = data_channel
        self.data_producers = data_producers
        self.producer_fn = producer_fn or DataProducerList._linear_producer_fn # TODO: generic topo-sort

    @property
    def data_channel(self) -> DataChannel:
        """The data queue where the data is inserted"""
        return self._data_channel

    def run(self):
        while True:
            try:
                data = self.producer_fn(self.data_producers)
                self.data_channel.put(data)
            except DataChannelIsClosed: # in case it closes between is_open() check and put(data)
                break
            except Exception as e:
                logger.error(e)
                break

    @staticmethod
    def _linear_producer_fn(data_producers: list[DataProducer]) -> dict[str, DataItem]:
        """Data producer function for this application. Topo-sorting is linear from first data producer to the last"""
        res = {}
        for data_producer in data_producers:
            res = {**res, **data_producer.produce(deps=res)}
        return res
