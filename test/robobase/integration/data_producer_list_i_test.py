import numpy as np
import time
from robobase import DataChannel, DataProducer, DataProducerList

def test_i_data_producer_list_basic():
    class RGB(DataProducer):
        i = 0
        def produce(self, deps = None):
            time.sleep(0.1)
            RGB.i += 1
            return {"rgb": np.zeros((10, 10)) + RGB.i}

    class RGBReverse(DataProducer):
        def produce(self, deps = None):
            return {"rgb_rev": deps["rgb"][::-1]}

    channel = DataChannel(supported_types=["rgb", "rgb_rev"], eq_fn=lambda a, b: np.allclose(a["rgb"], b["rgb"]))
    data_producers = [RGB(modalities=["rgb"]), RGBReverse(modalities=["rgb_rev"])]
    dp_list = DataProducerList(channel, data_producers) # topo-sort calling of produce() is done automatically

    assert channel._data is not None
    dp_list.start()

    time.sleep(1)
    channel.close()

    assert channel._data is not None
    assert (channel._data["rgb"] != 0).all() # unclear where the iteration will stop but we expect at least 2 iterations

if __name__ == "__main__":
    test_i_data_producer_list_basic()
