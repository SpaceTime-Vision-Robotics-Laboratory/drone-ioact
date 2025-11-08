"""semantic_data_producer.py produces both RGB and semantic segmentation using a PHG-MAE-Distil model"""
import numpy as np
from drone_ioact import DroneIn
from drone_ioact.utils import logger

from video_container import VideoContainer
from safeuav import SafeUAV
import torch as tr

COLOR_MAP = [[0, 255, 0], [0, 127, 0], [255, 255, 0], [255, 255, 255],
             [255, 0, 0], [0, 0, 255], [0, 255, 255], [127, 127, 63]]
CLASSES = ["land", "forest", "residential", "road", "little-objects", "water", "sky", "hill"]

class SemanticDataProducer(DroneIn):
    """VideoFrameReader gets data from a video container (producing frames in real time)"""
    def __init__(self, video: VideoContainer, weights_path: str):
        self.video = video
        self.weights_path = weights_path

        ckpt = tr.load(weights_path, map_location="cpu")
        logger.info("Loaded weights from '{weights_path}'")
        self.cfg = ckpt["hyper_parameters"]["cfg"]
        self.statistics = ckpt["hyper_parameters"]["statistics"]
        self.model = SafeUAV(**self.cfg["model"]["parameters"])
        self.model.load_state_dict(ckpt["state_dict"])
        self._mean = tr.Tensor(self.statistics["rgb"][2]).reshape(1, 3, 1, 1).to(self.device)
        self._std = tr.Tensor(self.statistics["rgb"][3]).reshape(1, 3, 1, 1).to(self.device)
        self.model = self.model.eval().to(self.device)

    def compute(self, rgb: np.ndarray) -> np.ndarray:
        h, w = self.cfg["model"]["hparams"]["data_shape"]["rgb"][1:3]
        cumsum = [0, *np.cumsum([x[0] for x in self.cfg["model"]["hparams"]["data_shape"].values()])]
        rgb_pos = self.cfg["data"]["parameters"]["task_names"].index("rgb")
        x = tr.zeros(len(ixs), self.model.encoder.d_in, h, w, device=self.device)
        tr_rgb = F.interpolate(tr.from_numpy(video[ixs]).permute(0, 3, 1, 2).to(self.device), size=(h, w))
        tr_rgb = (tr_rgb - self._mean) / self._std
        x[:, cumsum[rgb_pos]: cumsum[rgb_pos+1] ] = tr_rgb

        with tr.no_grad():
            y = self.model.forward(x) # output data is in logits (B, H, W, C)
        sema_pos = self.cfg["data"]["parameters"]["task_names"].index("semantic_output")
        y_rgb = y[:, cumsum[sema_pos]: cumsum[sema_pos+1]].permute(0, 2, 3, 1).cpu().numpy()
        return ReprOut(frames=video[ixs], output=MemoryData(y_rgb), key=ixs)


    def get_current_data(self, timeout_s: int = 10) -> dict[str, np.ndarray]:
        rgb = self.video.get_current_frame()
        semantic = None
        return {"rgb": rgb, "semantic": semantic}

    def is_streaming(self) -> bool:
        return not self.video.is_done

    def stop_streaming(self):
        self.video.is_done = True
