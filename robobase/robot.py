"""robot.py - The basic Robot class that defines all the low-level wirings and should handle 95% of the cases"""
from typing import Callable
import threading
import time
from .environment import Environment
from .data_channel import DataChannel
from .actions_queue import ActionsQueue
from .data_producer import DataProducer, RawDataProducer
from .controller import BaseController, Controller
from .actions2env import Actions2Environment
from .data_producers2channels import DataProducers2Channels
from .types import ActionFn, ControllerFn
from .utils import ThreadGroup, logger

SLEEP_TIME = 1

class Robot:
    """Robot class that interacts with an environment and has a single data channel and a single actions queue"""
    def __init__(self, env: Environment, data_channel: DataChannel, actions_queue: ActionsQueue, action_fn: ActionFn):
        self.env = env
        self.data_channel = data_channel
        self.actions_queue = actions_queue
        self.action_fn = action_fn

        # setup up at run() time
        self._data_producers: list[DataProducer] = []
        self._env2data: DataProducers2Channels | None = None
        self._controllers: dict[str, Controller] = {}
        self._actions2env = Actions2Environment(self.env, self.actions_queue, self.action_fn)
        self._other_threads: dict[str, threading.Thread] = {} # e.g. maybe we want to start the env at the same time.

    def add_data_producer(self, data_producer: DataProducer):
        """Add a data producer (i.e. yolo, semantic, optical flow etc.) to this robot. Has access to 'raw' env data"""
        self._data_producers.append(data_producer)

    def add_controller(self, controller: BaseController | ControllerFn, name: str | None = None):
        """Add a controller with optionally a name to this robot. If name is not set, it will be Controller-{i}"""
        if isinstance(controller, Callable):
            controller = Controller(self.data_channel, self.actions_queue, controller_fn=controller)
        assert isinstance(controller, BaseController), f"Expected 'robobase.Controller', got {type(controller)}"
        name = name or f"Controller-{len(self._controllers)}"
        self._controllers[name] = controller

    def add_other_thread(self, thread: threading.Thread, name: str | None = None):
        """Add another thread to be spawned upon run() time. Useful to start the env at the same time for example"""
        assert isinstance(thread, threading.Thread), type(thread)
        name = name or f"Thread-{len(self._other_threads)}"
        self._other_threads[name] = thread

    def _setup_run(self):
        self.add_data_producer(RawDataProducer(self.env))
        assert len(self._controllers) > 0, "At least one controller expected. Use `robot.add_controller`"
        self._env2data = DataProducers2Channels(data_producers=self._data_producers, data_channels=[self.data_channel])

    def run(self, sleep_duration: float = SLEEP_TIME):
        """start the robot's main loop which in turn starts all the threads: data producer + controllers + actuator"""
        self._setup_run()
        tg = ThreadGroup({
            "env2data": self._env2data,
            **self._controllers,
            **self._other_threads,
            "actions2env": self._actions2env,
        }).start()
        logger.info(f"Started threads: \n{tg}")

        try:
            while not tg.is_any_dead() and self.env.is_running():
                time.sleep(sleep_duration)
        finally:
            tg.join(timeout=sleep_duration)
