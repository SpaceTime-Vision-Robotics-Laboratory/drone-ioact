"""action.py The generic action class"""
from __future__ import annotations
from typing import NamedTuple, Any

class Action(NamedTuple):
    """action class is a name (str) + parameters (any)"""
    name: str
    parameters: Any = None

    def __eq__(self, other: Action | str):
        assert isinstance(other, (Action, str)), type(other)
        other: Action = Action(other) if isinstance(other, str) else other
        return self.name == other.name and self.parameters == other.parameters
