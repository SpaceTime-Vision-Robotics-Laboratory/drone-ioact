# Multi-Channel caching

**Created:** 2026-02-15 | **Closed:** 2026-03-15 | **GitLab:** #12

## Problem

If producer P produces modalities {A, B} and two channels each need different subsets, P runs twice — once per channel worker thread. No caching of producer results across channels. Doubles computation for expensive producers (neural network inference).

## Resolution

Result cache added in DataProducers2Channels.
