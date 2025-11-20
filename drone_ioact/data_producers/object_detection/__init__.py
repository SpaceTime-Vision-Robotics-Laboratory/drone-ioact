"""init file"""

__all__ = []

try:
    from .yolo.yolo_data_producer import YOLODataProducer
    __all__ = [*__all__, "YOLODataProducer"]
except ImportError:
    from drone_ioact.utils import logger
    logger.error("ultralytics is not installed")
