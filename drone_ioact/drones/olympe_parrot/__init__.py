"""init file"""
try:
    import olympe

    from .olympe_actions_consumer import OlympeActionsConsumer
    from .olympe_data_producer import OlympeDataProducer

    olympe.log.update_config({"loggers": {"olympe": {"level": "CRITICAL"}}})

    __all__ = ["OlympeDataProducer", "OlympeActionsConsumer"]
except ImportError as e:
    from drone_ioact.utils import logger
    logger.warning(f"olympe could not be imported {e}. Did you run 'pip install -r requirements-drones.txt' ?")
