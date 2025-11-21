# Keyboard controller but also perform some priority actions on specific keys and semantic segmentation

See the first example's README for setup: [link](../1-keyboard-controller-and-display/README.md).

```bash
python main.py 10.202.0.1 [/path/to/safeuav_model.ckpt]
```

The priority command is done on the keys "w" and "e" and ESC (quit). To test it, tap "i" a few times (forward that waits) and then tap "w" and see how it is ran before the other "i"s are taken into account.

The expected output should be something like:
```
Pressed 'i'. Adding: FORWARD (main.py:on_release:24)
Received action: FORWARD (#in queue: 0) (olympe_actions_maker.py:run:30)
Pressed 'i'. Adding: FORWARD (main.py:on_release:24)
Pressed 'i'. Adding: FORWARD (main.py:on_release:24)
Pressed 'i'. Adding: FORWARD (main.py:on_release:24)
Pressed 'i'. Adding: FORWARD (main.py:on_release:24)
Received action: FORWARD (#in queue: 4) (olympe_actions_maker.py:run:30)
Received action: FORWARD (#in queue: 3) (olympe_actions_maker.py:run:30)
Pressed 'w'. Adding: FORWARD_NOWAIT (main.py:on_release:24)
Received a priority action: FORWARD_NOWAIT. Adding it to the start of the queue (main.py:on_release:27)
Pressed 'e'. Adding: ROTATE_NOWAIT (main.py:on_release:24)
Received a priority action: ROTATE_NOWAIT. Adding it to the start of the queue (main.py:on_release:27)
Received action: FORWARD_NOWAIT (#in queue: 4) (olympe_actions_maker.py:run:30)
Received action: ROTATE_NOWAIT (#in queue: 3) (olympe_actions_maker.py:run:30)
Received action: FORWARD (#in queue: 2) (olympe_actions_maker.py:run:30)
Received action: FORWARD (#in queue: 1) (olympe_actions_maker.py:run:30)
Received action: FORWARD (#in queue: 0) (olympe_actions_maker.py:run:30)
```

If semantic segmentation model is provided (depends on [4-video-player-with-semantic-segmentation](../4-video-player-with-semantic-segmentation) example), it also displays semantic segmentation.
