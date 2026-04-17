# Extract KeyboardController from ScreenDisplayer

**Status:** closed | **Created:** 2026-04-14 | **Closed:** 2026-04-14 | **Priority:** 2

## Problem

Keyboard input was serialized with frame rendering inside ScreenDisplayer, causing action bunching and visible linger on key release. Fix: separate KeyboardController that runs on its own 30Hz timer, decoupled from frame rate.

## What's done

- **KeyboardController** exists in `roboimpl/controllers/keyboard_controller.py`
- **ScreenDisplayer** cleaned up — no `keyboard_fn`, no `Key`, no key event handling. Display-only.
- **screen_displayer_utils.py** cleaned up — no `Key`, no `make_keyboard_listener`, no `key_event` on `DisplayerBackend`
- **cv2 backend** clean — no pynput, `poll_events()` just pumps `cv2.waitKey(1)`
- **tkinter backend** clean — `poll_events()` just calls `root.update()`
- **robosim client** migrated to `ScreenDisplayer` + `KeyboardController`
- **`__init__.py`** exports `KeyboardController` and `Key`

## Design: 30Hz timer, not data-gated

`run()` polls keyboard at fixed 30Hz via `time.sleep`, not on DataChannel events. This is intentional — keyboard is an input device, not a data consumer. The simulator may lag but commands should still flow at a steady rate. `data_ts=None` on all keyboard actions (no provenance — keys aren't triggered by perception).

## Review bugs (all fixed)

- `KeyboardFn` type alias matched new signature `(keys) -> actions`
- Default `_keyboard_fn` no longer clears the pressed set
- `PYNPUT` guard added to `__init__`
- `robot.py` `name` param no longer silently ignored
- `INITIAL_DATA_MAX_DURATION_S` deduplicated
- `hello-cartpole` `screen_frame_callback` restored
- All 8 examples migrated

## Keyboard backend constraint

KeyboardController takes a keyboard backend with interface `get_pressed() -> set[Key]`. Two backends:

- **pynput** — global OS-level hooks, works with any display backend (cv2, tkinter, SDL2). Not window-scoped.
- **SDL2** — `SDL_GetKeyboardState`, window-scoped. **Requires SDL event loop**, which only exists when ScreenDisplayer also uses the SDL2 display backend. Cannot be used with cv2/tkinter display.

Valid combinations:

| Display | Keyboard | Works? | Notes |
|---------|----------|--------|-------|
| cv2 | pynput | Yes | current setup |
| tkinter | pynput | Yes | current setup |
| SDL2 | SDL2 | Yes | natural pairing, window-scoped |
| SDL2 | pynput | Yes | works but loses window-scoping |
| cv2/tkinter | SDL2 | **No** | no SDL event loop to pump `SDL_GetKeyboardState` |

This is not an incompatibility between controllers — it's a runtime dependency of the SDL2 keyboard backend on an SDL2 event loop. Pynput is the universal fallback. Assert at construction time if SDL2 keyboard is requested without SDL2 display.

## Done when

- `KeyboardController` exists as a standalone controller in `roboimpl/controllers/`
- ScreenDisplayer has no keyboard logic
- All examples migrated
- Tests pass
