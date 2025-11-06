# Keyboard controller but also perform some priority actions on specific keys

See the first example's README for setup: [link](../1-keyboard-controller-and-display/README.md).

```bash
DRONE_IP=10.202.0.1 python main.py
```

The priority command is done on the keys "w" and "e" and ESC (quit). To test it, tap "i" a few times (forward that waits) and then tap "w" and see how it is ran before the other "i"s are taken into account.
