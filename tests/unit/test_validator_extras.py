# ============================================================================
# SOURCEILE: test_validator_extras.py
# RELPATH: bundle_file_tool_v2/tests/unit/test_validator_extras.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.0
# LIFECYCLE: Proposed
# DESCRIPTION: Unit tests for PathValidator extras
# ============================================================================
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
