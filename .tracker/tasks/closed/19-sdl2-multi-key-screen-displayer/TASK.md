# SDL2 backend for ScreenDisplayer + KeyboardController

**Created:** 2026-04-14 | **Priority:** 2

**Phase 1:** Add SDL2 alongside existing backends (cv2, tkinter, pynput).  
**Phase 2:** Remove cv2/pynput, tkinter internal keyboard → Task #25

## Problem

Current backends (cv2, tkinter) have limitations for real-time robotics display:
- **cv2**: 80MB+ pip dependency, `waitKey` is single-key only, no press/release
- **tkinter**: slow for real-time display
- Both rely on **pynput** for multi-key input — global OS hooks, not window-scoped. Two windows = same key state.

SDL2 solves all three: hardware-accelerated display + window-scoped keyboard state + ~2MB pip install.

## Context: keyboard/display split (done, task #22)

ScreenDisplayer and KeyboardController are now separate controllers on separate threads:
- **ScreenDisplayer** — renders frames, driven by data events. Backend implements `DisplayerBackend` ABC (5 methods).
- **KeyboardController** — polls `set[Key]` at 30Hz, calls `keyboard_fn`. Currently uses pynput.

SDL2 touches both controllers independently.

## Plan

### 1. ScreenDisplayerSDL2 — new `DisplayerBackend`

New `screen_displayer_sdl2.py` using `pysdl2`. Implements:
- `initialize_window` → `SDL_CreateWindow` + `SDL_CreateRenderer` + `SDL_CreateTexture`
- `poll_events` → `SDL_PollEvent` (pumps event loop for window resize, close, etc.)
- `get_current_size` → `SDL_GetWindowSize`
- `update_frame` → `SDL_UpdateTexture` + `SDL_RenderCopy` + `SDL_RenderPresent`
- `close_window` → `SDL_DestroyWindow`

Add `"sdl2"` to backend dict in `screen_displayer.py`. Make it the default.

### 2. Keyboard handling per backend

**SDL2 backend:** `SDL_GetKeyboardState` returns a C pointer to SDL's internal key state array. Updated automatically when the display thread calls `SDL_PollEvent`. KeyboardController polls it — no events, no callbacks, no listener thread. Multi-key support.

```python
state = sdl2.SDL_GetKeyboardState(None)
# state[SDL_SCANCODE_W] == 1 means W is held
```

Build `_SDL2_SCANCODE_MAP: dict[int, Key]` analogous to current `_PYNPUT_KEYCODE_MAP`. Poll:
```python
def get_pressed(state, scancode_map) -> set[Key]:
    return {key for scancode, key in scancode_map.items() if state[scancode]}
```

**Constraint:** SDL2 keyboard requires ScreenDisplayerSDL2 running (it pumps events). Assert at construction time.

**tkinter backend:** Uses `bind("<KeyPress>")` / `bind("<KeyRelease>")` on the canvas. Single-key only (tkinter limitation). No external dependencies.

### 3. Drop cv2 backend + pynput

- cv2 (`opencv-python`): 80MB+ for `imshow` + `waitKey`. Delete `screen_displayer_cv2.py`. Move remaining cv2 usage (`image_resize`, `cvtColor`) to PIL.
- pynput: No longer needed. SDL2 has window-scoped multi-key, tkinter uses its own single-key handling.

### 4. tkinter backend: internal keyboard only

tkinter uses its own `bind("<KeyPress>")` / `bind("<KeyRelease>")` — single-key only (no simultaneous keys), but zero dependencies. Acceptable tradeoff for the fallback option.

### Final state (after Phase 2, Task #25)

Two backends, user chooses one:
| Backend | Display | Keyboard | Deps |
|---------|---------|----------|------|
| **sdl2** (default) | hardware-accelerated, fast | multi-key, window-scoped | pysdl2 + pysdl2-dll (~2MB) |
| **tkinter** (fallback) | slow for real-time | single-key only | stdlib (0MB) |

No opencv. No pynput.

## Dependencies

**Added (Phase 1):**
- `pysdl2` — thin ctypes bindings to SDL2 (pip, pure Python, ~50KB)
- `pysdl2-dll` — bundles SDL2 shared library (pip, ~2MB, Linux/macOS/Windows)

**Removed (Phase 2, Task #25):**
- `opencv-python` (~80MB)
- `pynput`

## Done when (Phase 1 only)

- `ScreenDisplayerSDL2` implements `DisplayerBackend` via `pysdl2`
- SDL2 keyboard via `SDL_GetKeyboardState` (multi-key, window-scoped)
- `"sdl2"` added to backend dict in `screen_displayer.py`
- Selectable via `ROBOIMPL_SCREEN_DISPLAYER_BACKEND=sdl2|cv2|tkinter`
- All examples work with sdl2 backend
- Two SDL2 windows controllable independently via window focus
- Existing backends (cv2, tkinter, pynput) unchanged — removal is Task #25

---

## Code Reference

### Install

```bash
pip install pysdl2 pysdl2-dll
# pysdl2: ~50KB, pure Python ctypes bindings
# pysdl2-dll: ~2MB, bundles SDL2.so/dll for Linux/macOS/Windows
```

### 1. ScreenDisplayerSDL2 (DisplayerBackend implementation)

```python
"""screen_displayer_sdl2.py - SDL2 backend for ScreenDisplayer"""
import ctypes
import numpy as np
from overrides import overrides

import sdl2
import sdl2.ext

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
                # User closed window - could set a flag here
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
        sdl2.SDL_RenderClear(renderer)
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
```

### 2. SDL2 Keyboard State (Window-Scoped)

```python
"""sdl2_keyboard.py - SDL2 keyboard state reader"""
import ctypes
import sdl2

from roboimpl.controllers.keyboard_controller import Key

# Map SDL2 scancodes to robobase Key enum
# Scancodes are physical key positions (layout-independent)
_SDL2_SCANCODE_MAP: dict[int, Key] = {
    # Letters a-z
    **{sdl2.SDL_SCANCODE_A + i: getattr(Key, chr(ord("a") + i)) 
       for i in range(26)},
    
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

def get_pressed_keys_sdl2() -> set[Key]:
    """
    Returns set of currently pressed keys (window-scoped).
    
    IMPORTANT: Only works when SDL window has focus.
    Requires poll_events() to be called regularly by the display thread.
    """
    num_keys = ctypes.c_int()
    # Returns pointer to internal SDL key state array (updated by SDL_PollEvent)
    state_ptr = sdl2.SDL_GetKeyboardState(ctypes.byref(num_keys))
    
    # state_ptr is Uint8* - each index is a scancode, value 1 = pressed
    pressed = set()
    for scancode, key in _SDL2_SCANCODE_MAP.items():
        if state_ptr[scancode]:
            pressed.add(key)
    
    return pressed
```

### 3. Standalone Test Script

```python
#!/usr/bin/env python3
"""test_sdl2_standalone.py - Verify SDL2 display + keyboard works"""
import ctypes
import time
import numpy as np
import sdl2

def main():
    # Init
    sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO)
    
    window = sdl2.SDL_CreateWindow(
        b"SDL2 Test - Press keys, ESC to quit",
        sdl2.SDL_WINDOWPOS_CENTERED, sdl2.SDL_WINDOWPOS_CENTERED,
        640, 480,
        sdl2.SDL_WINDOW_SHOWN | sdl2.SDL_WINDOW_RESIZABLE
    )
    renderer = sdl2.SDL_CreateRenderer(window, -1, sdl2.SDL_RENDERER_ACCELERATED)
    texture = sdl2.SDL_CreateTexture(
        renderer, sdl2.SDL_PIXELFORMAT_RGB24,
        sdl2.SDL_TEXTUREACCESS_STREAMING, 640, 480
    )
    
    # Get keyboard state pointer
    num_keys = ctypes.c_int()
    key_state = sdl2.SDL_GetKeyboardState(ctypes.byref(num_keys))
    
    running = True
    frame_count = 0
    
    while running:
        # Poll events (REQUIRED for keyboard state to update)
        event = sdl2.SDL_Event()
        while sdl2.SDL_PollEvent(ctypes.byref(event)):
            if event.type == sdl2.SDL_QUIT:
                running = False
        
        # Check ESC
        if key_state[sdl2.SDL_SCANCODE_ESCAPE]:
            running = False
        
        # Print pressed keys
        pressed = []
        for scancode in range(min(num_keys.value, 256)):
            if key_state[scancode]:
                name = sdl2.SDL_GetScancodeName(scancode)
                if name:
                    pressed.append(name.decode())
        if pressed:
            print(f"Pressed: {pressed}")
        
        # Generate test frame (moving gradient)
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        x = (frame_count * 5) % 640
        frame[:, x:x+50, 1] = 255  # green bar
        frame_count += 1
        
        # Update texture and render
        sdl2.SDL_UpdateTexture(texture, None, frame.ctypes.data_as(ctypes.c_void_p), 640 * 3)
        sdl2.SDL_RenderClear(renderer)
        sdl2.SDL_RenderCopy(renderer, texture, None, None)
        sdl2.SDL_RenderPresent(renderer)
        
        time.sleep(1/60)  # ~60 FPS
    
    # Cleanup
    sdl2.SDL_DestroyTexture(texture)
    sdl2.SDL_DestroyRenderer(renderer)
    sdl2.SDL_DestroyWindow(window)
    sdl2.SDL_Quit()
    print("Clean exit")

if __name__ == "__main__":
    main()
```

### 4. Architecture: Display Thread Pumps Events, Keyboard Thread Reads State

```
┌─────────────────────┐     ┌──────────────────────┐
│ ScreenDisplayerSDL2 │     │  KeyboardController  │
│ (display thread)    │     │  (keyboard thread)   │
│                     │     │                      │
│ poll_events() ──────┼──→  SDL internal state ←──┤ get_pressed_keys_sdl2()
│ update_frame()      │     (key state array)     │
└─────────────────────┘     └──────────────────────┘
```

**Why SDL2 keyboard is window-scoped:**
```python
# pynput (current) - GLOBAL hooks
listener = keyboard.Listener(on_press=..., on_release=...)
listener.start()  # captures ALL keys on the OS, any window

# SDL2 - window-scoped
state = sdl2.SDL_GetKeyboardState(None)
# Only returns keys pressed when THIS SDL window has focus
# Two SDL windows = two independent key states
```

**Thread safety:** `SDL_GetKeyboardState` returns a pointer to SDL's internal array. SDL guarantees this is safe to read from any thread as long as events are pumped from one thread. No locking needed.

### 5. Scancode Reference

| Key | SDL2 Scancode | Value |
|-----|--------------|-------|
| A-Z | `SDL_SCANCODE_A` + offset | 4-29 |
| 0-9 | `SDL_SCANCODE_0` + offset | 30-39 |
| Left | `SDL_SCANCODE_LEFT` | 80 |
| Right | `SDL_SCANCODE_RIGHT` | 79 |
| Up | `SDL_SCANCODE_UP` | 82 |
| Down | `SDL_SCANCODE_DOWN` | 81 |
| Space | `SDL_SCANCODE_SPACE` | 44 |
| Enter | `SDL_SCANCODE_RETURN` | 40 |
| Escape | `SDL_SCANCODE_ESCAPE` | 41 |
| F1-F12 | `SDL_SCANCODE_F1` + offset | 58-69 |

### 6. KeyboardController Integration

```python
# At top, alongside pynput imports:
try:
    import sdl2
    SDL2 = True
    from .sdl2_keyboard import get_pressed_keys_sdl2, _SDL2_SCANCODE_MAP
except ImportError:
    SDL2 = False

# In KeyboardController.__init__:
def __init__(self, ..., backend: str = "auto"):
    self.backend = backend  # "sdl2", "pynput", or "auto"
    # ...

# In KeyboardController.run():
def run(self):
    if self.backend == "sdl2" or (self.backend == "auto" and SDL2):
        # SDL2 mode - just poll the state array
        self.data_channel_event.wait(INITIAL_DATA_MAX_DURATION_S)
        prev = datetime.now()
        while self.data_channel.has_data():
            pressed = get_pressed_keys_sdl2()  # no listener needed
            actions = self.keyboard_fn(pressed)
            for action in actions:
                self.actions_queue.put(action, data_ts=None)
            # ... sleep logic
    else:
        # pynput fallback (current code)
        self.pressed = make_keyboard_listener()
        # ...
```
