# test_i_Robot_replay_from_logs_ReplayDataProducer_ActionsQueue

**Created:** 2026-03-13 | **Closed:** 2026-03-15 | **GitLab:** #15

## Problem

Needed programmatic "maze" test using BasicEnv. Two runs: first run stores logs, second run replays from logs and asserts actions are identical.

## Resolution

Test implemented with ReplayDataProducer + ReplayActionsQueue.
