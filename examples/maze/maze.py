"""maze.py -- simple 2D maze environment for testing purposes"""
from __future__ import annotations
from datetime import datetime
from typing import NamedTuple
import time
from loggez import make_logger
import numpy as np

EMPTY = 0
WALL = 1
PLAYER = 2
EXIT = 3

ENTRY_TO_CHAR = {
    EMPTY: "_",
    WALL: "x",
    PLAYER: "P",
    EXIT: "o",
}
FREQUENCY = 30

logger = make_logger("MAZE")

class PointIJ(NamedTuple):
    """2D point tuple in IJ coordinates"""
    i: int
    j: int

    def __add__(self, other: tuple | PointIJ) -> PointIJ:
        return PointIJ(self.i + other[0], self.j + other[1])
    def __sub__(self, other: tuple | PointIJ) -> PointIJ:
        return PointIJ(self.i - other[0], self.j - other[1])
    def __repr__(self):
        return f"({self.i}, {self.j})"

class Maze:
    """Maze implementation"""
    def __init__(self, maze_size: tuple[int, int], walls_prob: float, max_tries: int, random_seed: int | None = None):
        self.maze_size = maze_size
        np.random.seed(random_seed)
        self.maze = (np.random.random(size=maze_size) < walls_prob).astype(int)
        exit_pos, player_pos = np.random.choice(range(np.prod(maze_size)), 2, replace=False).tolist()
        self.player_pos: PointIJ = PointIJ(player_pos // maze_size[1], player_pos % maze_size[1])
        self.exit_pos: PointIJ = PointIJ(exit_pos // maze_size[1], exit_pos % maze_size[1])
        self.maze[*self.player_pos] = EMPTY # make sure this is empty so we don't have weird behavior
        self.maze[*self.exit_pos] = EMPTY # make sure this is empty so we don't have weird behavior

        self.max_tries = max_tries
        self.n_moves = 0
        self.initial_distance = np.linalg.norm(self.exit_pos - self.player_pos, ord=1).item()
        self._prev_time = datetime(1900, 1, 1)

    def is_finished(self) -> bool:
        """returns true if the maze is finished"""
        return self.player_pos == self.exit_pos

    def move_player(self, direction: str) -> bool:
        """moves player in one of the 4 directions. Returns true on succes, false otherwise"""
        assert not self.is_finished() and self.n_moves < self.max_tries, "maze already finished"
        self.n_moves += 1
        delta = {"up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1)}
        if direction not in delta.keys():
            logger.debug(f"Direction '{direction}' not in {list(delta.keys())}")
            return False

        new_pos = self.player_pos + delta[direction]
        if new_pos.i < 0 or new_pos.i >= self.maze_size[0] or new_pos.j < 0 or new_pos.j >= self.maze_size[1]:
            logger.debug(f"New position: {new_pos} is outside of {self.maze_size=}")
            return False
        if self.maze[*new_pos] == WALL:
            logger.debug(f"New position: {new_pos} is in a wall.")
            return False
        self.player_pos = new_pos
        if self.is_finished() or self.n_moves >= self.max_tries:
            logger.info("Maze environment ending.")
        return True

    def print_maze(self):
        """print the current state of the maze"""
        maze_entries_ix = dict(zip(range(len(ENTRY_TO_CHAR)), ENTRY_TO_CHAR.values()))
        char_maze = np.vectorize(maze_entries_ix.get)(self.maze)
        char_maze[*self.exit_pos] = ENTRY_TO_CHAR[EXIT]
        char_maze[*self.player_pos] = ENTRY_TO_CHAR[PLAYER]
        print(f"Moves: {self.n_moves}")
        for row in char_maze:
            print(" ".join(row))
        print("=" * 80)

    def get_state(self) -> dict[str, PointIJ | float]:
        """gets the current state of the maze w.r.t the player position"""
        if (diff := (1 / FREQUENCY) - ((now := datetime.now()) - self._prev_time).total_seconds()) > 0:
            time.sleep(diff)
        self._prev_time = now
        distance_to_exit = abs(self.exit_pos.i - self.player_pos.i) + abs(self.exit_pos.j - self.player_pos.j)
        return {"distance_to_exit": distance_to_exit, "n_moves": self.n_moves}
