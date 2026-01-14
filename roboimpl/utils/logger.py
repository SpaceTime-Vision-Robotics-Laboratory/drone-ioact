"""logger.py - logger file and logger-specific methods"""
from pathlib import Path
from loggez import make_logger as make_logger

from robobase.utils import logger as base_logger

logger = make_logger("ROBOIMPL", log_file=Path(base_logger.get_file_handler().file_path).parent / "ROBOIMPL.txt")
