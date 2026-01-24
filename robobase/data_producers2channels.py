"""data_producers2channels.py implements the mapping between a list of producers and a list of channels"""
import threading
import time

from .utils import ThreadGroup, logger
from .types import DataItem
from .data_producer import DataProducer
from .data_channel import DataChannel, DataChannelClosedError

def _topo_sort_producers(producers: list[DataProducer]) -> list[DataProducer]:
    """does a topological sort of the data producers given their dependencies and their modalities"""
    consumers: dict[str, list[int]] = {} # Map dependency string -> list of consumer indices
    degrees: list[int] = [len(p.dependencies) for p in producers]

    for i, p in enumerate(producers):
        for dep in p.dependencies:
            consumers.setdefault(dep, []).append(i)

    queue: list[int] = [i for i, d in enumerate(degrees) if d == 0]
    res: list[DataProducer] = []

    while len(queue) > 0:
        curr_idx = queue.pop()
        res.append(producers[curr_idx])
        for mod in producers[curr_idx].modalities:
            for c_idx in consumers.get(mod, []):
                degrees[c_idx] -= 1
                if degrees[c_idx] == 0:
                    queue.append(c_idx)

    if len(res) != len(producers):
        raise ValueError("couldn't solve")
    return res


# Note: reimplementation here as we want to merge the two implementations.
class _DataProducerList(threading.Thread):
    """Interface defining the requirements of a drone (real, sym, mock) to produce data for a consumer"""
    def __init__(self, data_channel: DataChannel, data_producers: list[DataProducer]):
        threading.Thread.__init__(self, daemon=True)
        assert isinstance(data_channel, DataChannel), f"data_channel is of wrong type: {type(data_channel)}"
        assert (A := data_channel.supported_types) == set(B := sum([d.modalities for d in data_producers], [])), (A, B)
        assert len(B) == len(set(B)), f"One or more DataProducers provide the same modality! {B}"
        self.data_channel = data_channel
        self.data_producers = data_producers

    def produce_all(self) -> dict[str, DataItem]:
        """Calls all the producers in topological order and synchronous"""
        data: dict[str, DataItem] = {}
        for data_producer in self.data_producers:
            producer_data = data_producer.produce(deps=data)
            if (A := set(producer_data.keys())) != set(B := data_producer.modalities):
                raise KeyError(f"Producer {data_producer} with modalities {B} produced {A}.")
            data |= producer_data
        return data

    def run(self):
        while True:
            try:
                data = self.produce_all()
                self.data_channel.put(data)
            except DataChannelClosedError: # in case it closes between is_open() check and put(data)
                break
            except Exception as e:
                logger.error(e)
                break

class DataProducers2Channels(threading.Thread):
    """
    DataProducers2Channels is a generalization of DataProducerList from 1 channel : M producers to N : M.
    The end-goal is to have a async-based where we actually have one thread per DataProducer. Right now this is just
    a generalization of the (sync) DataProducerList, so each underlying may do the same work multiple times.
    """
    def __init__(self, data_producers: list[DataProducer], data_channels: list[DataChannel]):
        super().__init__(daemon=True)
        self.data_channels = data_channels
        self.data_producers = _topo_sort_producers(data_producers)

        dp_lists = {}
        for i, data_channel in enumerate(data_channels):
            channel_dps = []
            for dp in data_producers:
                if any(dp_mod in data_channel.supported_types for dp_mod in dp.modalities):
                    channel_dps.append(dp)
            dp_lists[str(i)] = _DataProducerList(data_channel=data_channel, data_producers=channel_dps)

        self.dp_lists_tg = ThreadGroup(dp_lists)

    def run(self):
        self.dp_lists_tg.start()
        while not self.dp_lists_tg.is_any_dead():
            time.sleep(1)

    def close(self):
        self._close_all_channels()

    def _close_all_channels(self):
        for ch in self.data_channels:
            try:
                ch.close()
            except Exception:
                pass
