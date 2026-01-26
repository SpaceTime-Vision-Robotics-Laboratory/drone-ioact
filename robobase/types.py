"""types.py - Generic types for robobase"""
from typing import Callable
import numpy as np

DataItem = np.ndarray | int | str | float # used for the DataChannel dictionary: {modality_name: dict[str, DataItem]}
Action = str # actions are stored as simple strings for simplicity :)
ControllerFn = Callable[[dict[str, DataItem]], Action | None] # takes a data, returns an action (or none for no action)
ActionFn = Callable[["Environment", Action], bool] # noqa # takes an action, calls the robot and returns a bool (ok/nok)
