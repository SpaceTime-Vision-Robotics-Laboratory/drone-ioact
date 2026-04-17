# Robosim robobase client latency — RESOLVED with maxsize=1
**Created:** 2026-04-14 | **Priority:** 1

## Problem

`client.py` (robobase) was less snappy than `client-old.py` (manual threading) when server is remote. Root cause: **producer-consumer rate mismatch** — keyboard produced at 30/sec, A2E consumed at ~12/sec. With default `maxsize=100`, the queue buffered excess, causing drift after key release.

## Fix applied

- `QUEUE_DEFAULT_MAX_SIZE`: 100 → 1 (natural backpressure)
- Cached `MAXES` in `client.py` `actions_fn` (eliminated extra RTT per MOVE)

## Definitive measurements (server-side ACK timestamps, ~40ms RTT, w held 3s)

```
                     robobase(maxsize=1)   client-old
Moves applied:              38                 36
Duration:                 3.11s              2.97s
Rate:                    11.9/sec           11.8/sec
Avg interval:            83.9ms             84.8ms
Jitter (stddev):          3.0ms              4.1ms
Min/Max:            81.4/101.2ms       81.9/101.0ms
Queue drain:              none               none
```

**Identical performance.** Both limited by single TCP socket alternating camera fetches (~40ms) and moves (~40ms). Occasional ~101ms spikes from extra camera fetch between moves.

## Remaining

- [ ] Decide maxsize default — maxsize=1 breaks trajectory upload (see task #24)
- [ ] Document maxsize tradeoff

## Done when

- ~~Parity with client-old.py~~ DONE (identical server-side throughput)
- ~~Cache maxes~~ DONE
- ~~No queue drift~~ DONE
- Maxsize decision finalized (task #24)
