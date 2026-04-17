# How do we allow multiple "lanes" (multiple data channels?)

**Created:** 2026-01-20 | **Closed:** 2026-02-04 | **GitLab:** #4

## Resolution

DataProducers2Channels runs one worker thread per channel. Each channel has its own producer subset.
