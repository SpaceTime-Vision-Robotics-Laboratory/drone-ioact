"""data_producer.py - interface for DataProducer which are used to produce data to be stored in a DataChannel"""
from __future__ import annotations
from abc import ABC, abstractmethod

from robobase.types import DataItem
from robobase.utils import parsed_str_type

class DataProducer(ABC):
    """DataProducer - interface for a single data producer. It has a produce() method and a list of dependencies"""
    def __init__(self, modalities: list[str], dependencies: list[str] | None = None):
        assert isinstance(modalities, list) and len(modalities) > 0, type(modalities)
        assert dependencies is None or isinstance(dependencies, list), type(dependencies)
        self._dependencies = dependencies or []
        self._modalities = modalities

    @abstractmethod
    def produce(self, deps: dict[str, DataItem] | None = None) -> dict[str, DataItem]:
        """produces the data at the current time given the dependencies, if any"""

    @property
    def modalities(self) -> list[str]:
        """The list of modalities of this data producer"""
        return self._modalities

    @property
    def dependencies(self) -> list[str]:
        """The list of dependencies for this data producer"""
        return self._dependencies

    def __repr__(self):
        return f"[{parsed_str_type(self)}] Modalities: {self.modalities}. Deps: {self.dependencies}"
