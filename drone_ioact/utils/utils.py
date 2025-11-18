"""generic utils file"""
from pathlib import Path
from datetime import datetime
import numpy as np
from loggez import make_logger

def get_project_root() -> Path:
    """returns the project root"""
    return Path(__file__).parents[2]

logger = make_logger("DRONE", log_file=Path.cwd() / f"{get_project_root()}/logs/{datetime.now().isoformat()[0:-6]}.txt")

def lo(x: np.ndarray | None) -> str:
    """reimplementation of lovely_numpy's lo() without any extra stuff that spams the terminal. Only for numericals!"""
    def _dt(x: np.dtype) -> str:
        y = str(x).removeprefix("torch.") if str(x).startswith("torch.") else str(x)
        return y if y == "bool" else (f"{y[0]}{y[-1]}" if y[-1] == "8" else f"{y[0]}{y[-2:]}")
    def _r(x: np.ndarray):
        return round(x.item(), 2)
    assert isinstance(x, (type(None), np.ndarray)) or str(type(x)).find("torch") != -1, type(x)
    if x is None:
        return x
    arr_type = "arr" if isinstance(x, np.ndarray) else "tr"
    μ, σ = x.float().mean() if arr_type == "tr" else x.mean(), x.float().std() if arr_type == "tr" else x.std() # thx tr
    return f"{arr_type}{[*x.shape]} {_dt(x.dtype)} x∈[{_r(x.min())}, {_r(x.max())}], μ={_r(μ)}, σ={_r(σ)}"
