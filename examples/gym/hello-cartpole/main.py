#!/usr/bin/env python3
"""basic hello world that instantiates a cartpole"""
from typing import Any
from functools import partial
import gymnasium as gym
import numpy as np
from loggez import make_logger
from robobase import Robot, DataChannel, ActionsQueue, Action
from roboimpl.controllers import ScreenDisplayer
from roboimpl.envs.gym import GymEnv, GymState

logger = make_logger("CARTPOLE")

def action_fn(env: GymEnv, act: Any):
    """generic actions to gym-specific actions"""
    if act == "reset":
        env.reset()
    elif act == "stop":
        env.close()
    else:
        env.step([float(act)])

def controller_fn(data: dict[str, GymState], actions: list[Action]) -> Action:
    """controller fn: env state (data) to actions (generic)"""
    if data["state"].truncated or data["state"].terminated:
        logger.debug("resetting")
        return "reset"
    act = np.random.choice(actions).item()
    logger.debug(f"Action: {act}")
    return act

def main():
    """main fn"""
    env = GymEnv(gym.make("Pendulum-v1", render_mode="rgb_array"))
    data_channel = DataChannel(["state"], lambda a, b: np.allclose(a["state"].observation, b["state"].observation))
    # gym_actions = env.env.action_space
    # actions = list(map(str, range(gym_actions.start, gym_actions.n)))
    actions = [str(x) for x in np.linspace(-2, 2, 10000)]
    actions_queue = ActionsQueue(actions=actions + ["reset", "stop"])

    robot = Robot(env=env, data_channel=data_channel, actions_queue=actions_queue, action_fn=action_fn)
    robot.add_controller(partial(controller_fn, actions=actions))
    robot.add_controller(ScreenDisplayer(data_channel, actions_queue, screen_frame_callback=lambda d: env.render(),
                                         key_to_action={"Escape": "stop"}))

    robot.run()
    env.close()

if __name__ == "__main__":
    main()
