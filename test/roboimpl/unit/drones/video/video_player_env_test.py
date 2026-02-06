import time
import numpy as np
import pytest
from vre_video import VREVideo
from roboimpl.envs.video import VideoPlayerEnv

def test_VideoPlayerEnv_basic():
    video = VREVideo(frames := np.random.randint(0, 255, size=(100, 40, 40, 3), dtype=np.uint8), fps=30)
    video_player = VideoPlayerEnv(video)
    assert video_player.frame_ix == 0

    with pytest.raises(AssertionError):
        video_player.close()

    assert not video_player.is_running()
    video_player.start()
    time.sleep(0.01)
    assert video_player.is_running()

    assert video_player.frame_ix > 0
    current_frame = video_player.get_state()
    assert np.allclose(frames[current_frame["frame_ix"]], current_frame["rgb"])

    while True:
        if video_player.frame_ix > 10:
            video_player.close()
            break

    time.sleep(0.05)
    assert not video_player.is_running()
