"""phg_mae_semantic_data_producer.py produces both RGB and semantic segmentation using a PHG-MAE-Distil model"""
import numpy as np
import torch as tr
from torch.nn import functional as F
from overrides import overrides

from robobase import DataProducer, DataItem
from roboimpl.utils import logger

from .safeuav import SafeUAV

DEVICE = "cuda" if tr.cuda.is_available() else "cpu"

class PHGMAESemanticDataProducer(DataProducer):
    """PHGMAESemanticDataProducer - produces 'semantic' given a 'rgb' data producer which it composes over"""
    COLOR_MAP = [[0, 255, 0], [0, 127, 0], [255, 255, 0], [255, 255, 255],
                 [255, 0, 0], [0, 0, 255], [0, 255, 255], [127, 127, 63]]
    CLASSES = ["land", "forest", "residential", "road", "little-objects", "water", "sky", "hill"]

    def __init__(self, weights_path: str):
        super().__init__(modalities=["semantic"], dependencies=["rgb"])
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

    @overrides
    def produce(self, deps: dict[str, DataItem] | None = None) -> dict[str, DataItem]:
        semantic = self._compute_sema(deps["rgb"])
        return {"semantic": semantic}

    @tr.no_grad()
    def _compute_sema(self, rgb: np.ndarray) -> np.ndarray:
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
