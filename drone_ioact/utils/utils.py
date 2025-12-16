"""generic utils file"""
import os
from pathlib import Path
from datetime import datetime
from loggez import make_logger
import numpy as np
from PIL import Image

DEBUG_FREQ_S = float(os.getenv("DEBUG_FREQ_S", "2"))
LAST_DEBUG: dict[str, float] = {}

def get_project_root() -> Path:
    """returns the project root"""
    return Path(__file__).parents[2]

logger = make_logger("DRONE", log_file=Path.cwd() / f"{get_project_root()}/logs/{datetime.now().isoformat()[0:-6]}.txt")

def log_debug_every_s(start: datetime, msg: str):
    """logs only once every DEBUG_FREQ_S with logger.debug to avoid spam"""
    global LAST_DEBUG # pylint: disable=global-statement, global-variable-not-assigned
    LAST_DEBUG[key] = LAST_DEBUG.get(key := str(start), 0) # pylint: disable=used-before-assignment
    if (now_s := (datetime.now() - start).total_seconds()) - LAST_DEBUG[key] >= DEBUG_FREQ_S:
        LAST_DEBUG[key] = now_s
        logger.debug(msg)

def semantic_map_to_image(semantic_map: np.ndarray, color_map: list[tuple[int, int, int]]) -> np.ndarray:
    """Colorize semantic segmentation maps. Must be argmaxed (H, W)."""
    assert np.issubdtype(semantic_map.dtype, np.integer), semantic_map.dtype
    assert (max_class := semantic_map.max()) <= len(color_map), (max_class, len(color_map))
    assert len(semantic_map.shape) == 2, f"expected (H, W), got {semantic_map.shape}"
    return np.array(color_map)[semantic_map].astype(np.uint8)

def image_read(path: str) -> np.ndarray:
    """image reader from a path. Returns a RGB image even if the underlying image is grayscale. Removes any alpha."""
    img_pil = Image.open(path)
    img_np = np.array(img_pil, dtype=np.uint8)
    img_np = np.repeat(img_np[..., None], repeats=3, axis=-1) if img_pil.mode == "L" else img_np
    return img_np[..., 0:3] # return RGB only

def image_write(image: np.ndarray, path: str):
    """PIL image writer"""
    assert image.dtype == np.uint8, f"{image.dtype=}"
    assert len(image.shape) == 3, image.shape
    Image.fromarray(image, "RGB").save(path)
