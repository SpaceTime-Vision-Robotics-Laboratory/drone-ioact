# Simulate a drone with a random video using VREVideo (ffmpeg wrapper)

```bash
python main.py video.mp4
```

It also sends dummy actions, but no actions maker thread picks them up.  You can press 'q' to close the window as well.

This could be used in the future to test the library with to mock a simulator, reading frames from a video, not from an actual drone.
