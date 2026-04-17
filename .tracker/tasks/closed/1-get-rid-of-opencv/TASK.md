# Get rid of opencv

**Created:** 2025-11-16 | **Closed:** 2025-11-17 | **GitLab:** #1

## Problem

- opencv requires headless crap in CI
- for display: raylib or something else
- for saving/conversion: PIL
- pynput requires X server also failing in CI

## Resolution

Both still used but issue closed — opencv kept as optional backend, pynput dropped.
