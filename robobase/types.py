"""types.py - Generic types for robobase"""
from typing import Callable
import numpy as np

DataItem = np.ndarray | int | str | float # used for the DataChannel dictionary: {modality_name: dict[str, DataItem]}
Action = str # actions are stored as simple strings for simplicity :)
ActionFn = Callable[[Action], bool] # noqa
TerminationFn = Callable[[], bool]
