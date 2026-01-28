"""auto_follow_logs_frame_reader.py - interface for auto follow logs to simulate the olympe env as video"""
import numpy as np
from vre_video.readers import NumpyFrameReader
import os
from pathlib import Path
from natsort import natsorted
from roboimpl.utils import logger

class AutoFollowLogsFrameReader(NumpyFrameReader):
    def __init__(self, res_path: Path, fps: float | None = None, frames: list[int] | None = None):
        """must be the 'res' dir wtih npz files from auto follow logs"""
        res_names = natsorted([p.name for p in Path(res_path).iterdir()])
        assert all(p.endswith(".npz") for p in res_names), res_names
        data: list[np.ndarray] = []
        for ix in range(len(res_names)):
            res: dict = np.load(f"{res_path}/{res_names[ix]}", allow_pickle=True)["arr_0"].item()
            data.append(res["frame"][..., ::-1]) # BGR2RGB
        self.data = np.array(data)
        self._fps = fps or float(os.getenv("VIDEO_FPS", "1"))
        self.frames = frames or list(range(len(self.data)))
        self.frames_ix = dict(zip(self.frames, range(len(self.frames)))) # {ix: frame}
        self._path = str(data) if isinstance(data, (str, Path)) else "in memory"
        assert len(data) > 0
        logger.debug(f"Frames: {len(data)}")
