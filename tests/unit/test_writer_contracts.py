# ============================================================================
# SOURCEILE: test_writer_contracts.py
# RELPATH: bundle_file_tool_v2/tests/unit/test_writer_contracts.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.1
# LIFECYCLE: Proposed
# DESCRIPTION: 
# FIXES (v2.1.1):
#   - Added OverwritePolicy import to fix NameError
# ============================================================================
# Robust import of CLI whether or not 'src' is a package
import os
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
    from src.core.exceptions import BundleWriteError, OverwriteError  # type: ignore
except ModuleNotFoundError:
    from core.writer import BundleWriter, OverwritePolicy
    from core.models import BundleEntry
    from core.exceptions import BundleWriteError, OverwriteError

import pytest

def test_prompt_policy_raises(tmp_path: Path):
    target = tmp_path / "file.txt"
    target.write_text("original", encoding="utf-8")
    writer = BundleWriter(base_path=tmp_path, overwrite_policy=OverwritePolicy.PROMPT, add_headers=False)
    entry = BundleEntry(path="file.txt", content="new", is_binary=False, encoding="utf-8", eol_style="LF")
    with pytest.raises(OverwriteError):
        writer.write_entry(entry)

def test_utf8_bom_mapping(tmp_path: Path):
    writer = BundleWriter(base_path=tmp_path, overwrite_policy=OverwritePolicy.OVERWRITE, add_headers=False)
    entry = BundleEntry(path="bom.txt", content="x", is_binary=False, encoding="utf-8-bom", eol_style="LF")
    status, p = writer.write_entry(entry)
    assert status == "processed"
    data = Path(p).read_bytes()
    assert data.startswith(b"\xef\xbb\xbf")

def test_verbatim_newlines(tmp_path: Path):
    writer = BundleWriter(base_path=tmp_path, overwrite_policy=OverwritePolicy.OVERWRITE, add_headers=False)
    text = "a\r\nb\nc\rd"
    entry = BundleEntry(path="mix.txt", content=text, is_binary=False, encoding="utf-8", eol_style="MIXED")
    writer.write_entry(entry)
    assert (tmp_path / "mix.txt").read_bytes() == text.encode("utf-8")

def test_bundlewriteerror_signature(tmp_path: Path):
    writer = BundleWriter(base_path=tmp_path, overwrite_policy=OverwritePolicy.OVERWRITE, add_headers=False)
    bad = BundleEntry(path="bin.dat", content="!!not_base64!!", is_binary=True, encoding="base64", eol_style="n/a")
    with pytest.raises(BundleWriteError) as ei:
        writer.write_entry(bad)
    # tuple args: (path, reason)
    assert len(ei.value.args) == 2
    # FIX: Updated check to handle potential BinasciiError text
    assert "decode failed" in ei.value.args[1].lower()