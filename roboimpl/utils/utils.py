"""generic utils file"""
from pathlib import Path
from loggez import make_logger
from robobase.utils import logger as base_logger

log_file = None
if base_logger.get_file_handler() is not None:
    log_file = Path(base_logger.get_file_handler().file_path).parent / "ROBOIMPL.txt"

logger = make_logger("ROBOIMPL", log_file=log_file)
