import pytest
from robobase.data_channel import DataChannel
from robobase.types import DataItem

def test_DataChannel_ctor():
    with pytest.raises(AssertionError):
        _ = DataChannel(supported_types=[], eq_fn=lambda a, b: a==b)

    channel = DataChannel(supported_types=["rgb"], eq_fn=lambda a, b: a==b)
    assert channel.supported_types == {"rgb"}

def test_DataChannel_eq_fn():
    channel = DataChannel(supported_types=["rgb"], eq_fn=lambda a, b: a==b)
    d1 = DataItem({"rgb": 1})
    d2 = DataItem({"rgb": 2})
    d3 = DataItem({"rgb": 1})
    assert not channel.eq_fn(d1, d2)
    assert channel.eq_fn(d1, d3)
