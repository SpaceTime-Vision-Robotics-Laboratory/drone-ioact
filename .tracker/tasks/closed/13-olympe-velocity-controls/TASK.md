# Olympe: use velocity based controls (+timer) for both gimbal and piloting

**Status:** closed | **Created:** 2026-03-10 | **Closed:** 2026-03-10 | **GitLab:** #13

## Problem

Mixed high-level API (drone.piloting(), gimbal.set_target, TakeOff().wait()) was confusing. Needed unified velocity command queue with (intensity, duration) interface.

## Resolution

Thin scheduler: takes (command_type, axes_values, duration) off queue, sends NON_ACK command (PCMD or gimbal velocity), sends zero/stop after duration. Lifecycle commands (TakeOff, Landing, Emergency) kept separate.
