from pathlib import Path
import pytest
from core.validators import PathValidator, PathTraversalError

def test_validate_paths_returns_resolved(tmp_path: Path):
    pv = PathValidator(tmp_path)
    paths = [Path("a.txt"), Path("dir/b.txt")]
    out = pv.validate_paths(paths)
    assert all(p.is_absolute() for p in out)
    assert str(out[0]).endswith("a.txt")

def test_absolute_rejected_message(tmp_path: Path):
    pv = PathValidator(tmp_path)
    with pytest.raises(PathTraversalError, match="Absolute paths not allowed"):
        pv.validate_path(Path("/absolute/path"))
