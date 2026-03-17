"""circular_buffer.py - Basic circular buffer with fixed capacity based on numpy arrays"""
from typing import Any
import numpy as np

class CircularBuffer:
    """Basic circular buffer with fixed capacity based on numpy arrays"""
    def __init__(self, capacity: int, initial_values: list | None = None):
        super().__init__()
        initial_values = initial_values or []
        assert isinstance(capacity, int) and capacity > 0, "Capacity error: not a positive integer"
        assert len(initial_values) <= capacity, f"Capacity error: initial_values={len(initial_values)} > {capacity=}"
        self.capacity = capacity
        self.data = np.empty(capacity, dtype=object)
        self.data[0:len(initial_values)] = initial_values
        self._current_ix = len(initial_values)
        self._full = False

    def add(self, item: Any):
        """adds one item to the buffer"""
        self.data[self._current_ix % len(self.data)] = item
        if self._current_ix == len(self.data) - 1:
            self._full = True
        self._current_ix = (self._current_ix + 1) % len(self.data)

    def get(self) -> np.ndarray:
        """gets the data in the buffer in proper order"""
        first_part = self.data[0: self._current_ix]
        return first_part if self._full is False else np.concatenate([self.data[self._current_ix: ], first_part])

    def clear(self):
        """clears the buffer"""
        self._current_ix = 0
        self._full = False

    def __len__(self):
        return len(self.data) if self._full else self._current_ix
