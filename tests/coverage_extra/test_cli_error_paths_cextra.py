# ============================================================================
# SOURCEFILE: test_cli_error_paths_cextra.py
# RELPATH: bundle_file_tool_v2/tests/integration/test_cli_error_paths_cextra.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.0
# LIFECYCLE: Proposed
# DESCRIPTION: Integration tests for CLI commands
# Relative Path: C:/Users/mpw/Python/bundle_file_project/bundle_file_tool_v2/tests/coverage_extra/test_cli_error_paths_cextra.py
# Purpose:
# independent_entry_point:
# ============================================================================
import sys
import pytest
from pathlib import Path

# Import from the project's installed-layout package root.
import sys as _sys
from pathlib import Path as _Path
_REPO_ROOT = _Path(__file__).resolve().parents[2]
_SRC_DIR = _REPO_ROOT / "src"
if str(_SRC_DIR) not in _sys.path:
    _sys.path.insert(0, str(_SRC_DIR))
import cli
from core.writer import BundleWriter
from core.models import BundleEntry
from core.exceptions import BundleWriteError

def test_bundle_invalid_profile_exits_nonzero(tmp_path, monkeypatch, capsys):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "x.txt").write_text("x", encoding="utf-8")

    argv = [
        "prog", "bundle", str(src_dir),
        "--output", str(tmp_path / "out.txt"),
        "--profile", "__no_such_profile__",   # invalid, should trigger our error handling
        # NO --dry-run here (bundle doesn’t define it)
    ]
    monkeypatch.setattr(sys, "argv", argv)

    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "Invalid profile" in err or "not found" in err or "ERROR:" in err

def test_unbundle_requires_output_exits_nonzero(tmp_path, monkeypatch, capsys):
    bundle = tmp_path / "b.txt"
    bundle.write_text("# FILE: a.txt\n# META: encoding=utf-8; eol=LF; mode=text\n# ===\na\n", encoding="utf-8")

    argv = ["prog", "unbundle", str(bundle), "--profile", "plain_marker", "--dry-run"]
    monkeypatch.setattr(sys, "argv", argv)

    class EmptyOutputConfig:
        @staticmethod
        def get(key, default=None):
            return "" if key == "global_settings.output_dir" else default

        @staticmethod
        def check_config_integrity():
            return None

    monkeypatch.setattr(cli, "ConfigManager", EmptyOutputConfig)

    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 1
    stderr = capsys.readouterr().err
    assert "Output directory must be specified" in stderr or "output" in stderr.lower()
