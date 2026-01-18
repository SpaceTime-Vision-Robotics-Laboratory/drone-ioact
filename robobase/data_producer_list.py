"""data_producer_list.py - data structure to manage a list of data producers as a thread"""
import threading

from .utils import logger
from .types import DataItem
from .data_producer import DataProducer
from .data_channel import DataChannel, DataChannelClosedError

class DataProducerList(threading.Thread):
    """Interface defining the requirements of a drone (real, sym, mock) to produce data for a consumer"""
    def __init__(self, data_channel: DataChannel, data_producers: list[DataProducer]):
        threading.Thread.__init__(self, daemon=True)
        assert isinstance(data_channel, DataChannel), f"data_channel is of wrong type: {type(data_channel)}"
        assert (A := data_channel.supported_types) == set(B := sum([d.modalities for d in data_producers], [])), (A, B)
        assert len(B) == len(set(B)), f"One or more DataProducers provide the same modality! {B}"
        self._data_channel = data_channel
        self.data_producers = DataProducerList.topo_sort(data_producers)

    @staticmethod
    def topo_sort(producers: list[DataProducer]) -> list[DataProducer]:
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

    @property
    def data_channel(self) -> DataChannel:
        """The data queue where the data is inserted"""
        return self._data_channel

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
