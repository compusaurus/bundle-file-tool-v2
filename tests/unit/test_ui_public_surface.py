"""Release-gate inventory for every public native-UI command and dialog."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
UI_ROOT = ROOT / "src" / "ui"
DIALOG_MODULES = {"messagebox", "filedialog", "colorchooser"}


def test_native_ui_contains_no_public_placeholder_messages():
    public_source = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(UI_ROOT.glob("*.py"))
    ).casefold()

    for forbidden in (
        "feature not implemented",
        "will be implemented in phase",
        "refer to the master architecture blueprint",
    ):
        assert forbidden not in public_source


def test_every_native_dialog_has_an_explicit_owner():
    missing = []
    for path in sorted(UI_ROOT.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            owner = node.func.value
            if not isinstance(owner, ast.Name) or owner.id not in DIALOG_MODULES:
                continue
            if not any(keyword.arg == "parent" for keyword in node.keywords):
                missing.append(f"{path.name}:{node.lineno} {owner.id}.{node.func.attr}")

    assert missing == []


def test_public_help_and_package_documents_are_present():
    for name in ("README.md", "USER_GUIDE.md", "CHANGELOG.md", "LICENSE.txt"):
        path = ROOT / name
        assert path.is_file() and path.stat().st_size > 0


def test_advertised_open_shortcut_has_a_real_binding():
    source = (UI_ROOT / "main_window.py").read_text(encoding="utf-8")

    assert 'accelerator="Ctrl+O"' in source
    assert 'bind_all("<Control-o>", self._open_bundle_shortcut)' in source
