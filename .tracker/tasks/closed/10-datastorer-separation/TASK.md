# Separation of concerns in DataStorer (singleton) vs. DataChannel

**Status:** closed | **Created:** 2026-02-12 | **Closed:** 2026-02-14 | **GitLab:** #10

## Problem

DataStorer should be a singleton. `DataChannel.put()` and `ActionsQueue.put()` should call `DataStorer.get_instance().push()`. Should work even without a DataStorer (no-op when instance is None).

## Resolution

DataStorer is module-level singleton. `get_instance()` returns None when `ROBOBASE_STORE_LOGS != "2"`. Zero overhead when disabled.
