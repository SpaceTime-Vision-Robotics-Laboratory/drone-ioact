# Add edge-triggered key detection to DisplayerBackend

**Status:** closed (won't fix) | **Created:** 2026-04-22 | **Closed:** 2026-04-22

## Resolution

Wrong abstraction. Producer-side edge detection breaks when producer (`poll_events()` ~10ms) and consumer (e.g. TrajectoryController ~33ms) run at different frequencies — `_just_pressed` gets cleared before consumer reads it.

**Correct approach:** Consumer-side edge detection. Each consumer tracks their own `prev_pressed` and computes `pressed - prev_pressed`. No backend changes needed.

## Problem

`get_pressed_keys()` returns all currently held keys (level-triggered). For one-shot actions (e.g., "add via point"), this causes multiple firings if the key is held across poll cycles.

## Solution

Add parameter: `get_pressed_keys(just_pressed: bool = False)`

- `False` (default): return all currently held keys (existing behavior, for WASD movement)
- `True`: return only keys that transitioned down since last `poll_events()` call

## Implementation

In `ScreenDisplayerSDL2.poll_events()`:
```python
def poll_events(self):
    # ... existing SDL_PollEvent loop ...
    
    # After polling, compute edge-triggered set
    pressed = self._read_keyboard_state()
    self._just_pressed = pressed - self._pressed
    self._pressed = pressed

def get_pressed_keys(self, just_pressed: bool = False) -> set[Key]:
    return self._just_pressed.copy() if just_pressed else self._pressed.copy()
```

State is computed once per `poll_events()` call, so multiple consumers calling `get_pressed_keys(True)` get the same set for that frame.

## Files

- `roboimpl/controllers/screen_displayer/screen_displayer_utils.py` - update `DisplayerBackend` base class signature
- `roboimpl/controllers/screen_displayer/screen_displayer_sdl2.py` - implement for SDL2
- `roboimpl/controllers/screen_displayer/screen_displayer_tkinter.py` - implement for tkinter

Both backends must implement the same edge-detection logic to keep behavior consistent.
