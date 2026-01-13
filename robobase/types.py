"""types.py - Generic types for robobase"""
from typing import Callable
import numpy as np

Action = str # actions are stored as simple strings for simplicity :)
ActionsCallback = Callable[["ActionsConsumer", Action], bool] # noqa
DataItem = np.ndarray | int | str | float # used for the DataChannel dictionary: {modality_name: dict[str, DataItem]}
