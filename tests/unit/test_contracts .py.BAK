# tests/augmented/test_contracts.py
from pathlib import Path
import pytest
from core.writer import BundleWriter, BundleCreator
from core.models import BundleEntry
from core.exceptions import OverwriteError

def test_discovery_deny_precedence(tmp_path):
    (tmp_path / "keep.py").write_text("x")
    (tmp_path / "skip.log").write_text("x")
    creator = BundleCreator(allow_globs=["**/*"], deny_globs=["**/*.log"])
    files = creator.discover_files(tmp_path)
    names = {p.name for p in files}
    assert "keep.py" in names
    assert "skip.log" not in names

def test_prompt_policy_raises(tmp_path):
    writer = BundleWriter(base_path=tmp_path, overwrite_policy="prompt")
    (tmp_path / "a.txt").write_text("exists")
    entry = BundleEntry(path="a.txt", content="new", is_binary=False, encoding="utf-8", eol_style="LF")
    with pytest.raises(OverwriteError):
        writer.write_entry(entry, tmp_path)