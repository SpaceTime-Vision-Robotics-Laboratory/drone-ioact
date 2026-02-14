from pathlib import Path
from robobase import DataChannel
from robobase.utils import DataStorer
import pytest

def test_DataChannel_data_storer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ROBOBASE_LOGS_DIR", str(tmp_path))
    monkeypatch.setenv("ROBOBASE_STORE_LOGS", "2")
    channel = DataChannel(supported_types=["rgb"], eq_fn=lambda a, b: a==b)
    channel.put({"rgb": 0})
    channel.put({"rgb": 0})
    channel.put({"rgb": 1})
    channel.put({"rgb": 1})
    channel.put({"rgb": 2})
    channel.close()
    DataStorer.get_instance().close()
    assert len(list((tmp_path / "DataChannel").iterdir())) == 3

if __name__ == "__main__":
    from tempfile import TemporaryDirectory
    test_DataChannel_data_storer(Path(TemporaryDirectory().name))
