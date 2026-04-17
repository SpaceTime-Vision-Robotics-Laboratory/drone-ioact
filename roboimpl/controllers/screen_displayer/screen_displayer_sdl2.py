"""screen_displayer_sdl2.py - SDL2 backend for ScreenDisplayer"""
import ctypes
import numpy as np
from overrides import overrides

from roboimpl.utils import logger

try:
    import sdl2

    _SDL2_SCANCODE_MAP: dict[int, Key] = {
        # Letters a-z
        **{sdl2.SDL_SCANCODE_A + i: getattr(Key, chr(ord("a") + i)) for i in range(26)},
        # Arrow keys
        sdl2.SDL_SCANCODE_LEFT: Key.Left,
        sdl2.SDL_SCANCODE_RIGHT: Key.Right,
        sdl2.SDL_SCANCODE_UP: Key.Up,
        sdl2.SDL_SCANCODE_DOWN: Key.Down,
        # Special keys
        sdl2.SDL_SCANCODE_ESCAPE: Key.Esc,
        sdl2.SDL_SCANCODE_RETURN: Key.Enter,
        sdl2.SDL_SCANCODE_SPACE: Key.Space,
        sdl2.SDL_SCANCODE_PAGEUP: Key.PageUp,
        sdl2.SDL_SCANCODE_PAGEDOWN: Key.PageDown,
        sdl2.SDL_SCANCODE_COMMA: Key.Comma,
        sdl2.SDL_SCANCODE_PERIOD: Key.Period,
        # Function keys
        sdl2.SDL_SCANCODE_F1: Key.F1,
        sdl2.SDL_SCANCODE_F2: Key.F2,
        sdl2.SDL_SCANCODE_F3: Key.F3,
        sdl2.SDL_SCANCODE_F4: Key.F4,
        sdl2.SDL_SCANCODE_F5: Key.F5,
        sdl2.SDL_SCANCODE_F6: Key.F6,
        sdl2.SDL_SCANCODE_F7: Key.F7,
        sdl2.SDL_SCANCODE_F8: Key.F8,
        sdl2.SDL_SCANCODE_F9: Key.F9,
        sdl2.SDL_SCANCODE_F10: Key.F10,
        sdl2.SDL_SCANCODE_F11: Key.F11,
        sdl2.SDL_SCANCODE_F12: Key.F12,
    }

except ImportError:
    logger.error("sdl2 is not installed. Set ROBOIMPL_SCREEN_DISPLAYER_BACKEND='tkinter' or "
                 "pip install pysdl2 pysdl2-dll")

from .screen_displayer_utils import DisplayerBackend, Key

class ScreenDisplayerSDL2(DisplayerBackend):
    """SDL2-based screen displayer with hardware-accelerated rendering."""
    def __init__(self):
        self.window = None
        self.renderer = None
        self.texture = None
        self._texture_size: tuple[int, int] = (0, 0)  # (height, width)

    @overrides
    def initialize_window(self, height: int, width: int, title: str):
        assert self.window is None, "cannot call twice"

        # Initialize SDL2 video subsystem
        sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO)

        # Create window (resizable)
        self.window = sdl2.SDL_CreateWindow(
            title.encode("utf-8"),
            sdl2.SDL_WINDOWPOS_CENTERED,
            sdl2.SDL_WINDOWPOS_CENTERED,
            width, height,
            sdl2.SDL_WINDOW_SHOWN | sdl2.SDL_WINDOW_RESIZABLE
        )

        # Create hardware-accelerated renderer
        self.renderer = sdl2.SDL_CreateRenderer(
            self.window, -1, sdl2.SDL_RENDERER_ACCELERATED | sdl2.SDL_RENDERER_PRESENTVSYNC)

        # Create texture for streaming RGB frames
        self._create_texture(height, width)

    def _create_texture(self, height: int, width: int):
        """Create/recreate texture when frame size changes."""
        if self.texture is not None:
            sdl2.SDL_DestroyTexture(self.texture)

        # SDL_PIXELFORMAT_RGB24 for RGB numpy arrays
        self.texture = sdl2.SDL_CreateTexture(
            self.renderer,
            sdl2.SDL_PIXELFORMAT_RGB24,
            sdl2.SDL_TEXTUREACCESS_STREAMING,
            width, height
        )
        self._texture_size = (height, width)

    @overrides
    def get_current_size(self) -> tuple[int, int]:
        w, h = ctypes.c_int(), ctypes.c_int()
        sdl2.SDL_GetWindowSize(self.window, ctypes.byref(w), ctypes.byref(h))
        return h.value, w.value  # return (height, width)

    @overrides
    def poll_events(self):
        """Pump SDL event loop. MUST be called regularly for window/keyboard to work."""
        event = sdl2.SDL_Event()
        while sdl2.SDL_PollEvent(ctypes.byref(event)):
            if event.type == sdl2.SDL_QUIT:
                pass

    @overrides
    def get_pressed_keys(self) -> set[Key]:
        num_keys = ctypes.c_int()
        # Returns pointer to internal SDL key state array (updated by SDL_PollEvent)
        state_ptr = sdl2.SDL_GetKeyboardState(ctypes.byref(num_keys))

        # state_ptr is Uint8* - each index is a scancode, value 1 = pressed
        pressed = set()
        for scancode, key in _SDL2_SCANCODE_MAP.items():
            if state_ptr[scancode]:
                pressed.add(key)

        return pressed

    @overrides
    def update_frame(self, frame: np.ndarray):
        """Update texture with new RGB frame and render."""
        h, w = frame.shape[:2]

        # Recreate texture if frame size changed
        if (h, w) != self._texture_size:
            self._create_texture(h, w)

        # Ensure contiguous C-order array
        if not frame.flags["C_CONTIGUOUS"]:
            frame = np.ascontiguousarray(frame)

        # Update texture with pixel data
        # pitch = bytes per row = width * 3 (RGB)
        sdl2.SDL_UpdateTexture(
            self.texture,
            None,  # update entire texture
            frame.ctypes.data_as(ctypes.c_void_p),
            w * 3  # pitch
        )

        # Clear, copy texture to renderer, present
        sdl2.SDL_RenderClear(self.renderer)
        sdl2.SDL_RenderCopy(self.renderer, self.texture, None, None)
        sdl2.SDL_RenderPresent(self.renderer)

    @overrides
    def close_window(self):
        if self.texture:
            sdl2.SDL_DestroyTexture(self.texture)
        if self.renderer:
            sdl2.SDL_DestroyRenderer(self.renderer)
        if self.window:
            sdl2.SDL_DestroyWindow(self.window)
        sdl2.SDL_Quit()
