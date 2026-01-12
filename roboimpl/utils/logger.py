"""logger.py - logger file and logger-specific methods"""
from pathlib import Path
from datetime import datetime
import os
from loggez import make_logger

from .utils import get_project_root

LAST_DEBUG: dict[str, float] = {} # used by log_debug_every_s
DEBUG_FREQ_S = float(os.getenv("DEBUG_FREQ_S", "2"))

logger = make_logger("ROBOIMPL",
                     log_file=Path.cwd() / f"{get_project_root()}/logs/{datetime.now().isoformat()[0:-6]}_ROBOIMPL.txt")

def log_debug_every_s(start: datetime, msg: str):
    """logs only once every DEBUG_FREQ_S with logger.debug to avoid spam"""
    global LAST_DEBUG # pylint: disable=global-statement, global-variable-not-assigned
    LAST_DEBUG[key] = LAST_DEBUG.get(key := str(start), 0) # pylint: disable=used-before-assignment
    if (now_s := (datetime.now() - start).total_seconds()) - LAST_DEBUG[key] >= DEBUG_FREQ_S:
        LAST_DEBUG[key] = now_s
        logger.debug(msg)
