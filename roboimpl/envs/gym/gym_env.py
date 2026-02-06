"""gym_env.py - Wrapper for gymnasium environments based on the state=env.step(action) model"""
from typing import Any
from dataclasses import dataclass
from overrides import overrides
import gymnasium as gym # pylint: disable=import-error
from gymnasium.core import ObsType
from robobase import Environment

MAX_STEPS = 1000
INITIAL_SEED = 42
RenderFrame = Any

@dataclass
class GymState:
    """GmyState object that encapsulates the 5 standard returns of env.step() (or reset())"""
    observation: ObsType
    reward: float
    terminated: bool
    truncated: bool
    info: dict

class GymEnv(Environment):
    """
    Wrapper for a gym-based environment. Uses a threading.Event() to simulate the state=env.step(action) model.
    See discussion: https://aistudio.google.com/app/prompts/1WGwVg5ZsOR-P7Y1TxfIXh7zWoPFN1mWF
    """
    def __init__(self, env: gym.Env, max_steps: int | None = MAX_STEPS, seed: int | None = INITIAL_SEED):
        super().__init__()
        assert env.render_mode is None or env.render_mode in ("ascii", "rgb_array"), env.render_mode
        self.env = env

        self._last_state: GymState = None
        self.seed = seed
        self.total_steps = 0
        self.max_steps = max_steps
        self._is_done = False

        self.reset()

    @overrides
    def is_running(self) -> bool:
        return self.total_steps < self.max_steps and not self._is_done

    @overrides
    def get_state(self) -> dict:
        self.data_ready.wait_and_clear() # wait for green light and set red light
        return {"state": self._last_state}

    @overrides
    def get_modalities(self) -> list[str]:
        """The list of raw modalities produced by this environment"""
        return ["state"]

    @overrides
    def close(self):
        """closes this env"""
        self._is_done = True
        self.env.close()
        self.data_ready.set() # set to green light

    def render(self) -> RenderFrame | None:
        """Calls the 'render' method manually so we return a frame (or ascii) for human display"""
        return self.env.render()

    def step(self, action: Any):
        """Apply a step in the gym environment. Updates the state as well."""
        self.total_steps += 1
        self._last_state = GymState(*self.env.step(action))
        self.data_ready.set() # set to green light

    def reset(self):
        """Resets the gym environment to the initial state. Can be controlled via env.seed"""
        res = self.env.reset(seed=self.seed)
        self._last_state = GymState(observation=res[0], reward=-2**31, terminated=False, truncated=False, info=res[1])
        self.data_ready.set() # set to green light
