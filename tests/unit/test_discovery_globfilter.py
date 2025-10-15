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
