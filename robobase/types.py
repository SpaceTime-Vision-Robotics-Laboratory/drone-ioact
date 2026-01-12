"""types.py - Generic types for robobase"""
from typing import Callable
import numpy as np

Action = str # actions are stored as simple strings for simplicity :)
ActionsCallback = Callable[["ActionsConsumer", Action], bool]
DataItem = dict[str, np.ndarray | int | str | float] # perception dictionary: {modality_name: modality_data}
