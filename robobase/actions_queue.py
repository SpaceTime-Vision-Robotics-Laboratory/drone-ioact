"""actions_queue.py - thread-safe queue composition with support for robobase generic actions"""
from queue import Queue

from robobase.types import Action

class ActionsQueue:
    """Interface defining the actions understandable by a drone and the application. Queue must be thread-safe!"""
    def __init__(self, queue: Queue, actions: list[Action]):
        assert len(actions) > 0, "cannot have an empty list of actions"
        super().__init__()
        self.queue = queue
        self.actions = actions

    def put(self, item: Action, *args, **kwargs):
        """Put an item into the queue"""
        assert isinstance(item, Action), type(item)
        assert item in (actions := self.actions), f"{item} not in {actions}"
        self.queue.put(item, *args, **kwargs)

    def get(self, *args, **kwargs) -> Action:
        """Remove and return an item from the queue"""
        return self.queue.get(*args, **kwargs)

    def __len__(self):
        return self.queue.qsize()

    def __repr__(self):
        return f"[ActionsQueue] Actions: {self.actions}. Size: {len(self)}"
