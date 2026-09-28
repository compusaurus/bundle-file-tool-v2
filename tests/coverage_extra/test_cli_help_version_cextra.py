# ============================================================================
# SOURCEFILE: test_cli_help_version.py
# RELPATH: bundle_file_tool_v2/tests/integration/test_cli_help_version.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.0
# LIFECYCLE: Proposed
# DESCRIPTION: Integration tests for CLI commands
# Relative Path: C:/Users/mpw/Python/bundle_file_project/bundle_file_tool_v2/tests/coverage_extra/test_cli_help_version_cextra.py
# Purpose:
# independent_entry_point:
# ============================================================================
import sys
from pathlib import Path
import pytest

# Import from the project's installed-layout package root.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_DIR = _REPO_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))
from core.writer import BundleWriter
from core.models import BundleEntry, BundleManifest
import cli

def test_cli_help_exits_zero(monkeypatch, capsys):
    argv = ["prog", "--help"]
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 0
    out = capsys.readouterr().out
    # Presence of the top-level commands in help output (don’t assert full text)
    assert any(tok in out for tok in ("bundle", "unbundle", "validate"))

# Only add a version test if your CLI supports it globally; leaving it out avoids argparse exit=2.
