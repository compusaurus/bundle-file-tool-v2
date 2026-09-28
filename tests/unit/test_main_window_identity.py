"""Release identity must own every main-window title."""

from pathlib import Path


def test_main_window_titles_are_derived_from_the_runtime_version():
    source = Path("src/ui/main_window.py").read_text(encoding="utf-8")

    assert "Bundle File Tool v2.2" not in source
    assert source.count('f"Bundle File Tool v{__version__}') >= 4
