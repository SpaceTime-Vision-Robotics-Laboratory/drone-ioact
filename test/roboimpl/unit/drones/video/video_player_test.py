import time
import numpy as np
import pytest
from vre_video import VREVideo
from roboimpl.drones.video import VideoPlayer

def test_VideoPlayer_basic():
    video = VREVideo(frames := np.random.randint(0, 255, size=(100, 40, 40, 3), dtype=np.uint8), fps=30)
    video_player = VideoPlayer(video)
    assert video_player.frame_ix == 0

    with pytest.raises(AssertionError):
        video_player.stop_video()

    video_player.start()
    time.sleep(0.01)
    assert video_player.frame_ix > 0
    current_frame = video_player.get_current_frame()
    assert np.allclose(frames[current_frame["frame_ix"]], current_frame["rgb"])

    while True:
        if video_player.frame_ix > 10:
            video_player.stop_video()
            break

    time.sleep(0.05)
    assert not video_player.is_alive()
