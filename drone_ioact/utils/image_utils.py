"""generic utils for images manipulation"""
from PIL import Image, ImageDraw
import numpy as np

from .utils import logger

try:
    import cv2
    DEFAULT_RESIZE_BACKEND = "cv2"
except ImportError:
    logger.error("OpenCV is not installed. Will use PIL for image_reisze")
    DEFAULT_RESIZE_BACKEND = "pil"

def image_write(image: np.ndarray, path: str):
    """PIL image writer"""
    assert image.min() >= 0 and image.max() <= 255
    img = Image.fromarray(image.astype(np.uint8), "RGB")
    img.save(path)

def image_resize(image: np.ndarray, height: int | None, width: int | None,
                 interpolation: str = "bilinear", backend: str = DEFAULT_RESIZE_BACKEND, **kwargs) -> np.ndarray:
    """Wrapper on top of Image(arr).resize((w, h), args) or cv2.resize. Sadly cv2 is faster so we cannot remove it."""

    def _scale(a: int, b: int, c: int) -> int:
        return int(b / a * c)

    def _get_height_width(image_shape: tuple[int, int], height: int | None, width: int | None) -> tuple[int, int]:
        width = _scale(image_shape[0], height, image_shape[1]) if (width is None or width == -1) else width
        height = _scale(image_shape[1], width, image_shape[0]) if (height is None or height == -1) else height
        return height, width

    assert image.dtype == np.uint8, f"{image.dtype=}"
    assert len(image.shape) == 3, image.shape
    height, width = _get_height_width(image.shape, height, width)
    assert isinstance(height, int) and isinstance(width, int), (type(height), type(width))
    if image.shape[0:2] == (height, width):
        return image

    if backend == "cv2":
        interpolation = {
            "nearest": cv2.INTER_NEAREST,
            "bilinear": cv2.INTER_LINEAR,
            "lanczos": cv2.INTER_LANCZOS4
        }[interpolation]
        res = cv2.resize(image, dsize=(width, height), interpolation=interpolation, **kwargs)
    elif backend == "pil":
        interpolation_type: Image.Resampling = {
            "nearest": Image.Resampling.NEAREST,
            "bilinear": Image.Resampling.BILINEAR,
            "lanczos": Image.Resampling.LANCZOS,
        }[interpolation]
        assert image.dtype == np.uint8, f"Only uint8 allowed, got {image.dtype}"
        pil_image = Image.fromarray(image).resize((width, height), resample=interpolation_type, **kwargs)
        res = np.asarray(pil_image)
    else:
        raise ValueError(str(backend))

    return res

def image_read(path: str) -> np.ndarray:
    """image reader from a path. Returns a RGB image even if the underlying image is grayscale. Removes any alpha."""
    img_pil = Image.open(path)
    img_np = np.array(img_pil, dtype=np.uint8)
    # grayscale -> 3 gray channels repeated.
    img_np = np.repeat(img_np[..., None], repeats=3, axis=-1) if img_pil.mode == "L" else img_np
    return img_np[..., 0:3] # return RGB only

def image_draw_rectangle(image: np.ndarray, top_left: tuple[int, int], bottom_right: tuple[int, int],
                         color: tuple[int, int, int], thickness: int) -> np.ndarray:
    """Draws a rectangle (i.e. bounding box) over an image. Thinkness is in pixels."""
    assert image.dtype == np.uint8, f"{image.dtype=}"
    assert len(image.shape) == 3, image.shape
    img_pil = Image.fromarray(image)
    draw = ImageDraw.Draw(img_pil)
    draw.rectangle([*top_left, *bottom_right], outline=color, width=thickness)
    return np.array(img_pil)

def image_paste(image1: np.ndarray, image2: np.ndarray) -> np.ndarray:
    """Pastes two [0:255] images over each other. image  takes priority everywhere except where it's (0, 0, 0)"""
    assert image1.dtype == image2.dtype == np.uint8, f"{image1.dtype=}, {image1.dtype=}"
    assert len(image1.shape) == len(image2.shape) == 3, (image1.shape, image2.shape)
    assert image1.shape == image2.shape, (image1.shape, image2.shape)

    mask: np.ndarray = (image2.astype(int).sum(-1, keepdims=True) == 0).astype(np.uint8)
    result = image1 * mask + image2 * (~mask)
    return result

def semantic_map_to_image(semantic_map: np.ndarray, color_map: list[tuple[int, int, int]]) -> np.ndarray:
    """Colorize semantic segmentation maps. Must be argmaxed (H, W)."""
    assert np.issubdtype(semantic_map.dtype, np.integer), semantic_map.dtype
    assert (max_class := semantic_map.max()) <= len(color_map), (max_class, len(color_map))
    assert len(semantic_map.shape) == 2, f"expected (H, W), got {semantic_map.shape}"
    return np.array(color_map)[semantic_map].astype(np.uint8)
