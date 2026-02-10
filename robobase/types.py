"""types.py - Generic types for robobase"""
from typing import Callable
import numpy as np

DataItem = np.ndarray | int | str | float # used for the DataChannel dictionary: {modality_name: dict[str, DataItem]}
DataEqFn = Callable[[dict[str, DataItem], dict[str, DataItem]], bool] # eq_fn(data1, data2) -> true/false
ControllerFn = Callable[[dict[str, DataItem]], "Action | None"] # takes a data, returns an action (or none for no action) # noqa # pylint: disable=all
ActionFn = Callable[["Environment", "Action"], bool] # takes an action, calls the robot and returns a bool (ok/nok) # noqa # pylint: disable=all
