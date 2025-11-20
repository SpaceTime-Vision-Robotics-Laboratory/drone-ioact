"""generic utils file"""
import os
from pathlib import Path
from datetime import datetime
from loggez import make_logger

DEBUG_FREQ_S = float(os.getenv("DEBUG_FREQ_S", "2"))
LAST_DEBUG = 0

def get_project_root() -> Path:
    """returns the project root"""
    return Path(__file__).parents[2]

logger = make_logger("DRONE", log_file=Path.cwd() / f"{get_project_root()}/logs/{datetime.now().isoformat()[0:-6]}.txt")

def log_debug_every_s(start: datetime, msg: str):
    """logs only once every DEBUG_FREQ_S with logger.debug to avoid spam"""
    global LAST_DEBUG # pylint: disable=global-statement
    if (now_s := (datetime.now() - start).total_seconds()) - LAST_DEBUG >= DEBUG_FREQ_S:
        LAST_DEBUG = now_s
        logger.debug(msg)
