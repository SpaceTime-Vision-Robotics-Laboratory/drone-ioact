# Remove cv2/pynput, tkinter internal keyboard

**Status:** open | **Created:** 2026-04-17 | **Priority:** 3

**Depends on:** #19 (SDL2 backend working first)

**Design decision:** KeyboardController takes explicit `DisplayerBackend` reference. Keeps controllers separate (screen is screen), but shares the window resource for keyboard state.

## Problem

After SDL2 is implemented (#19), we have redundant dependencies:
- `opencv-python` (~80MB) — only used for display (now SDL2) and image ops (use PIL)
- `pynput` — global keyboard hooks, not window-scoped. SDL2 replaces this.

tkinter backend needs its own keyboard handling (currently relies on pynput).

## Plan

### 1. Add keyboard methods to DisplayerBackend ABC

```python
class DisplayerBackend(ABC):
    # ... existing 5 methods ...
    
    @abstractmethod
    def setup_keyboard(self) -> None:
        """Set up keyboard capture. Called once after initialize_window."""
    
    @abstractmethod
    def get_pressed_keys(self) -> set[Key]:
        """Return currently pressed keys. Empty if window not focused."""
```

### 2. Implement in ScreenDisplayerSDL2

```python
def setup_keyboard(self) -> None:
    pass  # SDL2 needs no setup, SDL_GetKeyboardState works after SDL_Init

def get_pressed_keys(self) -> set[Key]:
    return get_pressed_keys_sdl2()  # from sdl2_keyboard.py
```

### 3. Implement in ScreenDisplayerTkinter

Single-key only (tkinter limitation). Track last pressed key:

```python
def __init__(self):
    # ...
    self._pressed_key: Key | None = None

def setup_keyboard(self) -> None:
    self.canvas.bind("<KeyPress>", self._on_key_press)
    self.canvas.bind("<KeyRelease>", self._on_key_release)

def _on_key_press(self, event):
    if (key := _TKINTER_KEY_MAP.get(event.keysym)) is not None:
        self._pressed_key = key

def _on_key_release(self, event):
    if _TKINTER_KEY_MAP.get(event.keysym) == self._pressed_key:
        self._pressed_key = None

def get_pressed_keys(self) -> set[Key]:
    return {self._pressed_key} if self._pressed_key else set()
```

### 4. Update KeyboardController

```python
class KeyboardController(BaseController):
    def __init__(self, data_channel, actions_queue, backend: DisplayerBackend, 
                 keyboard_fn: KeyboardFn = None, key_to_action: dict = None):
        assert backend is not None, "KeyboardController requires a DisplayerBackend"
        self.backend = backend
        # ...

    def run(self):
        self.backend.setup_keyboard()
        self.data_channel_event.wait(INITIAL_DATA_MAX_DURATION_S)
        while self.data_channel.has_data():
            pressed = self.backend.get_pressed_keys()
            actions = self.keyboard_fn(pressed)
            # ...
```

### 5. Delete cv2 backend and pynput usage

- Delete `screen_displayer_cv2.py`
- Remove pynput from `keyboard_controller.py`
- Move `image_resize` cv2 calls to PIL in `roboimpl/utils/`
- Update `requirements-extra.txt`: remove `opencv-python`, `pynput`

### 6. Tkinter key map

```python
_TKINTER_KEY_MAP: dict[str, Key] = {
    **{chr(c): getattr(Key, chr(c)) for c in range(ord("a"), ord("z") + 1)},
    "Left": Key.Left, "Right": Key.Right, "Up": Key.Up, "Down": Key.Down,
    "Escape": Key.Esc, "Return": Key.Enter, "space": Key.Space,
    "Prior": Key.PageUp, "Next": Key.PageDown,
    "comma": Key.Comma, "period": Key.Period,
    "F1": Key.F1, "F2": Key.F2, # ... etc
}
```

## Done when

- `DisplayerBackend` ABC has `setup_keyboard()` and `get_pressed_keys()` methods
- `ScreenDisplayerSDL2` implements keyboard methods (multi-key)
- `ScreenDisplayerTkinter` implements keyboard methods (single-key)
- `KeyboardController` takes `DisplayerBackend` reference, uses its keyboard methods
- `screen_displayer_cv2.py` deleted
- pynput removed from `keyboard_controller.py`
- `opencv-python` and `pynput` removed from requirements
- All examples work with both backends
