# Refactor ScreenDisplayer: key_to_action dict -> keyboard_fn callback

**Status:** closed | **Created:** 2026-04-14 | **Closed:** 2026-04-14 | **Priority:** 1

## Problem

`ScreenDisplayer` used `key_to_action: dict[Key, Action]` — one key maps to one action. Cannot express multi-key combinations (e.g., Up+Left for diagonal movement).

## What was done

- `key_to_action` removed entirely from codebase (no references left)
- `keyboard_fn: Callable[[set[Key]], Action | list[Action]]` added (default: no-op that logs)
- `ScreenDisplayer.run()` refactored: `backend.poll_events()` pumps UI every iteration, `keyboard_fn` gated on data frames OR key events (via pynput `threading.Event`)
- `_PYNPUT_KEYCODE_MAP` and `make_keyboard_listener()` in `screen_displayer_utils.py` (shared by tkinter + cv2)
- Both backends use pynput for keyboard, `DisplayerBackend` ABC has `key_event` property
- `ControllerFn` type alias updated to return `list[Action]`
- `Controller.run()` iterates directly (no normalize step)
- All controller_fns across examples and tests return `list[Action]`
- All examples migrated: robosim, video, olympe, gym, maze, hello-world
- All tests pass (35/35)
