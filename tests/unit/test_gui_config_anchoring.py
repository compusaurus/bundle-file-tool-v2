# BFT_B109_GUI_CONFIG_ANCHORING_TESTS
# ============================================================================
# SOURCEFILE: test_gui_config_anchoring.py
# RELPATH: bundle_file_tool_v2/tests/unit/test_gui_config_anchoring.py
# PROJECT: Bundle File Tool v2.1
# VERSION: 2.1.109
# LIFECYCLE: Testing
# STATUS: Build 109 - BFT_B109_GUI_CONFIG_ANCHORING_TESTS
# ============================================================================
"""F-02: the GUI must address the same governed configuration as everything else.

Paul's finding, ratified by George as a hard prerequisite to Layer C
(`ARCH-RULING-2026-08-23-02` §3.4): Build 105 anchored `ConfigManager()` to the
application root, but `BundleFileToolApp.__init__` still passed an explicit
relative name:

    ConfigManager("bundle_config.json")

`ConfigManager` treats an explicit path as developer/test scope — it resolves
against the process working directory and *may create the file*. So the primary
user-facing surface could read, and cause the creation of, a different document
from the one the CLI reads and the installer governs.

Why this had to land before the filesystem protection: `attrib +R` on the
installed file protects nothing if the application is using a different,
unprotected file. That combination is worse than no protection, because it
looks hardened.

These tests were written to fail against Build 108 and pass after the fix.
"""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from core.config import ConfigManager

SRC = Path(__file__).resolve().parents[2] / "src"
ROOT = SRC.parent


# ---------------------------------------------------------------------------
# 1. The construction contract, checked statically
# ---------------------------------------------------------------------------

def test_no_ui_module_constructs_configmanager_with_an_explicit_path():
    """Every UI surface must use the governed, no-argument constructor.

    Static rather than behavioural on purpose: this is the contract that
    regressed, and an AST check catches it in any UI module, including ones
    written after this build.
    """
    offenders = []
    for module in sorted((SRC / "ui").rglob("*.py")):
        tree = ast.parse(module.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "ConfigManager"
                    and (node.args or node.keywords)):
                offenders.append(f"{module.name}:{node.lineno}")

    assert not offenders, (
        "UI modules must call ConfigManager() with no arguments so the governed "
        f"document is resolved from the application root. Offenders: {offenders}"
    )


# ---------------------------------------------------------------------------
# 2. The behaviour that contract buys
# ---------------------------------------------------------------------------

def test_governed_manager_anchors_from_any_working_directory(tmp_path, monkeypatch):
    """Resolution is a property of the installation, not of the launch directory."""
    expected = ConfigManager.governed_config_path()

    for cwd in (ROOT, SRC, tmp_path):
        monkeypatch.chdir(cwd)
        manager = ConfigManager()
        assert manager.is_governed is True
        assert manager.config_file == expected, f"drifted when launched from {cwd}"


def test_governed_manager_creates_nothing_in_the_working_directory(tmp_path, monkeypatch):
    """The failure mode this closes: a governed-looking file appearing in the CWD."""
    monkeypatch.chdir(tmp_path)
    ConfigManager()
    assert not (tmp_path / "bundle_config.json").exists(), (
        "a config was created in the working directory"
    )


def test_the_explicit_path_form_still_behaves_as_developer_scope(tmp_path, monkeypatch):
    """The escape hatch is retained deliberately, so the contract above matters.

    `ConfigManager("bundle_config.json")` is legitimate for tests and tooling.
    It is *not* legitimate for a shipped UI surface, which is exactly why the
    static check above exists rather than removing the parameter.
    """
    monkeypatch.chdir(tmp_path)
    manager = ConfigManager("bundle_config.json")
    assert manager.is_governed is False
    assert manager.config_file.resolve() == (tmp_path / "bundle_config.json").resolve()


# ---------------------------------------------------------------------------
# 3. End to end: the real application object
# ---------------------------------------------------------------------------

_APP_PROBE = """
import json, os, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
os.chdir(sys.argv[2])
try:
    import tkinter
    tkinter.Tk().destroy()
except Exception as error:
    print(json.dumps({"skip": str(error)}))
    raise SystemExit(0)
from ui.main_window import BundleFileToolApp
app = BundleFileToolApp()
app.withdraw()
manager = app.config_manager
print(json.dumps({
    "is_governed": bool(getattr(manager, "is_governed", False)),
    "config_file": str(getattr(manager, "config_file", "")),
    "created_in_cwd": Path(os.getcwd(), "bundle_config.json").exists(),
}))
app.destroy()
"""


def test_the_real_app_anchors_when_launched_from_an_unrelated_directory(tmp_path):
    """Constructs the actual BundleFileToolApp with an unrelated working directory.

    Runs as a subprocess for two reasons: it needs its own working directory,
    and a second Tk root in the pytest process destabilises Tcl.
    """
    probe = tmp_path / "probe.py"
    probe.write_text(_APP_PROBE, encoding="utf-8")
    workdir = tmp_path / "elsewhere"
    workdir.mkdir()

    result = subprocess.run(
        [sys.executable, str(probe), str(SRC), str(workdir)],
        capture_output=True, text=True,
        env={**os.environ, "PYTHONPATH": str(SRC)},
    )
    assert result.returncode == 0, result.stderr

    payload = json.loads(result.stdout.strip().splitlines()[-1])
    if "skip" in payload:
        pytest.skip(f"no usable display: {payload['skip']}")

    assert payload["is_governed"] is True, (
        "the GUI built a developer-scope ConfigManager; it must use the governed one"
    )
    assert Path(payload["config_file"]) == ConfigManager.governed_config_path()
    assert payload["created_in_cwd"] is False, (
        "the GUI created a config in its working directory"
    )


# ---------------------------------------------------------------------------
# 4. Drift reporting must be reachable from the GUI path too
# ---------------------------------------------------------------------------

def test_the_governed_manager_exposes_drift_findings_to_any_surface():
    """Build 105 added drift reporting; it is only useful where the UI can see it."""
    manager = ConfigManager()
    findings = manager.check_governed_policy()
    assert isinstance(findings, list)
    assert findings == [], f"the live governed config has drifted: {findings}"
