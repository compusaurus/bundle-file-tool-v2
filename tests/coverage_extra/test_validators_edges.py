import sys
from pathlib import Path

# Robust to both import styles (src.core.* and core.*)
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_DIR = _REPO_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

try:
    from src.core.validators import GlobFilter, PathValidator  # type: ignore
except ModuleNotFoundError:
    from core.validators import GlobFilter, PathValidator


def test_allow_empty_list_allows_nothing(tmp_path):
    gf = GlobFilter(allow_patterns=[])
    assert gf.should_include("any.txt") is False


def test_globstar_basename_match():
    gf = GlobFilter(allow_patterns=["**/*.log"])
    assert gf.should_include("error.log") is True


def test_filter_paths_with_base_variants(tmp_path):
    base = tmp_path / "src"
    base.mkdir()
    f = base / "pkg" / "m.py"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("x", encoding="utf-8")
    gf = GlobFilter(allow_patterns=["src/**/*.py"])
    out = gf.filter_paths([f], base_path=base)
    assert out == [f]


def test_sanitize_non_string_yields_unnamed():
    assert PathValidator.sanitize_filename(123) == "unnamed"
