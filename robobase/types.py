"""types.py - Generic types for robobase"""
from typing import Callable
import numpy as np

DataItem = np.ndarray | int | str | float # used for the DataChannel dictionary: {modality_name: dict[str, DataItem]}
Action = str # actions are stored as simple strings for simplicity :)
PlannerFn = Callable[[dict[str, DataItem]], Action] # takes a data, returns an action
ActionFn = Callable[[Action], bool] # noqa # takes an action, calls the robot and returns bool if succeeded
TerminationFn = Callable[[], bool] # returns true if the robot died
