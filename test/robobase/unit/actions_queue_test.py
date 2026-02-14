import pytest
from robobase.actions2env import ActionsQueue

def test_ActionsQueue_ctor():
    with pytest.raises(AssertionError):
         ActionsQueue(actions=[])

    aq = ActionsQueue(actions=["a1", "a2"])
    assert aq.actions == ["a1", "a2"]
    assert len(aq) == 0

def test_ActionsQueue_push_pop():
    aq = ActionsQueue(actions=["a1", "a2"])
    assert len(aq) == 0
    aq.put("a1", data_ts=None)
    aq.put("a2", data_ts=None)
    assert len(aq) == 2
    assert aq.get() == "a1"
    assert len(aq) == 1
    with pytest.raises(AssertionError):
        aq.put(0, data_ts=None)
    with pytest.raises(AssertionError):
        aq.put("a3", data_ts=None)
    assert aq.get() == "a2"
    assert len(aq) == 0
