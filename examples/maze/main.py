#!/usr/bin/env python3
"""maze main function"""
from __future__ import annotations
import time
import sys
import os
from functools import partial
from dataclasses import dataclass
from pathlib import Path
import random
from queue import Queue
from loggez import make_logger

from robobase import (DataProducer, DataChannel, ActionsQueue, ThreadGroup,
                      DataProducerList, Planner, DataItem, ActionConsumer, Action)

sys.path.append(Path(__file__).parent.__str__())
from maze import Maze, PointIJ # pylint: disable=all

logger = make_logger("MAZE_SOLVER")

MAZE_SIZE = (10, 10)
MAZE_WALLS_PROB = 0.2
MAZE_MAX_TRIES = 200
INF = 2**31
PRINT = os.getenv("PRINT", "0") == "1"
SEED = random.randint(0, 10000)

class MazeDataProducer(DataProducer):
    """maze data producer"""
    def __init__(self, maze: Maze):
        super().__init__(modalities=["distance_to_exit", "n_moves"])
        self.maze = maze

    def produce(self, deps = None) -> dict[str, DataItem]:
        return self.maze.get_state()

def random_planner_fn(data: dict[str, DataItem]) -> Action: # pylint:disable=unused-argument
    """random planner"""
    res = random.choice(["up", "down", "left", "right"])
    logger.debug(f"Doing action: {res}")
    return res

@dataclass
class State:
    position: PointIJ # current position
    distance: float # distance from now to goal
    move: str | None # what move I took here
    prev_state: State | None # the previous state

class Strategy1:
    def __init__(self):
        self.pos_to_distance: dict[PointIJ, float] = {} # {relative position: score], -inf if wall or empty path
        self.state = State(position=PointIJ(0, 0), distance=2**31, move=None, prev_state=None)

    def move(self, move: str) -> str:
        """wrapper to update stuff before returning"""
        self.state.move = move
        move_to_delta = {"up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1)}
        logger.debug(f"Move: {move}. Position: {self.state.position}. Distance: {self.state.distance}.")
        if self.pos_to_distance.get(self.state.position + move_to_delta[self.state.move], 0) == INF:
            logger.debug(self.pos_to_distance)
            raise ValueError("stuck most likely")
        return move

    def __call__(self, data: dict[str, DataItem]) -> Action:
        move_to_rev = {"up": "down", "right": "left", "down": "up", "left": "right"}
        move_to_delta = {"up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1)}
        moves = list(move_to_rev)
        curr_distance = data["distance_to_exit"]
        prev_state = self.state

        if len(self.pos_to_distance) == 0: # note: it's safe to do it here as you cannot spawn in a wall.
            self.pos_to_distance[self.state.position] = self.state.distance = data["distance_to_exit"]
            logger.debug("> First move")
            return self.move("up")

        self.state = State(
            position=prev_state.position + move_to_delta[prev_state.move],
            distance=curr_distance,
            move=None,
            prev_state=prev_state
        )

        if curr_distance == prev_state.distance: # last move was into a wall, so we mark it as bad and get rid of it
            # mark that position as inf and revert to previous one
            self.pos_to_distance[self.state.position] = INF
            self.state = prev_state
            logger.debug("> Hit wall, reverting state")

        # pick first unexplored move
        self.pos_to_distance[self.state.position] = curr_distance
        n_walls = 0
        potential_moves, potential_scores = [], []
        for potential_move in moves:
            potential_position = self.state.position + move_to_delta[potential_move]
            if potential_position not in self.pos_to_distance:
                logger.debug("> Go in first unexplored move")
                return self.move(potential_move)
            else: # was previously explored
                potential_moves.append(potential_move)
                potential_scores.append(self.pos_to_distance[potential_position])
                if self.pos_to_distance[potential_position] == INF:
                    n_walls += 1

        assert n_walls < 4, "stuck?"
        if n_walls == 3:
            self.pos_to_distance[self.state.position] = INF
            logger.debug("> 3 walls, going back")
        logger.debug(f"> {n_walls} walls. Picking smallest distance path. If >1, pick at random")
        min_score = min(potential_scores)
        potential_moves = [move for i, move in enumerate(potential_moves) if potential_scores[i] == min_score]
        return self.move(random.choice(potential_moves))

def actions_fn(action: Action, maze: Maze):
    maze.move_player(action)
    if PRINT:
        print("\n" * 20)
        maze.print_maze()

def main():
    """main fn"""
    planner_fn = {
        "random": random_planner_fn,
        "strategy1": Strategy1(),
    }[sys.argv[1]]
    maze = Maze(maze_size=MAZE_SIZE, walls_prob=MAZE_WALLS_PROB, max_tries=MAZE_MAX_TRIES, random_seed=SEED)
    logger.info(f"Maze started. initial distance of: {maze.initial_distance}")
    maze.print_maze()

    maze2data = MazeDataProducer(maze)
    actions_queue = ActionsQueue(Queue(), actions=["up", "down", "left", "right"])
    data_channel = DataChannel(supported_types=["distance_to_exit", "n_moves"],
                               eq_fn=lambda a, b: a["n_moves"] == b["n_moves"])

    planner = Planner(data_channel, actions_queue, planner_fn=planner_fn)
    action2maze = ActionConsumer(actions_queue, actions_fn=partial(actions_fn, maze=maze),
                                 termination_fn=lambda: maze.is_finished() or maze.n_moves >= maze.max_tries)

    threads = ThreadGroup({
        "Maze -> Data": DataProducerList(data_channel, data_producers=[maze2data]),
        "Planner": planner,
        "Action -> Maze": action2maze,
    }).start()

    while not threads.is_any_dead():
        time.sleep(1) # important to not throttle everything with this main thread
    threads.join(timeout=1) # stop all the threads

    maze.print_maze()
    logger.info(f"Maze {'finished in' if maze.is_finished() else 'not finished after'} {maze.n_moves} moves.")

if __name__ == "__main__":
    main()
