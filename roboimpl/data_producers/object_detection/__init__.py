"""init file"""

try:
    from .yolo.yolo_data_producer import YOLODataProducer
    __all__ = ["YOLODataProducer"]
except ImportError:
    from roboimpl.utils import logger
    logger.error("ultralytics is not installed")
