# ============================================================================
# SOURCEILE: test_discovery_globfilter.py
# RELPATH: bundle_file_tool_v2/tests/unit/test_discovery_globfilter.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.0
# LIFECYCLE: Proposed
# DESCRIPTION: Comprehensive tests for v1.1.5 → v2.1 config migration
# ============================================================================
from pathlib import Path
from core.writer import BundleCreator

def test_discover_respects_allow_and_deny(tmp_path: Path):
    (tmp_path / "keep.py").write_text("a")
    (tmp_path / "skip.txt").write_text("b")
    (tmp_path / "skip.log").write_text("c")
    bc = BundleCreator(
        allow_globs=["**/*.py", "**/*.txt", "**/*.log"],
        deny_globs=["**/*.log", "**/.venv/**"]
    )
    files = bc.discover_files(tmp_path)
    names = sorted(p.name for p in files)
    assert "keep.py" in names
    assert "skip.txt" in names
    assert "skip.log" not in names  # denied wins

def test_discover_respects_allow_and_deny(tmp_path: Path):
    (tmp_path / "keep.py").write_text("a")
    (tmp_path / "skip.txt").write_text("b")
    (tmp_path / "skip.log").write_text("c")
    bc = BundleCreator(
        allow_globs=["**/*.py", "**/*.txt", "**/*.log"],
        deny_globs=["**/*.log", "**/.venv/**"]
    )
    files = bc.discover_files(tmp_path)
    names = sorted(p.name for p in files)
    assert "keep.py" in names
    assert "skip.txt" in names
    assert "skip.log" not in names  # denied wins
