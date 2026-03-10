"""init file"""

try:
    import olympe
    import os

    from .olympe_env import OlympeEnv
    from .olympe_actions import olympe_actions_fn, OLYMPE_SUPPORTED_ACTIONS

    if (val := os.getenv("OLYMPE_LOG_LEVEL", "")) != "":
        olympe.log.update_config({"loggers": {"olympe": {"level": val}}})
    else:
        olympe.log.update_config({"loggers": {"olympe": {"level": "CRITICAL"}}})

    __all__ = ["OlympeEnv", "olympe_actions_fn", "OLYMPE_SUPPORTED_ACTIONS",]
except ImportError as e:
    from roboimpl.utils import logger
    logger.warning(f"olympe could not be imported {e}. Did you run 'pip install -r requirements-extra.txt' ?")
