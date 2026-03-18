"""init file"""
import logging
from roboimpl.utils import logger

try:
    from .yolo_data_producer import YOLODataProducer
    __all__ = ["YOLODataProducer"]
    logging.getLogger("ultralytics").setLevel(logging.CRITICAL)
except ImportError as e:
    logger.error(f"{e}\nPerhaps ultralytics not installed? Try 'pip install ultralytics'")
