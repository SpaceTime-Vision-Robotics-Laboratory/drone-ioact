"""generic utils file"""
from pathlib import Path
from datetime import datetime
from enum import Enum
from loggez import make_logger

def get_project_root() -> Path:
    """returns the project root"""
    return Path(__file__).parent

logger = make_logger("DRONE", log_file=Path.cwd() / f"{get_project_root()}/logs/{datetime.now().isoformat()[0:-6]}.txt")

class Action(Enum):
    """Possible actions of a drone. Move to a "drone_out" class"""
    DISCONNECT = 0
    LIFT = 1
    LAND = 2
    FORWARD = 3
    ROTATE = 4
    FORWARD_NOWAIT = 5
    ROTATE_NOWAIT = 6
