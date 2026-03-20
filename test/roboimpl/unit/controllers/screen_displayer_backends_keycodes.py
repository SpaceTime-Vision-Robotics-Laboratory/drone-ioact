from roboimpl.controllers.screen_displayer.screen_displayer_cv2 import _KEYCODE_MAP as KEYCODE_MAP_CV2
from roboimpl.controllers.screen_displayer.screen_displayer_tkinter import _KEYCODE_MAP as KEYCODE_MAP_TKINTER
from roboimpl.controllers import Key
from typing import Any
import pytest

@pytest.mark.parametrize("backend, backend_map", [("cv2", KEYCODE_MAP_CV2), ("tkinter", KEYCODE_MAP_TKINTER)])
def test_ScreenDisplayer_KEYCODE_MAP(backend: str, backend_map: dict[Any, Key]):
    backend_map_rev = {v: k for k, v in backend_map.items()}
    for key in Key:
        assert key in backend_map_rev, f"Key '{key}' not in backend {backend}"
