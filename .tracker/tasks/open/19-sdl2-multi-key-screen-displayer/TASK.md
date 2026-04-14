# SDL2 backend for ScreenDisplayer + multi-key support

**Status:** open | **Created:** 2026-04-14 | **Priority:** 1

## Problem

Cannot press multiple keys simultaneously. Current backends:
- **tkinter**: has press/release events (multi-key possible) but slow for real-time display
- **cv2**: fast display but `waitKey` returns one key per call (no multi-key, no press/release)

Need: fast display + multi-key tracking + window-scoped (two clients = two windows = independent control).

## Solution

### 1. SDL2 backend via ctypes (no pip dependency)

SDL2 is a system library on Linux. Use ctypes to bind ~15 functions:
- `SDL_Init`, `SDL_Quit`
- `SDL_CreateWindow`, `SDL_DestroyWindow`
- `SDL_CreateRenderer`, `SDL_CreateTexture`, `SDL_UpdateTexture`, `SDL_RenderCopy`, `SDL_RenderPresent`
- `SDL_PollEvent` (gives `SDL_KEYDOWN`, `SDL_KEYUP` with scancodes)
- `SDL_GetKeyboardState` (multi-key pressed array, window-scoped)

~100-150 lines of wrapper code. Zero dead code. Fast (hardware-accelerated). Multi-key. Window-scoped. Works on a thread on Linux.

### 2. Refactor key_to_action to pressed-set callback

Replace `key_to_action: dict[Key, Action]` with:
```
keyboard_fn(pressed_keys: set[Key], data: dict) -> Action | list[Action] | None
```

Same signature works for all backends:
- **tkinter**: maintains pressed set from press/release events -> multi-key works
- **cv2**: pressed set has at most 1 key per poll (known limitation, not a bug)
- **SDL2**: full multi-key via `SDL_GetKeyboardState`

User code never knows which backend — just gets a pressed set and returns actions.

### 3. Core principle: minimize dependencies

SDL2 via ctypes means zero pip dependencies. The library (`libSDL2`) is pre-installed on virtually every Linux desktop. Aligns with project principle of near-zero dead code.

## Context

- See `client2.py` in uav-trajectories-raylib for the pynput-based pattern that inspired this (global capture, not window-scoped — insufficient for multi-client)
- GitLab #1 originally wanted to get rid of opencv; #18 added the Key enum mapper across backends
- This supersedes both: SDL2 gives fast display + proper keyboard in one backend

## Done when

- SDL2 backend exists as `ScreenDisplayerSDL2` implementing `DisplayerBackend`
- `ScreenDisplayer` accepts `keyboard_fn(pressed: set[Key], data) -> Action | list[Action] | None` instead of `key_to_action` dict
- tkinter backend updated to maintain `pressed_keys` set
- cv2 backend unchanged (single-key limitation documented)
- Two simultaneous clients can be controlled independently via window focus
