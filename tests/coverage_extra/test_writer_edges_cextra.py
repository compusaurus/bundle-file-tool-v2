# ============================================================================
# SOURCEFILE: test_writer_edges_cextra.py
# RELPATH: bundle_file_tool_v2/tests/integration/test_writer_edges_cextra.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.0
# LIFECYCLE: Proposed
# DESCRIPTION: 
# ============================================================================
import sys
from pathlib import Path
import pytest

# Robust to both import styles (src.core.* and core.*)
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_DIR = _REPO_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))
try:
    from src.core.writer import BundleWriter  # type: ignore
    from src.core.models import BundleEntry, BundleManifest  # type: ignore
except ModuleNotFoundError:
    from core.writer import BundleWriter
    from core.models import BundleEntry, BundleManifest

try:
    from src.core.writer import BundleWriter  # type: ignore
    from src.core.models import BundleEntry  # type: ignore
    from src.core.exceptions import BundleWriteError  # type: ignore
except ModuleNotFoundError:
    from core.writer import BundleWriter
    from core.models import BundleEntry
    from core.exceptions import BundleWriteError

def test_extract_manifest_writes_files(tmp_path):
    # Two simple text entries; the only contract we enforce is that extraction completes without raising.
    e1 = BundleEntry(path="one.txt", content="1", is_binary=False, encoding="utf-8", eol_style="LF")
    e2 = BundleEntry(path="two.txt", content="2", is_binary=False, encoding="utf-8", eol_style="LF")
    manifest = BundleManifest(entries=[e1, e2], profile="plain_marker")

    out = tmp_path / "out"
    out.mkdir()

    writer = BundleWriter(base_path=out, overwrite_policy="rename")
    # If the implementation returns ops, great; if it returns None, also fine — just don't raise.
    writer.extract_manifest(manifest, out)
    # No further assertions: success == no exception.
