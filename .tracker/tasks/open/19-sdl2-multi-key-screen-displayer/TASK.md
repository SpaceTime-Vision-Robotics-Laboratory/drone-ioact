# SDL2 backend for ScreenDisplayer + KeyboardController

**Status:** open | **Created:** 2026-04-14 | **Priority:** 2

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

### 2. SDL2 keyboard backend in KeyboardController

`SDL_GetKeyboardState` returns a C pointer to SDL's internal key state array. Updated automatically when the display thread calls `SDL_PollEvent`. KeyboardController just reads it — no events, no callbacks, no listener thread.

```python
state = sdl2.SDL_GetKeyboardState(None)
# state[SDL_SCANCODE_W] == 1 means W is held
```

Build `_SDL2_SCANCODE_MAP: dict[int, Key]` analogous to current `_PYNPUT_KEYCODE_MAP`. Poll:
```python
def get_pressed(state, scancode_map) -> set[Key]:
    return {key for scancode, key in scancode_map.items() if state[scancode]}
```

**Constraint:** SDL2 keyboard backend requires ScreenDisplayerSDL2 running (it pumps events). Assert at construction time. pynput remains fallback for headless / non-SDL2 setups.

### 3. Drop cv2 backend

cv2 (`opencv-python`) is 80MB+ for `imshow` + `waitKey`. Move remaining cv2 usage (`image_resize`, `cvtColor`) to PIL (already a dependency). Delete `screen_displayer_cv2.py`.

### 4. Keep tkinter backend as fallback

tkinter is stdlib — zero cost. Slow for real-time, but works everywhere without any install. Good fallback when `pysdl2-dll` has issues on an exotic platform.

### 5. Drop pynput

Once SDL2 keyboard backend works, pynput is only needed for headless / non-SDL2 edge cases. If those don't exist in practice, drop pynput too.

Final state: two display backends (sdl2 primary, tkinter fallback), one keyboard backend (sdl2, pynput fallback if needed).

## Dependencies

- `pysdl2` — thin ctypes bindings to SDL2 (pip, pure Python)
- `pysdl2-dll` — bundles SDL2 shared library (pip, ~2MB, Linux/macOS/Windows)
- No system package install needed. Pure pip.

Replaces: `opencv-python` (~80MB), `pynput`, tkinter+Pillow for display.

## Done when

- `ScreenDisplayerSDL2` implements `DisplayerBackend` via `pysdl2`
- `KeyboardController` supports SDL2 keyboard backend via `SDL_GetKeyboardState`
- cv2 backend deleted, remaining cv2 usage moved to PIL
- tkinter backend kept as fallback
- Default backend is sdl2
- Selectable via `ROBOIMPL_SCREEN_DISPLAYER_BACKEND=sdl2|tkinter`
- All examples work with sdl2 backend
- Two simultaneous clients controllable independently via window focus
