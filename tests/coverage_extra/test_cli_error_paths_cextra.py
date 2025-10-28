# ============================================================================
# SOURCEFILE: test_cli_error_paths_cextra.py
# RELPATH: bundle_file_tool_v2/tests/integration/test_cli_error_paths_cextra.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.0
# LIFECYCLE: Proposed
# DESCRIPTION: Integration tests for CLI commands
# ============================================================================
import sys
import pytest
from pathlib import Path

# Robust import of CLI whether or not 'src' is on sys.path.
import sys as _sys, importlib.util
from pathlib import Path as _Path
_REPO_ROOT = _Path(__file__).resolve().parents[2]
_SRC_DIR = _REPO_ROOT / "src"
try:
    import src.cli as cli  # type: ignore
except Exception:
    cli_path = _SRC_DIR / "cli.py"
    if not cli_path.exists():
        raise ModuleNotFoundError("Unable to locate src/cli.py for import")
    spec = importlib.util.spec_from_file_location("cli", cli_path)
    _mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader, "Invalid import spec for cli.py"
    spec.loader.exec_module(_mod)  # type: ignore[attr-defined]
    cli = _mod

try:
    from src.core.writer import BundleWriter  # type: ignore
    from src.core.models import BundleEntry  # type: ignore
    from src.core.exceptions import BundleWriteError  # type: ignore
except ModuleNotFoundError:
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

    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 1
    stderr = capsys.readouterr().err
    assert "Output directory must be specified" in stderr or "output" in stderr.lower()
