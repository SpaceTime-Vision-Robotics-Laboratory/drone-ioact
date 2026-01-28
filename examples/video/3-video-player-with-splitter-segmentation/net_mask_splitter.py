#!/usr/bin/env python3
# pylint: disable=all
from pathlib import Path

import torch
import numpy as np
from torch import nn
from torchinfo import summary

from roboimpl.utils import image_resize

DEVICE = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")

class DoubleConv(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, dropout_rate: float = 0.1):
        super().__init__()
        self.double_conv = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, 3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Dropout2d(dropout_rate),
            nn.Conv2d(out_channels, out_channels, 3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        )

    def forward(self, x):
        return self.double_conv(x)


class Down(nn.Module):
    """Downscaling with max pool then double conv"""

    def __init__(self, in_channels: int, out_channels: int, dropout_rate: float = 0.1):
        super().__init__()
        self.max_pool_conv = nn.Sequential(
            nn.MaxPool2d(2),
            DoubleConv(in_channels, out_channels, dropout_rate)
        )

    def forward(self, x):
        return self.max_pool_conv(x)


class Up(nn.Module):
    """Upscaling then double conv"""

    def __init__(self, in_channels: int, out_channels: int, dropout_rate: float = 0.1):
        super().__init__()
        self.up = nn.ConvTranspose2d(in_channels, in_channels // 2, kernel_size=2, stride=2)
        self.conv = DoubleConv(in_channels, out_channels, dropout_rate)

    def forward(self, x1, x2):
        x1 = self.up(x1)
        diff_y = x2.size()[2] - x1.size()[2]
        diff_x = x2.size()[3] - x1.size()[3]
        x1 = nn.functional.pad(x1, [diff_x // 2, diff_x - diff_x // 2, diff_y // 2, diff_y - diff_y // 2])
        x = torch.cat([x2, x1], dim=1)
        return self.conv(x)


class OutputConv(nn.Module):
    def __init__(self, in_channels: int, out_channels: int):
        super().__init__()
        self.conv = nn.Conv2d(in_channels, out_channels, kernel_size=1)

    def forward(self, x):
        return self.conv(x)


class MaskSplitterNet(nn.Module):
    def __init__(
            self,
            in_channels: int = 4,
            out_channels: int = 2,
            base_channels: int = 32,
            dropout_rate: float = 0.1,
    ):
        super().__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels

        self.inc = DoubleConv(in_channels, base_channels, 0)
        self.image_conv = DoubleConv(3, base_channels, 0)
        self.mask_attention = nn.Sequential(
            nn.Conv2d(1, base_channels, kernel_size=3, padding=1),
            nn.Sigmoid()
        )
        self.down1 = Down(base_channels, base_channels * 2, 0)
        self.down2 = Down(base_channels * 2, base_channels * 4, 0)
        self.down3 = Down(base_channels * 4, base_channels * 8, dropout_rate)

        self.up1 = Up(base_channels * 8, base_channels * 4, dropout_rate)
        self.up2 = Up(base_channels * 4, base_channels * 2, 0)
        self.up3 = Up(base_channels * 2, base_channels, 0)

        self.outc = OutputConv(base_channels, out_channels)

    def forward(self, x):
        img, mask = x[:, :3], x[:, 3:]
        x_img = self.image_conv(img)
        attention = self.mask_attention(mask)
        x1 = x_img * (1 + attention)
        x2 = self.down1(x1)
        x3 = self.down2(x2)
        x4 = self.down3(x3)
        x = self.up1(x4, x3)
        x = self.up2(x, x2)
        x = self.up3(x, x1)
        return self.outc(x)

    def load_model(self, model_path: str | Path):
        self.load_state_dict(torch.load(model_path))
        return self

    def preprocess(self, image: np.ndarray, mask: np.ndarray, image_size: tuple[int, int]) -> torch.Tensor:
        """Prepares the input 4-channel tensor from image and mask."""
        assert len(A := image.shape) == 3 and len(B := mask.shape) == 3 and A[0:2] == B[0:2], (image.shape, mask.shape)
        image_bgr = image[..., ::-1] # BGR! (H', W', 3)
        image_bgr_rsz = image_resize(image_bgr, height=image_size[0], width=image_size[1]) # (H, W, 3)
        mask_rsz = image_resize(mask, height=image_size[0], width=image_size[1], interpolation="nearest") # (H, W, 1)
        tr_image = torch.from_numpy(image_bgr_rsz.copy()).to(DEVICE).permute(2, 0, 1).float() / 255.0 # (3, H, W)
        tr_mask = torch.from_numpy(mask_rsz).to(DEVICE).permute(2, 0, 1).float() / 255.0 # (1, H, W)
        res = torch.cat([tr_image, tr_mask], dim=0).to(DEVICE).unsqueeze(0) # (1, 4, H, W)
        return res

    def infer(self, image: np.ndarray, mask: np.ndarray, image_size: tuple[int, int],
              bbox_threshold: float) -> tuple[np.ndarray, np.ndarray]:
        """Performs inference on a single frame."""
        input_tensor = self.preprocess(image, mask, image_size)
        with torch.inference_mode():
            output = self(input_tensor)
            probs = torch.sigmoid(output)
            predictions = (probs > bbox_threshold).to(dtype=torch.uint8).squeeze(0)
        return predictions.cpu().numpy()

if __name__ == "__main__":
    input_channels = 4  # RGB (3) + mask (1)
    model = MaskSplitterNet(in_channels=input_channels, out_channels=2, base_channels=32)

    sample_input_size = (1, input_channels, 360, 640)
    sample_input = torch.randn(*sample_input_size)
    output = model(sample_input)
    print(f"Output shape: {output.shape}")
    summary(model, input_size=sample_input_size)
