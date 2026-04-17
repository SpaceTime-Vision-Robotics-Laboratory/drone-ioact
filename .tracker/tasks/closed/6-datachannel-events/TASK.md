# Add events to DataChannel and make controllers wait for it w/o busy waiting

**Created:** 2026-02-06 | **Closed:** 2026-02-07 | **GitLab:** #6

## Problem

Controllers busy-waited with `time.sleep()` loop polling `has_data()`.

## Resolution

DataChannel uses `threading.Event` pub/sub. Controllers call `wait_and_clear(event)`.
