"""generic utils for images manipulation from gitlab.com/meehai/image_utils.py"""
from PIL import Image, ImageDraw
import numpy as np
from loggez import make_logger

logger = make_logger("IMAGE_UTILS")

try:
    import cv2
    DEFAULT_RESIZE_BACKEND = "cv2"
except ImportError:
    logger.error("OpenCV is not installed. Will use PIL for image_reisze")
    DEFAULT_RESIZE_BACKEND = "pil"

Point = tuple[int, int] # (U, V) coordinates
Color = tuple[int, int, int] # RGB (0-255)
U, V = 0, 1

# module utilities

def _check_image(image: np.ndarray):
    assert image.dtype == np.uint8, f"{image.dtype=}"
    assert len(image.shape) == 3, image.shape

def _scale(a: int, b: int, c: int) -> int:
    return int(b / a * c)

def _get_height_width(image_shape: tuple[int, int], height: int | None, width: int | None) -> tuple[int, int]:
    width = _scale(image_shape[U], height, image_shape[V]) if (width is None or width == -1) else width
    height = _scale(image_shape[V], width, image_shape[U]) if (height is None or height == -1) else height
    return height, width

def _get_px_from_perc(perc: float, image_shape: tuple[int, int]) -> int:
    """returns the size in pixels from percents"""
    min_shape = perc * min(image_shape[0], image_shape[1]) / 100
    if min_shape < 1:
        logger.debug2(f"{min_shape=} below 1 pixel. Returning 1")
    return max(1, int(min_shape))

# public API

def semantic_map_to_image(semantic_map: np.ndarray, color_map: list[Color]) -> np.ndarray:
    """Colorize semantic segmentation maps. Must be argmaxed (H, W)."""
    assert np.issubdtype(semantic_map.dtype, np.integer), semantic_map.dtype
    assert (max_class := semantic_map.max()) <= len(color_map), (max_class, len(color_map))
    assert len(semantic_map.shape) == 2, f"expected (H, W), got {semantic_map.shape}"
    return np.array(color_map)[semantic_map].astype(np.uint8)

def image_read(path: str) -> np.ndarray:
    """image reader from a path. Returns a RGB image even if the underlying image is grayscale. Removes any alpha."""
    img_pil = Image.open(path)
    img_np = np.array(img_pil, dtype=np.uint8)
    # grayscale -> 3 gray channels repeated.
    img_np = np.repeat(img_np[..., None], repeats=3, axis=-1) if img_pil.mode == "L" else img_np
    return img_np[..., 0:3] # return RGB only

def image_write(image: np.ndarray, path: str):
    """PIL image writer"""
    _check_image(image)
    img = Image.fromarray(image, "RGB")
    img.save(path)

def image_resize(image: np.ndarray, height: int | None, width: int | None,
                 interpolation: str = "bilinear", backend: str = DEFAULT_RESIZE_BACKEND, **kwargs) -> np.ndarray:
    """Wrapper on top of Image(arr).resize((w, h), args) or cv2.resize. Sadly cv2 is faster so we cannot remove it."""
    _check_image(image)
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

# drawing functions. All functions have an 'inplace' parameter which is set to False by default.

def image_draw_rectangle(image: np.ndarray, top_left: Point, bottom_right: Point,
                         color: Color, thickness: float, inplace: bool=False) -> np.ndarray:
    """Draws a rectangle (i.e. bounding box) over an image. Thinkness is in percents w.r.t smallest axis (min 1)."""
    _check_image(image)

    if top_left[U] > bottom_right[U]:
        logger.debug2(f"{top_left=}, {bottom_right=}. Swapping.")
        top_left, bottom_right = bottom_right, top_left

    thickness_px = _get_px_from_perc(thickness, image.shape)
    img_pil = Image.fromarray(image)
    draw = ImageDraw.Draw(img_pil)
    draw.rectangle([top_left[V], top_left[U], bottom_right[V], bottom_right[U]], outline=color, width=thickness_px)
    res = np.array(img_pil)
    if inplace:
        image[:] = res
    return res

def image_draw_circle(image: np.ndarray, center: Point, radius: float, color: Color, thickness: int,
                      inplace: bool=False) -> np.ndarray:
    """draw a circle at a given center with a radius (in percents)"""
    _check_image(image)
    assert thickness > 0 or thickness == -1, "thinkness cannot be 0"
    img_pil = Image.fromarray(image)
    draw = ImageDraw.Draw(img_pil)
    r_px = _get_px_from_perc(radius, image.shape)

    if thickness == -1:
        draw.ellipse((center[V] - r_px, center[U] - r_px, center[V] + r_px, center[U] + r_px), fill=color)
    else:
        draw.ellipse((center[V] - r_px, center[U] - r_px, center[V] + r_px, center[U] + r_px), outline=color)
    res =  np.array(img_pil)
    if inplace:
        image[:] = res
    return res

def image_draw_polygon(image: np.ndarray, points: list[Point], color: Color, thickness: int,
                       inplace: bool=False) -> np.ndarray:
    """draws a polygon given some points"""
    _check_image(image)
    assert len(points) >= 2, "at least 2 points needed"

    img_pil = Image.fromarray(image)
    draw = ImageDraw.Draw(img_pil)
    for l, r in zip(points, [*points[1:], points[0]]): # noqa: E741
        draw.line((l[V], l[U], r[V], r[U]), fill=color, width=thickness)
    res = np.array(img_pil)
    if inplace:
        image[:] = res
    return res

def image_paste(image1: np.ndarray, image2: np.ndarray, top_left: Point=(0, 0),
                background_color: Color=(0, 0, 0), inplace: bool=False) -> np.ndarray:
    """Pastes two [0:255] images over each other. image  takes priority everywhere except where it's (0, 0, 0)"""
    _check_image(image1)
    _check_image(image2)
    assert image1.shape[U] - top_left[U] >= image2.shape[U]
    assert image1.shape[V] - top_left[V] >= image2.shape[V]
    res = image1 if inplace else image1.copy()

    res_shifted = res[top_left[U]:top_left[U] + image2.shape[U], top_left[V]:top_left[V] + image2.shape[V]]
    mask: np.ndarray = (image2 == background_color).sum(-1, keepdims=True) == 3
    res_shifted[:] = res_shifted * mask + image2 * (~mask)
    return res
