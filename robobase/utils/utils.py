"""generic utils file"""
from pathlib import Path
from datetime import datetime
from functools import partial
from typing import Any, T, Iterable, Callable
from loggez import make_logger

def get_project_root() -> Path:
    """returns the project root"""
    return Path(__file__).parents[2]

logs_dir = get_project_root() / "logs"

logger = make_logger("ROBOBASE", log_file=f"{logs_dir}/{datetime.now().isoformat()[0:-7]}/ROBOBASE.txt")

def parsed_str_type(item: Any) -> str:
    """Given an object with a type of the format: <class 'A.B.C.D'>, parse it and return 'A.B.C.D'"""
    return str(type(item)).rsplit(".", maxsplit=1)[-1][0:-2]


def natsorted(seq: Iterable[T], key: Callable[[T], "SupportsGTAndLT"] | None = None, reverse: bool=False) -> list[T]:
    """wrapper on top of natsorted so we can properly remove it"""
    def _try_convert_to_num(x: str) -> str | int | float:
        try:
            return int(x)
        except ValueError:
            try:
                return float(x)
            except ValueError:
                return x

    def natsorted_key(item: T, key: Callable) -> "SupportsGTAndLT":
        item = key(item)
        if isinstance(item, str):
            ix_dot = item.rfind(".")
            item = item[0:ix_dot] if ix_dot != -1 else item
            item = _try_convert_to_num(item)
        return item

    key = key or (lambda item: item)
    return sorted(seq, key=partial(natsorted_key, key=key), reverse=reverse)
