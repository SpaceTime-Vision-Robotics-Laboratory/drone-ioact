"""generic utils for images manipulation"""
from PIL import Image
import numpy as np

from .utils import logger

try:
    import cv2
    DEFAULT_RESIZE_BACKEND = "cv2"
except ImportError:
    logger.error("OpenCV is not installed. Will use PIL for image_reisze")
    DEFAULT_RESIZE_BACKEND = "pil"

def image_write(data: np.ndarray, path: str):
    """PIL image writer"""
    assert data.min() >= 0 and data.max() <= 255
    img = Image.fromarray(data.astype(np.uint8), "RGB")
    img.save(path)

def image_resize(data: np.ndarray, height: int | None, width: int | None,
                 interpolation: str = "bilinear", backend: str = DEFAULT_RESIZE_BACKEND, **kwargs) -> np.ndarray:
    """Wrapper on top of Image(arr).resize((w, h), args) or cv2.resize. Sadly cv2 is faster so we cannot remove it."""

    def _scale(a: int, b: int, c: int) -> int:
        return int(b / a * c)

    def _get_height_width(data_shape: tuple[int, int], height: int | None, width: int | None) -> tuple[int, int]:
        width = _scale(data_shape[0], height, data_shape[1]) if (width is None or width == -1) else width
        height = _scale(data_shape[1], width, data_shape[0]) if (height is None or height == -1) else height
        return height, width

    height, width = _get_height_width(data.shape, height, width)
    assert isinstance(height, int) and isinstance(width, int), (type(height), type(width))
    if data.shape[0:2] == (height, width):
        return data

    if backend == "cv2":
        interpolation = {
            "nearest": cv2.INTER_NEAREST,
            "bilinear": cv2.INTER_LINEAR,
            "lanczos": cv2.INTER_LANCZOS4
        }[interpolation]
        res = cv2.resize(data, dsize=(width, height), interpolation=interpolation, **kwargs)
    elif backend == "pil":
        interpolation_type: Image.Resampling = {
            "nearest": Image.Resampling.NEAREST,
            "bilinear": Image.Resampling.BILINEAR,
            "lanczos": Image.Resampling.LANCZOS,
        }[interpolation]
        assert data.dtype == np.uint8, f"Only uint8 allowed, got {data.dtype}"
        pil_image = Image.fromarray(data).resize((width, height), resample=interpolation_type, **kwargs)
        res = np.asarray(pil_image)
    else:
        raise ValueError(str(backend))

    return res

def colorize_semantic_segmentation(semantic_map: np.ndarray, color_map: list[tuple[int, int, int]]) -> np.ndarray:
    """Colorize semantic segmentation maps. Must be argmaxed (H, W). Can paint over the original RGB frame or not."""
    assert np.issubdtype(semantic_map.dtype, np.integer), semantic_map.dtype
    assert (max_class := semantic_map.max()) <= len(color_map), (max_class, len(color_map))
    return np.array(color_map)[semantic_map]
