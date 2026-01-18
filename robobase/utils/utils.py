"""generic utils file"""
from pathlib import Path
from datetime import datetime
from typing import Any
from loggez import make_logger

def get_project_root() -> Path:
    """returns the project root"""
    return Path(__file__).parents[2]

logs_dir = get_project_root() / "logs"

logger = make_logger("ROBOBASE", log_file=f"{logs_dir}/{datetime.now().isoformat()[0:-7]}/ROBOBASE.txt")

def parsed_str_type(item: Any) -> str:
    """Given an object with a type of the format: <class 'A.B.C.D'>, parse it and return 'A.B.C.D'"""
    return str(type(item)).rsplit(".", maxsplit=1)[-1][0:-2]
