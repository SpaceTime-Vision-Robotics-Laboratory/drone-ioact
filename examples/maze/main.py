#!/usr/bin/env python3
"""maze main function"""
from __future__ import annotations
import time
import sys
from pathlib import Path
import random
from queue import Queue

from robobase import (DataProducer, DataChannel, ActionsQueue, ThreadGroup,
                      DataProducerList, Planner, DataItem, ActionConsumer, Action)

sys.path.append(Path(__file__).parent.__str__())
from maze import Maze, logger # pylint: disable=all

MAZE_SIZE = (10, 10)
MAZE_WALLS_PROB = 0.2
MAZE_MAX_TRIES = 100

class MazeDataProducer(DataProducer):
    """maze data producer"""
    def __init__(self, maze: Maze):
        super().__init__(modalities=["position", "distance_to_exit", "timestamp"])
        self.maze = maze

    def produce(self, deps = None) -> dict[str, DataItem]:
        return self.maze.get_state()

def random_planner_fn(data: dict[str, DataItem]) -> Action: # pylint:disable=unused-argument
    """random planner"""
    res = random.choice(["up", "down", "left", "right"])
    logger.debug(f"Doing action: {res}")
    return res

def main():
    """main fn"""
    planner_fn = {
        "random": random_planner_fn,
    }[sys.argv[1]]
    maze = Maze(maze_size=MAZE_SIZE, walls_prob=MAZE_WALLS_PROB, max_tries=MAZE_MAX_TRIES)
    maze2data = MazeDataProducer(maze)

    actions_queue = ActionsQueue(Queue(), actions=["up", "down", "left", "right"])
    data_channel = DataChannel(supported_types=["position", "distance_to_exit", "timestamp"],
                               eq_fn=lambda a, b: a["timestamp"] == b["timestamp"])

    planner = Planner(data_channel, actions_queue, planner_fn=planner_fn)
    action2maze = ActionConsumer(actions_queue, actions_fn=maze.move_player,
                                 termination_fn=lambda: maze.is_finished() or maze.n_moves >= maze.max_tries)

    threads = ThreadGroup({
        "Maze -> Data": DataProducerList(data_channel, data_producers=[maze2data]),
        "Planner": planner,
        "Action -> Maze": action2maze,
    }).start()

    while not threads.is_any_dead():
        time.sleep(1) # important to not throttle everything with this main thread
        maze.print_maze()
    threads.join(timeout=1) # stop all the threads

    _not = f"{' not' if not maze.is_finished() else ''}"
    logger.info(f"Maze{_not} finished in {maze.n_moves} steps. Initial distance of: {maze.initial_distance}")

if __name__ == "__main__":
    main()
