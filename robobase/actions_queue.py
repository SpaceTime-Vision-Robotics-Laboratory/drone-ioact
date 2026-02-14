"""actions_queue.py - thread-safe queue composition with support for robobase generic actions"""
from queue import Queue
from datetime import datetime

from .action import Action
from .utils import DataStorer

class ActionsQueue:
    """Interface defining the actions understandable by a drone and the application. Queue must be thread-safe!"""
    def __init__(self, actions: list[Action | str], queue: Queue | None = None):
        assert len(actions) > 0, "cannot have an empty list of actions"
        assert all(isinstance(action, (Action, str)) for action in actions), actions
        self.actions: list[Action] = [act if isinstance(act, Action) else Action(name=act) for act in actions]
        self.queue = queue or Queue()
        self._action_names = set(a.name for a in self.actions)

    def put(self, action: Action | str, data_ts: datetime | None, *args, **kwargs):
        """Put an action into the queue. data_ts is the ts of the data that produced the action or None (i.e. kb)"""
        item_ts = datetime.now()
        assert isinstance(action, (Action, str)), type(action)
        action = Action(action) if isinstance(action, str) else action
        assert action.name in self._action_names, f"{action} not in {self._action_names}"
        if (storer := DataStorer.get_instance()) is not None:
            storer.push(item={"action": action, "data_ts": None if data_ts is None else data_ts.isoformat()},
                        tag="ActionsQueue", timestamp=item_ts)
        self.queue.put(action, *args, **kwargs)

    def get(self, *args, **kwargs) -> Action:
        """Remove and return an item from the queue"""
        return self.queue.get(*args, **kwargs)

    def __len__(self):
        return self.queue.qsize()

    def __repr__(self):
        return f"[ActionsQueue] Actions: {self.actions}. Size: {len(self)}"
