# Actions2Environment: batch-drain + pipeline send
**Created:** 2026-04-15 | **Priority:** 2

## Problem

Old `Actions2Environment` polled with `get_nowait()` + `sleep(0.1)`, adding ~50ms average latency per action. Also, the old `ActionsFn` signature `(env, action: Action)` processed one action at a time — no batching for envs that support pipelining (like `send_recv_packets`).

## What's done

- **A2E batch drain implemented** — `actions2env.py` now blocks on first action via `get(blocking=True, timeout=0.01)`, then drains remaining with `get_nowait()`. No more `sleep(0.1)`. Instant wake on first action, batches the rest.
- **`ActionsFn` signature changed** — `(Environment, list[Action]) -> bool` everywhere (types.py, actions2env.py). Single unified signature, no dual `action_fn`/`batch_action_fn` split.
- **robosim `client.py` updated** — uses `actions_fn(env, actions: list[Act])` with `env.send_recv_packets(msgs)` for pipelining. Works well on localhost — higher throughput than old client due to batching.
- **Lag resolved** — the 100ms sleep was causing perceived display lag (actions delayed → server physics delayed → stale frames).

## What's left

All other `action_fn` callsites still use the old single-action signature `(env, action: Action)`. Need to update to `(env, actions: list[Action])`:

**roboimpl action fns (3 — load-bearing):**
- `roboimpl/envs/gym/gym_env.py:17` — `gym_action_fn`
- `roboimpl/envs/video/video_actions.py:9` — `video_action_fn`
- `roboimpl/envs/olympe/olympe_actions.py:15` — `olympe_actions_fn`

**Examples (5 — follow from above):**
- `examples/basic/hello-world-controller/main.py:54` — lambda
- `examples/basic/hello-world-webcam/main.py:30` — `action_fn`
- `examples/maze/main.py:102` — `actions_fn` (name matches but sig is old)
- `examples/olympe/2-nser-ibvs/main.py:63` — `ibvs_olympe_actions_fn` (wraps `olympe_actions_fn`)
- All video/gym examples use the roboimpl fns above

**Tests (7):**
- `test/robobase/integration/test_i_Robot_replay_from_logs.py` — 6 lambdas `lambda env, action: ...`
- `test/robobase/integration/test_i_DataProducers2Channels_two_channels_two_controllers.py:72` — `lambda: None`
- `test/e2e/video-udp-screenshot/main.py:32` — uses `video_action_fn`

## Done when

- All `action_fn` callsites updated to `list[Action]` signature
- Tests pass (`pytest test/robobase`)
- robosim client.py confirmed working (already done)
