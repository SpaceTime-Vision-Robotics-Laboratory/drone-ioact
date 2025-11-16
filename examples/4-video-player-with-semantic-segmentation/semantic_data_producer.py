"""semantic_data_producer.py produces both RGB and semantic segmentation using a PHG-MAE-Distil model"""
# pylint: disable=duplicate-code
import numpy as np
import torch as tr # pylint: disable=import-error
from torch.nn import functional as F # pylint: disable=import-error

from safeuav import SafeUAV

from drone_ioact import DataProducer
from drone_ioact.drones.video import VideoContainer
from drone_ioact.utils import logger

COLOR_MAP = [[0, 255, 0], [0, 127, 0], [255, 255, 0], [255, 255, 255],
             [255, 0, 0], [0, 0, 255], [0, 255, 255], [127, 127, 63]]
CLASSES = ["land", "forest", "residential", "road", "little-objects", "water", "sky", "hill"]
DEVICE = "cuda" if tr.cuda.is_available() else "cpu"

def colorize_semantic_segmentation(semantic_map: np.ndarray, color_map: list[tuple[int, int, int]] | None = None) \
        -> np.ndarray:
    """Colorize semantic segmentation maps. Must be argmaxed (H, W). Can paint over the original RGB frame or not."""
    color_map = color_map or COLOR_MAP
    assert np.issubdtype(semantic_map.dtype, np.integer), semantic_map.dtype
    assert (max_class := semantic_map.max()) <= len(color_map), (max_class, len(color_map))
    return np.array(color_map)[semantic_map]

class SemanticDataProducer(DataProducer):
    """VideoFrameReader gets data from a video container (producing frames in real time)"""
    def __init__(self, video: VideoContainer, weights_path: str):
        self.video = video
        self.weights_path = weights_path

        ckpt = tr.load(weights_path, map_location="cpu")
        logger.info(f"Loaded weights from '{weights_path}'")
        self.cfg = ckpt["hyper_parameters"]["cfg"]
        self.statistics = ckpt["hyper_parameters"]["statistics"]
        self.model = SafeUAV(**self.cfg["model"]["parameters"])
        self.model.load_state_dict(ckpt["state_dict"])
        self._mean = tr.Tensor(self.statistics["rgb"][2]).reshape(1, 3, 1, 1).to(DEVICE)
        self._std = tr.Tensor(self.statistics["rgb"][3]).reshape(1, 3, 1, 1).to(DEVICE)
        self.model = self.model.eval().to(DEVICE)

    @tr.no_grad()
    def compute_sema(self, rgb: np.ndarray) -> np.ndarray:
        """computes semantic segmentation for one rgb frame"""
        h, w = self.cfg["model"]["hparams"]["data_shape"]["rgb"][1:3]
        rgb_h, rgb_w = rgb.shape[0:2]

        # safuav defines [rgb_channels, sema_channels] concatenated so model expectes 3 + N_CLASSES channels as inputs
        cumsum = [0, *np.cumsum([x[0] for x in self.cfg["model"]["hparams"]["data_shape"].values()])]
        rgb_pos = self.cfg["data"]["parameters"]["task_names"].index("rgb")
        x = tr.zeros(1, self.model.encoder.d_in, h, w, device=DEVICE)

        tr_rgb = F.interpolate(tr.from_numpy(rgb)[None].permute(0, 3, 1, 2).to(DEVICE), size=(h, w))
        tr_rgb_std = (tr_rgb - self._mean) / self._std
        x[:, cumsum[rgb_pos]: cumsum[rgb_pos+1] ] = tr_rgb_std
        y = self.model.forward(x) # output data is in logits (B, H, W, C)

        sema_pos = self.cfg["data"]["parameters"]["task_names"].index("semantic_output")
        tr_y_sema = F.interpolate(y[:, cumsum[sema_pos]: cumsum[sema_pos+1]], (rgb_h, rgb_w))
        y_sema = tr_y_sema.permute(0, 2, 3, 1).cpu().numpy()[0]
        return y_sema

    def get_current_data(self, timeout_s: int = 10) -> dict[str, np.ndarray]:
        rgb = self.video.get_current_frame()
        semantic = self.compute_sema(rgb)
        return {"rgb": rgb, "semantic": semantic}

    def is_streaming(self) -> bool:
        return not self.video.is_done
