import sys
from pathlib import Path
import pytest

# Robust import of CLI whether or not 'src' is a package
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_DIR = _REPO_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

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
