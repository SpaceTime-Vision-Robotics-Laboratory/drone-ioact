"""generic actions of any drone"""
from enum import Enum

class Action(Enum):
    """Possible actions of a drone. Move to a "drone_out" class"""
    DISCONNECT = 0
    LIFT = 1
    LAND = 2
    FORWARD = 3
    ROTATE = 4
    FORWARD_NOWAIT = 5
    ROTATE_NOWAIT = 6
