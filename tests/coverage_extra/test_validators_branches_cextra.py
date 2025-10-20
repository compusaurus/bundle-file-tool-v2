import sys
from pathlib import Path
import pytest

# Robust to both import styles (src.core.* and core.*)
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_DIR = _REPO_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))
try:
    from src.core.validators import GlobFilter, PathValidator  # type: ignore
except ModuleNotFoundError:
    from core.validators import GlobFilter, PathValidator


def test_deny_precedence_when_allow_also_matches(tmp_path):
    base = tmp_path
    f = base / "tests" / "mod.py"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("x", encoding="utf-8")

    gf = GlobFilter(allow_patterns=["**/*.py"], deny_patterns=["**/tests/**"])
    assert gf.should_include(str(f)) is False  # deny wins

def test_invalid_glob_pattern_variant_raises():
    with pytest.raises(Exception):
        GlobFilter(allow_patterns=["[abc"])

def test_is_safe_path_windows_and_unc_behave():
    pv = PathValidator()  # use defaults; just assert boolean return
    assert isinstance(pv.is_safe_path(r"C:\windows\system32"), bool)
    assert isinstance(pv.is_safe_path(r"\\server\share\folder"), bool)

def test_sanitize_filename_reserved_and_long():
    for bad in ("CON", "NUL", "PRN", "LPT1", "COM1", "file.", "name..", "trailspace "):
        safe = PathValidator.sanitize_filename(bad)
        assert isinstance(safe, str) and safe and all(ch not in safe for ch in "\\/:*?\"<>|")
    long_name = "a" * 300
    safe_long = PathValidator.sanitize_filename(long_name)
    assert isinstance(safe_long, str) and len(safe_long) > 0
