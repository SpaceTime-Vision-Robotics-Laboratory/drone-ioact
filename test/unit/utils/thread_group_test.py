from drone_ioact.utils import ThreadGroup
import threading
import pytest
import time

def test_ThreadGroup_ctor():
    with pytest.raises(AssertionError, match="no threads provided"):
        _ = ThreadGroup({})

    with pytest.raises(AssertionError, match="Not all are threads"):
        _ = ThreadGroup({"a": "B"})

    tg = ThreadGroup({"a": threading.Thread(target=lambda: 0)})
    assert len(tg) == 1

def test_ThreadGroup_status():
    tg = ThreadGroup({"a": threading.Thread(target=lambda: 0)})
    assert tg.status() == [False]
    assert tg.is_any_dead() is True

def test_ThreadGroup_dict_overrides():
    tg = ThreadGroup({"a": (t := threading.Thread(target=lambda: 0))})
    assert tg.values() == [t]
    assert tg.items() == [("a", t)]

def test_ThreadGroup_start():
    """Check a basic thread doing some work (increment one value)"""
    x = 0
    def f():
        nonlocal x
        x += 1
        while True:
            time.sleep(1)

    tg = ThreadGroup({"a": threading.Thread(target=f, daemon=True)})
    assert x == 0
    tg.start()
    time.sleep(0.001)
    assert x == 1
