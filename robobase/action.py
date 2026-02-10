"""action.py The generic action class"""
from __future__ import annotations
from typing import NamedTuple, Any

class Action(NamedTuple):
    """action class is a name (str) + parameters (any)"""
    name: str
    parameters: tuple[Any, ...] = ()

    def __eq__(self, other: Action | str):
        assert isinstance(other, (Action, str)), type(other)
        return self.name == (Action(other) if isinstance(other, str) else other).name

    def __repr__(self):
        return f"Action({self.name}{'' if self.parameters == tuple() else f' {self.parameters}'})"
