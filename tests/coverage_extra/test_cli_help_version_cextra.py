# ============================================================================
# SOURCEFILE: test_cli_help_version.py
# RELPATH: bundle_file_tool_v2/tests/integration/test_cli_help_version.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.0
# LIFECYCLE: Proposed
# DESCRIPTION: Integration tests for CLI commands
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

import importlib.util
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
