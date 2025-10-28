# ============================================================================
# SOURCEFILE: test_writer_failures.py
# RELPATH: bundle_file_tool_v2/tests/integration/test_writer_failures.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.0
# LIFECYCLE: Proposed
# DESCRIPTION: 
# ============================================================================

import sys
from pathlib import Path

# Robust to both import styles (src.core.* and core.*)
from pathlib import Path as _P
import sys as _sys
_REPO_ROOT = _P(__file__).resolve().parents[2]
_SRC_DIR = _REPO_ROOT / "src"
if str(_SRC_DIR) not in _sys.path:
    _sys.path.insert(0, str(_SRC_DIR))

try:
    from src.core.writer import BundleWriter, OverwritePolicy  # type: ignore
    from src.core.models import BundleEntry  # type: ignore
    from src.core.exceptions import BundleWriteError  # type: ignore
except ModuleNotFoundError:
    from core.writer import BundleWriter, OverwritePolicy
    from core.models import BundleEntry
    from core.exceptions import BundleWriteError

import pytest

def test_write_entry_binary_bad_base64_raises(tmp_path):
    writer = BundleWriter(base_path=tmp_path, add_headers=False)
    bad = BundleEntry(
        path="img.png",
        content="***notbase64***",
        is_binary=True,
        encoding="base64",
        eol_style="n/a",
    )
    with pytest.raises(BundleWriteError):
        writer.write_entry(bad, tmp_path / "img.png")


def test_write_entry_unknown_encoding_raises(tmp_path):
    writer = BundleWriter(base_path=tmp_path, add_headers=False)
    bad_txt = BundleEntry(
        path="a.txt",
        content="hello",
        is_binary=False,
        encoding="definitely-not-an-encoding",
        eol_style="LF",
    )
    with pytest.raises(BundleWriteError):
        writer.write_entry(bad_txt, tmp_path / "a.txt")


def test_get_renamed_path_considers_pending_writes(tmp_path):
    writer = BundleWriter(
        base_path=tmp_path, 
        overwrite_policy=OverwritePolicy.RENAME,
        add_headers=False
    )
    e1 = BundleEntry(path="f.txt", content="1", is_binary=False, encoding="utf-8", eol_style="LF")
    status1, path1 = writer.write_entry(e1, tmp_path / "f.txt")
    assert status1 == "processed"
    assert Path(path1).name == "f.txt"
    
    e2 = BundleEntry(path="f.txt", content="2", is_binary=False, encoding="utf-8", eol_style="LF")
    status2, path2 = writer.write_entry(e2, tmp_path / "f.txt")
    assert status2 == "processed"
    # Accept typical suffix variants
    assert Path(path2).name in {"f_1.txt", "f_2.txt", "f (1).txt", "f (2).txt"}