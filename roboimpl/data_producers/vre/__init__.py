"""init file"""
from roboimpl.utils import logger

try:
    from .vre_data_producers import build_vre_data_producers, VREDataProducer
    __all__ = ["build_vre_data_producers", "VREDataProducer"]
except ImportError as e:
    logger.error(f"{e}\nPerhaps vre not installed? Try 'pip install vre-representations-extractor'")
