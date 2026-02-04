"""action2robot.py - the module that interfaces bewteen the action and the robot/drone"""
from __future__ import annotations
import threading
import traceback
from queue import Empty

from .types import Action, ActionFn
from .utils import logger
from .actions_queue import ActionsQueue
from .environment import Environment

class Actions2Robot(threading.Thread):
    """Interface defining the requirements of a robot (real, sym, mock) to receive an action & apply it to the robot"""
    def __init__(self, env: Environment, actions_queue: ActionsQueue, action_fn: ActionFn):
        threading.Thread.__init__(self, daemon=True)
        assert isinstance(actions_queue, ActionsQueue), f"queue must inherit ActionsQueue: {type(actions_queue)}"
        self.env = env
        self._actions_queue = actions_queue
        self._action_fn = action_fn

    @property
    def actions_queue(self) -> ActionsQueue:
        """The actions queue where the actions are inserted"""
        return self._actions_queue

    @property
    def action_fn(self) -> ActionFn:
        """Given a generic action, communicates it to the robot"""
        return self._action_fn

    def run(self):
        while res := self.env.is_running():
            try:
                action: Action = self.actions_queue.get(block=True, timeout=1_000)
                logger.log_every_s(f"Received action: '{action}' (#in queue: {len(self.actions_queue)})", "DEBUG")
                logger.trace(f"Received action: '{action}' (#in queue: {len(self.actions_queue)})")
                res = self.action_fn(self.env, action)
                if res is False:
                    logger.warning(f"Could not perform action '{action}'")
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Error {e}\nTraceback: {traceback.format_exc()}")
                break

        logger.debug(f"Stopping {self}. {self.env.is_running()=}")
