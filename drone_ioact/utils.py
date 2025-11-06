"""generic utils file"""
from pathlib import Path
from datetime import datetime
from loggez import make_logger

def get_project_root() -> Path:
    """returns the project root"""
    return Path(__file__).parents[1]

logger = make_logger("DRONE", log_file=Path.cwd() / f"{get_project_root()}/logs/{datetime.now().isoformat()[0:-6]}.txt")
