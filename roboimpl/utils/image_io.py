"""image_io.py - Image utils that are I/O or app specific, not part of the generic lib"""
import numpy as np
from PIL import Image

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
