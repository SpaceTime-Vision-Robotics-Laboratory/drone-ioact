# Video player on a random video VREVideo (ffmpeg wrapper) using the Drone's I/O data queues & controllers

```bash
python main.py video.mp4 [PORT=42069]
```

Controls:
- `q` - closes the window
- `Key.space` - pauses or plays the video
- `Key.right` - skips on second ahead
- `Key.left` - goes one second behind

Furthermore, this example starts an UDP socket listening to the given port. If the controls from above are provided as an UDP message, the actions are also taken.

To test the UDP connection, use:

```bash
echo -e "Key.left" | ncat -u 127.0.0.1 42069
```
