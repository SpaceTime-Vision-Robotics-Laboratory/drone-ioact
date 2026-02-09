# Video player on a random video VREVideo (ffmpeg wrapper) using the Drone's I/O data queues & controllers

```bash
python main.py video.mp4 [PORT=42069]
```

Key to Action:
- `Escape` -> `DISCONNECT`: closes the window
- `Space` -> `PLAY_PAUSE`: pauses or plays the video
- `Right` -> `SKIP_AHEAD_ONE_SECOND`: skips on second ahead
- `Left` -> `GO_BACK_ONE_SECOND`: goes one second behind
- `n/a` -> `TAKE_SCREENSHOT`: take a screenshot (no key, only UDP)

Furthermore, this example starts an UDP socket listening to the given port. The raw actions (right side) can also be sent via UDP messages.

To test the UDP connection, use:

```bash
echo -e "SKIP_AHEAD_ONE_SECOND" | ncat -u 127.0.0.1 42069
```
