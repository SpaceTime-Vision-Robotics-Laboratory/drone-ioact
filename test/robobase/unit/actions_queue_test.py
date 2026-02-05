import pytest
from queue import Queue
from robobase.actions2env import ActionsQueue

def test_ActionsQueue_ctor():
    with pytest.raises(AssertionError):
         ActionsQueue(Queue(), actions=[])

    aq = ActionsQueue(Queue(), actions=["a1", "a2"])
    assert aq.actions == ["a1", "a2"]
    assert len(aq) == 0

def test_ActionsQueue_push_pop():
    aq = ActionsQueue(Queue(), actions=["a1", "a2"])
    assert len(aq) == 0
    aq.put("a1")
    aq.put("a2")
    assert len(aq) == 2
    assert aq.get() == "a1"
    assert len(aq) == 1
    with pytest.raises(AssertionError):
        aq.put(0)
    with pytest.raises(AssertionError):
        aq.put("a3")
    assert aq.get() == "a2"
    assert len(aq) == 0
