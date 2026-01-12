"""generic utils file"""
from pathlib import Path

def get_project_root() -> Path:
    """returns the project root"""
    return Path(__file__).parents[2]
