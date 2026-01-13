"""data_producer.py - interface for DataProducer which are used to produce data to be stored in a DataChannel"""
from __future__ import annotations
from abc import ABC, abstractmethod

from robobase.types import DataItem

class DataProducer(ABC):
    """DataProducer - interface for a single data producer. It has a produce() method and a list of dependencies"""
    def __init__(self, dependencies: list[str] | None = None):
        self._dependencies = dependencies or []

    @abstractmethod
    def produce(self, deps: dict[str, DataItem] | None = None) -> dict[str, DataItem]:
        """produces the data at the current time given the dependencies, if any"""

    @property
    def dependencies(self) -> list[str]:
        """The list of dependencies for this data producer"""
        return self._dependencies
