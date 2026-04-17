"""screen_displayer_sdl2.py - SDL2 backend for ScreenDisplayer"""
import ctypes
import numpy as np
from overrides import overrides

from roboimpl.utils import logger

try:
    import sdl2
except ImportError:
    logger.error("sdl2 is not installed. Set ROBOIMPL_SCREEN_DISPLAYER_BACKEND='tkinter' or "
                 "pip install pysdl2 pysdl2-dll")

from .screen_displayer_utils import DisplayerBackend

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
            self.window, -1,
            sdl2.SDL_RENDERER_ACCELERATED | sdl2.SDL_RENDERER_PRESENTVSYNC
        )

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
