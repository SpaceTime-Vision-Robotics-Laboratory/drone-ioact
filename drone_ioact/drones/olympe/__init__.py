"""init file"""
try:
    import olympe

    from .olympe_actions_maker import OlympeActionsMaker
    from .olympe_frame_reader import OlympeFrameReader

    olympe.log.update_config({"loggers": {"olympe": {"level": "CRITICAL"}}})

    __all__ = ["OlympeActionsMaker", "OlympeFrameReader"]
except ImportError as e:
    from drone_ioact.utils import logger
    logger.warning(f"olympe could not be imported {e}. Did you run 'pip install -r requirements-drones.txt' ?")
