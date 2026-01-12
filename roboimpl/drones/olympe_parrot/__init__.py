"""init file"""
try:
    import olympe

    from .olympe_actions_consumer import OlympeActionsConsumer
    from .olympe_data_producer import OlympeDataProducer
    from .olympe_actions import olympe_actions_callback, OLYMPE_SUPPORTED_ACTIONS

    olympe.log.update_config({"loggers": {"olympe": {"level": "CRITICAL"}}})

    __all__ = ["OlympeDataProducer", "OlympeActionsConsumer", "olympe_actions_callback", "OLYMPE_SUPPORTED_ACTIONS",]
except ImportError as e:
    from roboimpl.utils import logger
    logger.warning(f"olympe could not be imported {e}. Did you run 'pip install -r requirements-drones.txt' ?")
