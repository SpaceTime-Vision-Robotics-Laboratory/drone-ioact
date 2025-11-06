"""init file"""
import olympe
olympe.log.update_config({"loggers": {"olympe": {"level": "CRITICAL"}}})

from .olympe_actions_maker import OlympeActionsMaker
from .olympe_frame_reader import OlympeFrameReader
