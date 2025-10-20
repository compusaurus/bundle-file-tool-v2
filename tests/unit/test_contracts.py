# ============================================================================
# FILE: test_contracts.py - FINAL CORRECTED VERSION
# ============================================================================

from pathlib import Path
import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from core.writer import BundleWriter, BundleCreator, OverwritePolicy
from core.models import BundleEntry
from core.exceptions import OverwriteError

def test_discovery_deny_precedence(tmp_path):
    """
    Ensures that deny patterns take precedence over allow patterns during discovery.
    This is a critical contract for the BundleCreator's filtering logic.
    """
    (tmp_path / "keep.py").write_text("x")
    (tmp_path / "skip.log").write_text("x")
    
    # BundleCreator should correctly pass these globs to the GlobFilter
    creator = BundleCreator(allow_globs=["**/*"], deny_globs=["*.log"])
    files = creator.discover_files(tmp_path)
    
    names = {p.name for p in files}
    assert "keep.py" in names
    assert "skip.log" not in names

def test_prompt_policy_raises(tmp_path):
    """
    Ensures that the default 'prompt' overwrite policy raises an OverwriteError
    when a file collision is detected in a non-interactive context.
    """
    target = tmp_path / "a.txt"
    target.write_text("exists")
    
    writer = BundleWriter(base_path=tmp_path, overwrite_policy=OverwritePolicy.PROMPT)
    entry = BundleEntry(path="a.txt", content="new", is_binary=False, encoding="utf-8", eol_style="LF")
    
    with pytest.raises(OverwriteError):
        # The write_entry method is the correct place to test this contract directly
        writer.write_entry(entry)

