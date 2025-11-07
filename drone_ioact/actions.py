"""generic actions of any drone"""
from __future__ import annotations
from enum import Enum

class Action(Enum):
    """Various generic actions of any drone. Custom actions should be built on top of this in the main code"""
    DISCONNECT = 0
    LIFT = 1
    LAND = 2
    FORWARD = 3
    ROTATE = 4
    FORWARD_NOWAIT = 5
    ROTATE_NOWAIT = 6

    def __lt__(self, other: Action) -> bool:
        """For ties in standard priority queue..."""
        return self.value < other.value
