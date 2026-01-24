from robobase import DataProducer, DataChannel
from robobase.data_producers2channels import _DataProducerList as DataProducerList
import pytest

class FakeDP(DataProducer):
    def produce(self, deps = None):
        return {}

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
    rgb, hsv = FakeDP(modalities=["rgb"]), FakeDP(modalities=["hsv"])
    with pytest.raises(AssertionError):
        _ = DataProducerList(DataChannel(supported_types=["rgb"], eq_fn=lambda: True), data_producers=[rgb, hsv])

    _ = DataProducerList(DataChannel(supported_types=["rgb", "hsv"], eq_fn=lambda: True), data_producers=[rgb, hsv])

def test_DataProducerList_same_modality_in_different_DataProducer():
    rgb, hsv = FakeDP(modalities=["rgb"]), FakeDP(modalities=["hsv", "rgb"])
    with pytest.raises(AssertionError) as exc:
        _ = DataProducerList(DataChannel(supported_types=["rgb", "hsv"], eq_fn=lambda: True), data_producers=[rgb, hsv])
    assert str(exc.value).startswith("One or more DataProducers provide the same modality!")

def test_DataProducerList_toposort_good():
    rgb = FakeDP(["rgb"], [])
    hsv = FakeDP(["hsv"], ["rgb"])
    edges = FakeDP(["edges", "canny"], ["rgb", "hsv"])

    ts_dp = DataProducerList.topo_sort([edges, rgb, hsv])
    assert ts_dp == [rgb, hsv, edges]

def test_DataProducerList_toposort_bad():
    rgb = FakeDP(["rgb"], ["edges"])
    hsv = FakeDP(["hsv"], ["rgb"])
    bad = FakeDP(["edges"], ["hsv"])

    with pytest.raises(ValueError) as exc:
        DataProducerList.topo_sort([bad, rgb, hsv])
    assert str(exc.value).startswith("couldn't solve")
