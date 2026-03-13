"""replay_data_producer.py - Implementation of ReplayDataProducer"""
from pathlib import Path
from overrides import overrides
import numpy as np

from .data_producer import DataProducer
from .types import DataItem
from .utils import logger

class ReplayDataProducer(DataProducer):
    """Acts like a RawDataProducer, but operates on the logs/ of ROBOBASE_STORE_LOGS=2 (or similar) from DataChannel"""
    def __init__(self, data_dir: Path, prefix: str | None = None, loop: bool=True):
        self.data_dir = Path(data_dir)
        self.loop = loop
        self.prefix = prefix or ""

        self._data = self._build_data()
        self._keys = list(self._data.keys())
        self._modalities = self._build_modalities()
        super().__init__(modalities=self._modalities)
        logger.debug(f"Built ReplayEnv from {len(self._data)} items on disk. Modalities: {self._modalities}")

        self._current_ix = 0

    @overrides
    def produce(self, deps: dict[str, DataItem] | None = None) -> dict[str, DataItem]:
        file = self._data[self._keys[self._current_ix]]
        data = np.load(file, allow_pickle=True)
        res = {}
        for k, v in data.items():
            if v.shape == (0, ) or (len(v.shape) > 0 and v.shape[0] > 0 and isinstance(v[0], str)): # npz is hard :/
                res[f"{self.prefix}{k}"] = v
            else:
                res[f"{self.prefix}{k}"] = v.item()
        self._current_ix = (self._current_ix + 1) % len(self._data)
        return res

    def _build_data(self) -> dict[str, Path]:
        """returns an (oredered) dict {timestamp: list of npz files to read}. Matches actions to data if needed"""
        assert (data_dir := self.data_dir / "DataChannel").exists()
        res = {item.stem: item for item in sorted(data_dir.iterdir(), key=lambda p: p.name)}
        assert len(res) > 0, f"No data items fround at '{self.data_dir}'"
        return res

    def _build_modalities(self) -> list[str]:
        """returns the list of modalities from the first data item"""
        file = self._data[self._keys[0]]
        res = list(np.load(file, allow_pickle=True).keys())
        return [f"{self.prefix}{modality}" for modality in res]
