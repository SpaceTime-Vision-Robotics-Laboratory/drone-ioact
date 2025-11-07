"""init file"""
import olympe

from .olympe_actions_maker import OlympeActionsMaker
from .olympe_frame_reader import OlympeFrameReader

olympe.log.update_config({"loggers": {"olympe": {"level": "CRITICAL"}}})

__all__ = ["OlympeActionsMaker", "OlympeFrameReader"]
