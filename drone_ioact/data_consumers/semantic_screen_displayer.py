"""semantic_screen_displayer.py: Extends ScreenDisplayer to display semantic segmentation"""
import numpy as np

from .screen_displayer import ScreenDisplayer

def colorize_semantic_segmentation(semantic_map: np.ndarray, color_map: list[tuple[int, int, int]]) -> np.ndarray:
    """Colorize semantic segmentation maps. Must be argmaxed (H, W). Can paint over the original RGB frame or not."""
    assert np.issubdtype(semantic_map.dtype, np.integer), semantic_map.dtype
    assert (max_class := semantic_map.max()) <= len(color_map), (max_class, len(color_map))
    return np.array(color_map)[semantic_map]

class SemanticScreenDisplayer(ScreenDisplayer):
    """Extends ScreenDisplayer to display semantic segmentation"""
    def __init__(self, *args, color_map: list[tuple[int, int, int]], **kwargs):
        super().__init__(*args, **kwargs)
        assert "semantic" in (st := self.data_producer.get_supported_types()), f"'rgb' not in {st}"
        self.color_map = color_map

    def get_current_frame(self):
        data = self.data_producer.get_current_data()
        rgb, semantic = data["rgb"], data["semantic"]
        sema_rgb = colorize_semantic_segmentation(semantic.argmax(-1), self.color_map).astype(np.uint8)
        combined = np.concatenate([rgb, sema_rgb], axis=1)
        return combined
