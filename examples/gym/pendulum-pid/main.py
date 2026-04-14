#!/usr/bin/env python3
"""basic hello world that instantiates a cartpole"""
from functools import partial
import gymnasium as gym
import numpy as np
from loggez import make_logger
from robobase import Robot, DataChannel, ActionsQueue, Action
from roboimpl.controllers import ScreenDisplayer, Key
from roboimpl.envs.gym import GymEnv, GymState, gym_action_fn, GYM_ACTION_NAMES

logger = make_logger("GYM")

def controller_fn(data: dict[str, GymState], action_space: gym.Space) -> list[Action]:
    """controller fn: env state (data) to actions (generic)"""
    if data["state"].truncated or data["state"].terminated:
        return [Action("reset")]
    act = Action("step", parameters=(action_space.sample(), ))
    logger.debug(f"Action: {act}")
    return [act]

def main():
    """main fn"""
    env = GymEnv(gym.make("Pendulum-v1", render_mode="rgb_array"))
    data_channel = DataChannel(["state"], lambda a, b: np.allclose(a["state"].observation, b["state"].observation))
    actions_queue = ActionsQueue(action_names=GYM_ACTION_NAMES)

    robot = Robot(env=env, data_channel=data_channel, actions_queue=actions_queue, action_fn=gym_action_fn)
    robot.add_controller(partial(controller_fn, action_space=env.action_space))
    robot.add_controller(ScreenDisplayer(data_channel, actions_queue, screen_frame_callback=lambda d: env.render(),
                                         keyboard_fn=lambda pressed: [Action("close")] if Key.Esc in pressed else []))

    robot.run()
    env.close()

if __name__ == "__main__":
    main()
