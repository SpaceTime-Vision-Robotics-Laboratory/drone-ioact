# SDL2 backend for ScreenDisplayer

**Status:** open | **Created:** 2026-04-14 | **Priority:** 2

## Problem

- **tkinter**: has press/release events but auto-repeat quirks on Linux, slow for real-time display
- **cv2**: fast display but `waitKey` returns one key per call (no multi-key, no press/release)

Need: fast display + multi-key tracking + window-scoped (two clients = two windows = independent control).

## What's done

### Multi-key keyboard refactor (complete, branch `updates-from-robosim`)

- `key_to_action` removed entirely — replaced by `keyboard_fn: Callable[[set[Key]], list[Action]]`
- `_PYNPUT_KEYCODE_MAP` and `make_keyboard_listener()` in `screen_displayer_utils.py` (shared by tkinter + cv2)
- Both backends use pynput for keyboard, `DisplayerBackend` ABC has `key_event` property
- `ScreenDisplayer.run()`: `poll_events()` pumps UI every iteration, `keyboard_fn` gated on data frames OR key events
- `ControllerFn` type returns `list[Action]`, `Controller.run()` iterates directly
- All examples migrated (robosim, video, olympe, gym, maze, hello-world)
- All tests pass (35/35)

### Architecture

```
pynput listener thread          ScreenDisplayer.run() loop
  _on_press → pressed.add()      poll_events() every iter (pumps UI)
  _on_release → pressed.discard()  keyboard_fn(pressed) on data OR key events
  event.set()                       → actions_queue.put()
```

## Remaining

### SDL2 backend

New `screen_displayer_sdl2.py` implementing `DisplayerBackend`, using `pysdl2` (thin ctypes wrapper over system `libSDL2`).

Key SDL2 features:
- `SDL_CreateWindow` / `SDL_CreateRenderer` / `SDL_CreateTexture` — hardware-accelerated display
- `SDL_PollEvent` — pump event loop (window resize, close, etc.)
- `SDL_GetKeyboardState` — snapshot of all held keys → map to `Key` enum → `set[Key]`
- Events include `windowID` — window-scoped input for free (no pynput needed)

Add `"sdl2"` to the backend dict in `screen_displayer.py`, selectable via `ROBOIMPL_SCREEN_DISPLAYER_BACKEND=sdl2`.

## Dependencies

- System: `libSDL2` (apt/brew/system package)
- Python: `pysdl2` (pip, pure Python ctypes wrapper)

## Done when

- `ScreenDisplayerSDL2` exists implementing `DisplayerBackend`
- `poll_events()` returns `set[Key]` via `SDL_GetKeyboardState` (no pynput needed for SDL2)
- Selectable via `ROBOIMPL_SCREEN_DISPLAYER_BACKEND=sdl2`
- Two simultaneous clients can be controlled independently via window focus
