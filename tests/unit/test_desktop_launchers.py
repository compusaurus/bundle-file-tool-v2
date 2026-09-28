"""Cross-platform desktop launchers keep normal and diagnostic paths distinct."""

from __future__ import annotations

import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_windows_normal_launcher_is_windowless_and_uses_pythonw():
    source = (ROOT / "launchers" / "windows" / "Bundle File Tool.vbs").read_text(
        encoding="utf-8")
    assert "pythonw.exe" in source
    assert "shell.Run command, 0, False" in source
    assert '("BFT_DIAGNOSTIC") = "0"' in source
    assert "importlib.util.find_spec('pysplashx')" in source
    assert "importlib.util.find_spec('PySide6')" in source
    assert "fallbackPythonw" in source


def test_windows_diagnostic_launcher_keeps_console_and_session_logging():
    source = (ROOT / "launchers" / "windows"
              / "Bundle File Tool Diagnostic.cmd").read_text(encoding="utf-8")
    assert "python.exe" in source
    assert 'set "BFT_DIAGNOSTIC=1"' in source
    assert "pythonw.exe" not in source


def test_windows_web_launcher_is_windowless_and_starts_web_entry_point():
    source = (ROOT / "launchers" / "windows"
              / "Bundle File Tool Web.vbs").read_text(encoding="utf-8")
    assert "pythonw.exe" in source
    assert "src\\web_main.py" in source
    assert "shell.Run command, 0, False" in source


def test_windows_shortcut_quotes_the_vbs_path_without_cmd_consuming_quotes():
    installers = list(ROOT.glob("INSTALL_BUNDLETOOL_*.bat"))
    assert len(installers) == 1
    source = installers[0].read_text(encoding="ascii")
    assert "$s.Arguments=[char]34+" in source
    assert "+[char]34; $s.WorkingDirectory" in source
    assert "Bundle File Tool Web.lnk" in source
    assert "Bundle File Tool Web.vbs')+[char]34" in source


def test_macos_app_is_an_application_wrapper_not_a_terminal_launcher():
    app = ROOT / "launchers" / "macos" / "Bundle File Tool.app" / "Contents"
    plist = (app / "Info.plist").read_text(encoding="utf-8")
    executable = (app / "MacOS" / "bft-gui").read_text(encoding="utf-8")
    assert "CFBundleExecutable" in plist and "bft-gui" in plist
    assert "src/main.py" in executable
    assert "BFT_DIAGNOSTIC=0" in executable
    assert ".command" not in executable


def test_macos_web_app_starts_the_loopback_workspace():
    app = ROOT / "launchers" / "macos" / "Bundle File Tool Web.app" / "Contents"
    plist = (app / "Info.plist").read_text(encoding="utf-8")
    executable = (app / "MacOS" / "bft-web").read_text(encoding="utf-8")
    assert "CFBundleExecutable" in plist and "bft-web" in plist
    assert "src/web_main.py" in executable
    assert "Bundle File Tool Web.app" in (
        ROOT / "scripts" / "install_macos.sh").read_text(encoding="utf-8")


def test_macos_setup_keeps_user_state_out_of_governed_config():
    setup = (ROOT / "scripts" / "install_macos.sh").read_text(encoding="utf-8")
    guide = (ROOT / "docs" / "MACOS_SETUP.md").read_text(encoding="utf-8")
    assert "bundle_config.json" not in setup
    assert "~/.config/bundle_file_tool/user_state.json" in guide
    assert "Startup logs" in guide


def test_package_metadata_declares_windows_and_macos():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    classifiers = set(project["project"]["classifiers"])
    assert "Operating System :: Microsoft :: Windows" in classifiers
    assert "Operating System :: MacOS" in classifiers
