"""screen_displayer_cv2.py - OpenCV2 screen displayer"""
import numpy as np
from overrides import overrides
from roboimpl.utils import logger

try:
    import cv2
except ImportError:
    logger.error("OpenCV is not installed. Set `ROBOIMPL_SCREEN_DISPLAYER_BACKEND='tkinter' or install opencv")

from .screen_displayer_utils import DisplayerBackend

_KEYCODE_MAP = {
    **{k: chr(k) for k in range(ord("a"), ord("z") + 1)},
    **{k: chr(k) for k in range(ord("A"), ord("Z") + 1)},
    81: "Left", 82: "Up", 83: "Right", 84: "Down",  # arrow keys (Linux)
    27: "Escape", 13: "Return", 32: "space",
}

class ScreenDisplayerCV2(DisplayerBackend):
    """CV2-based screen displayer."""
    def __init__(self):
        self._window_name: str | None = None
        self._is_open = False

    @overrides
    def initialize_window(self, height: int, width: int, title: str):
        """starts the tk window"""
        self._window_name = title
        cv2.namedWindow(self._window_name, cv2.WINDOW_NORMAL | cv2.WINDOW_FREERATIO | cv2.WINDOW_GUI_NORMAL)
        cv2.resizeWindow(self._window_name, width, height)
        self._is_open = True

    @overrides
    def get_current_size(self) -> tuple[int, int]:
        width, height = cv2.getWindowImageRect(self._window_name)[2:4]
        return height, width

    @overrides
    def poll_events(self) -> list[str]:
        # waitKey(1) is required to pump the event loop
        key = cv2.waitKey(1) & 0xFF
        if key == 255:  # no key pressed
            return []

        # Check if window was closed
        if cv2.getWindowProperty(self._window_name, cv2.WND_PROP_VISIBLE) < 1:
            self._is_open = False
            return []

        if keysym := _KEYCODE_MAP.get(key):
            return [keysym] # TODO: KeyEvent(keysym=keysym) later on
        return []

    @overrides
    def update_frame(self, frame: np.ndarray):
        if not self._is_open:
            return
        # OpenCV expects BGR
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        cv2.imshow(self._window_name, frame_bgr)

    @overrides
    def close_window(self):
        if self._window_name:
            cv2.destroyWindow(self._window_name)
            self._is_open = False
