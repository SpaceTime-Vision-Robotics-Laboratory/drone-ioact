# DataWriter for ActionsQueue (+data channel ts for linking)

**Created:** 2026-02-06 | **Closed:** 2026-02-14 | **GitLab:** #7

## Resolution

`ActionsQueue.put(action, data_ts)` stores provenance timestamp linking actions to the perception data that triggered them. DataStorer handles persistence.
