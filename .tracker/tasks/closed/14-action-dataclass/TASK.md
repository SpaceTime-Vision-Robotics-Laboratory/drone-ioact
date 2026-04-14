# Action should be a dataclass and nothing else

**Status:** closed | **Created:** 2026-03-11 | **Closed:** 2026-03-12 | **GitLab:** #14

## Problem

- Caused issues when storing as npz (loads as ndarray, not Action)
- Caused issues when storing actions in set/list (hash != eq)

## Resolution

Action is now a frozen `@dataclass(name, parameters)` with full equality.
