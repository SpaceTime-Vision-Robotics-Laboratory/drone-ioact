"""generic utils file"""
from pathlib import Path
import os
from datetime import datetime
from typing import Any
from loggez import make_logger

def get_project_root() -> Path:
    """returns the project root"""
    return Path(__file__).parents[2]

# Create a logger. For the lgos dir we have a few options: ROBOBASE_STORE_LOGS must be >=1 otherwise no logs.
# For the file, if the env. var ROBOBASE_LOGS_DIR is set, then it's used, otherwise defaults to proj_root/logs/now_iso
logs_dir = os.getenv("ROBOBASE_LOGS_DIR", get_project_root() / "logs" / datetime.now().isoformat()[0:-7])
log_file = f"{logs_dir}/ROBOBASE.txt" if os.getenv("ROBOBASE_STORE_LOGS", "0") in ("1", "2") else None
logger = make_logger("ROBOBASE", log_file=log_file)

def parsed_str_type(item: Any) -> str:
    """Given an object with a type of the format: <class 'A.B.C.D'>, parse it and return 'A.B.C.D'"""
    return str(type(item)).rsplit(".", maxsplit=1)[-1][0:-2]
