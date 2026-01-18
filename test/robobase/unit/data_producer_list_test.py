from robobase import DataProducerList, DataProducer, DataChannel
import pytest

def test_DataProducerList_wrong_data_key():
    class RGB(DataProducer):
        key: str = "rgb2"
        def produce(self, deps = None):
            return {RGB.key: 0}

    rgb = RGB(modalities=["rgb"])
    dp_list = DataProducerList(DataChannel(supported_types=["rgb"], eq_fn=lambda: True), data_producers=[rgb])
    with pytest.raises(KeyError):
        dp_list.produce_all()
    RGB.key = "rgb"
    res = dp_list.produce_all()
    assert res.keys() == {"rgb"}


def test_DataProducerList_wrong_data_channel_supported_types():
    class FakeDP(DataProducer):
        def produce(self, deps = None):
            return {}

    rgb, hsv = FakeDP(modalities=["rgb"]), FakeDP(modalities=["hsv"])
    with pytest.raises(AssertionError):
        _ = DataProducerList(DataChannel(supported_types=["rgb"], eq_fn=lambda: True), data_producers=[rgb, hsv])

    _ = DataProducerList(DataChannel(supported_types=["rgb", "hsv"], eq_fn=lambda: True), data_producers=[rgb, hsv])
