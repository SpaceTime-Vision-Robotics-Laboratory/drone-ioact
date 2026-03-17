import pytest
from roboimpl.utils import CircularBuffer

def test_CircularBuffer_ctor():
    buffer = CircularBuffer(capacity=100)
    assert buffer.capacity == 100 and len(buffer) == 0

    with pytest.raises(AssertionError, match="Capacity error: not a positive integer"):
        CircularBuffer(capacity=-100)
    with pytest.raises(AssertionError, match="Capacity error: not a positive integer"):
        CircularBuffer(capacity="asdf")

    buffer = CircularBuffer(capacity=100, initial_values=[1, 2, 3])
    assert buffer.capacity == 100 and len(buffer) == 3

    with pytest.raises(AssertionError, match="Capacity error"):
        CircularBuffer(capacity=2, initial_values=[1, 2, 3])

def test_CircularBuffer_add_get_1():
    buffer = CircularBuffer(capacity=100)
    for i in range(10):
        buffer.add(i)
    assert len(buffer) == 10 and buffer.get().tolist() == list(range(10))

def test_CircularBuffer_add_get_2():
    buffer = CircularBuffer(capacity=7)
    for i in range(10):
        buffer.add(i)
    assert len(buffer) == 7 and buffer.get().tolist() == list(range(3, 10))
    assert buffer.data.tolist() == [7, 8, 9, 3, 4, 5, 6]

def test_CircularBuffer_clear():
    buffer = CircularBuffer(capacity=5)
    for i in range(10):
        buffer.add(i)
        if i == 7:
            buffer.clear()
    assert len(buffer) == 2 and buffer.get().tolist() == [8, 9]
    assert buffer.data.tolist() == [8, 9, 7, 3, 4]

