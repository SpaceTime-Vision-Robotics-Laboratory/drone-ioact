from pathlib import Path
from datetime import datetime
from queue import Empty
from robobase.utils import DataStorer
import numpy as np
import pytest

def test_DataStorer_constructor_creates_directory(tmp_path: Path):
    target = tmp_path / "store_dir"
    assert not target.exists()

    DataStorer(target)
    assert target.exists()
    assert target.is_dir()

def test_DataStorer_constructor_rejects_non_empty_directory(tmp_path: Path):
    (target := tmp_path / "non_empty_dir").mkdir()
    (target / "file.txt").write_text("data")

    with pytest.raises(AssertionError) as exc:
        DataStorer(target)
    assert "exists" in str(exc.value)

def test_push_and_get_and_store_flow(tmp_path):
    ds = DataStorer(tmp_path)
    t1, t2 = datetime.now(), datetime.now()
    arr1, arr2 = np.array([1, 2, 3]), np.array([4, 5, 6])

    # Calling before push should raise
    with pytest.raises(Empty):
        ds.get_and_store()

    ds.push(arr1, t1)
    ds.push(arr2, t2)
    assert ds.data_queue.qsize() == 2

    # store and check twice
    ds.get_and_store()
    assert ds.data_queue.qsize() == 1
    ds.get_and_store()
    assert ds.data_queue.qsize() == 0
    with pytest.raises(Empty):
        ds.get_and_store()

    # verify data on disk
    files = sorted(list(tmp_path.iterdir()), key=lambda p: p.name) # sort for consistency
    assert len(files) == 2
    saved_arrays = [np.load(f) for f in files]
    assert np.array_equal(saved_arrays[0], arr1)
    assert np.array_equal(saved_arrays[1], arr2)
