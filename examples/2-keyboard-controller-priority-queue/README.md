# Keyboard controller but also perform some priority actions on specific keys

See the first example's README for setup: [link](../1-keyboard-controller-and-display/README.md).

```bash
python main.py 10.202.0.1
```

The priority command is done on the keys "w" and "e" and ESC (quit). To test it, tap "i" a few times (forward that waits) and then tap "w" and see how it is ran before the other "i"s are taken into account.

The expected output should be something like:
```
[2025-11-06T17:09:07 DRONE-INFO] Pressed 'i'. Adding: FORWARD (main.py:on_release:24)
[2025-11-06T17:09:07 DRONE-INFO] Received action: FORWARD (#in queue: 0) (olympe_actions_maker.py:run:30)
[2025-11-06T17:09:07 DRONE-INFO] Pressed 'i'. Adding: FORWARD (main.py:on_release:24)
[2025-11-06T17:09:07 DRONE-INFO] Pressed 'i'. Adding: FORWARD (main.py:on_release:24)
[2025-11-06T17:09:07 DRONE-INFO] Pressed 'i'. Adding: FORWARD (main.py:on_release:24)
[2025-11-06T17:09:08 DRONE-INFO] Pressed 'i'. Adding: FORWARD (main.py:on_release:24)
[2025-11-06T17:09:16 DRONE-INFO] Received action: FORWARD (#in queue: 4) (olympe_actions_maker.py:run:30)
[2025-11-06T17:09:25 DRONE-INFO] Received action: FORWARD (#in queue: 3) (olympe_actions_maker.py:run:30)
[2025-11-06T17:09:39 DRONE-INFO] Pressed 'w'. Adding: FORWARD_NOWAIT (main.py:on_release:24)
[2025-11-06T17:09:39 DRONE-DEBUG] Received a priority action: FORWARD_NOWAIT. Adding it to the start of the queue (main.py:on_release:27)
[2025-11-06T17:09:39 DRONE-INFO] Pressed 'e'. Adding: ROTATE_NOWAIT (main.py:on_release:24)
[2025-11-06T17:09:39 DRONE-DEBUG] Received a priority action: ROTATE_NOWAIT. Adding it to the start of the queue (main.py:on_release:27)
[2025-11-06T17:09:43 DRONE-INFO] Received action: FORWARD_NOWAIT (#in queue: 4) (olympe_actions_maker.py:run:30)
[2025-11-06T17:09:43 DRONE-INFO] Received action: ROTATE_NOWAIT (#in queue: 3) (olympe_actions_maker.py:run:30)
[2025-11-06T17:09:43 DRONE-INFO] Received action: FORWARD (#in queue: 2) (olympe_actions_maker.py:run:30)
[2025-11-06T17:09:46 DRONE-INFO] Received action: FORWARD (#in queue: 1) (olympe_actions_maker.py:run:30)
[2025-11-06T17:09:49 DRONE-INFO] Received action: FORWARD (#in queue: 0) (olympe_actions_maker.py:run:30)
```
