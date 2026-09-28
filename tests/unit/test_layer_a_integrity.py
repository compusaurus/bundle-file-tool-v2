# BFT_B109_LAYER_A_INTEGRITY_TESTS
# ============================================================================
# SOURCEFILE: test_layer_a_integrity.py
# RELPATH: bundle_file_tool_v2/tests/unit/test_layer_a_integrity.py
# PROJECT: Bundle File Tool v2.1
# VERSION: 2.1.109
# LIFECYCLE: Testing
# STATUS: Build 109 - BFT_B109_LAYER_A_INTEGRITY_TESTS
# ============================================================================
"""Layer A: the governed configuration reports when something else wrote it.

`ARCH-RULING-2026-08-23-02` §3.4 step 4. Layer D removes stale copies and Layer
C blocks their writes; Layer A is what speaks up when one gets through anyway.

The motivation is concrete. The fourth configuration drift cost an afternoon of
forensics — reconstructing the writer from file timestamps, a bundle's archived
copy and a window-geometry string — because nothing recorded what happened. The
requirement here is modest and specific: a fifth occurrence should name its own
cause at the moment it is noticed.

Paul's refinement (`BFT-ANALYSIS-2026-08-23-01` §5) sets the payload: expected
and actual digest, application version, executable path and timestamp, and no
unnecessary user data.
"""

from __future__ import annotations

import json
import os
import re
import stat
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

import pytest

from core.config import ConfigManager

SRC = Path(__file__).resolve().parents[2] / "src"


@contextmanager
def governed_config_temporarily(content: bytes):
    """Swap the governed config, then put it back exactly as it was.

    Layer C makes the installed configuration read-only, so a test that writes
    it must clear the attribute first and restore it afterwards. Without this
    the suite would pass in development and fail the moment it is re-run on an
    installed tree — which is precisely when someone would run it.
    """
    governed = ConfigManager.governed_config_path()
    original = governed.read_bytes()
    was_readonly = not os.access(governed, os.W_OK)
    try:
        if was_readonly:
            governed.chmod(stat.S_IWRITE | stat.S_IREAD)
        governed.write_bytes(content)
        yield governed
    finally:
        try:
            governed.chmod(stat.S_IWRITE | stat.S_IREAD)
            governed.write_bytes(original)
        finally:
            if was_readonly:
                governed.chmod(stat.S_IREAD)


# ---------------------------------------------------------------------------
# 1. The baseline is recorded and correct
# ---------------------------------------------------------------------------

def test_the_manifest_records_a_digest_for_the_governed_config():
    expected = ConfigManager.expected_config_digest()
    assert expected is not None, "no governed_config_sha256 recorded in the manifest"
    assert re.fullmatch(r"[0-9a-f]{64}", expected)


def test_the_recorded_digest_matches_the_shipped_configuration():
    """The delivered config and its recorded digest must agree at rest."""
    actual = ConfigManager.file_digest(ConfigManager.governed_config_path())
    assert actual == ConfigManager.expected_config_digest()


def test_a_clean_installation_reports_no_finding():
    assert ConfigManager().check_config_integrity() is None


# ---------------------------------------------------------------------------
# 2. Tampering is detected, with a usable payload
# ---------------------------------------------------------------------------

def test_a_modified_configuration_is_detected(tmp_path, monkeypatch):
    """The Layer A scenario, reproduced: the file changes underneath us."""
    governed = tmp_path / "bundle_config.json"
    original = ConfigManager.governed_config_path().read_bytes()
    governed.write_bytes(original)

    monkeypatch.setattr(ConfigManager, "governed_config_path",
                        staticmethod(lambda: governed))
    manager = ConfigManager()
    assert manager.check_config_integrity() is None, "clean copy should be quiet"

    # what a stale writer does
    drifted = json.loads(original.decode("utf-8"))
    drifted["version"] = "2.1.0"
    drifted["safety"]["allow_globs"] = ["**/*.py", "**/*.txt"]
    governed.write_text(json.dumps(drifted, indent=2) + "\n", encoding="utf-8")

    finding = manager.check_config_integrity()
    assert finding is not None, "a rewritten governed config was not detected"
    assert finding["expected_sha256"] == ConfigManager.expected_config_digest()
    assert finding["actual_sha256"] != finding["expected_sha256"]


def test_the_finding_carries_everything_paul_asked_for(tmp_path, monkeypatch):
    governed = tmp_path / "bundle_config.json"
    governed.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(ConfigManager, "governed_config_path",
                        staticmethod(lambda: governed))

    finding = ConfigManager().check_config_integrity()
    assert finding is not None

    assert set(finding) == {
        "path", "expected_sha256", "actual_sha256",
        "application_version", "executable", "observed_utc",
    }
    assert finding["executable"] == sys.executable
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", finding["observed_utc"])
    from core.version import __version__
    assert finding["application_version"] == __version__


def test_the_alert_text_is_operator_readable(tmp_path, monkeypatch):
    governed = tmp_path / "bundle_config.json"
    governed.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(ConfigManager, "governed_config_path",
                        staticmethod(lambda: governed))

    lines = ConfigManager.format_integrity_alert(ConfigManager().check_config_integrity())
    joined = "\n".join(lines)

    assert lines[0].startswith("WARNING:")
    assert "expected" in joined and "actual" in joined
    assert "Reinstall the delivery kit" in joined


# ---------------------------------------------------------------------------
# 3. Absence of a baseline is not tampering
# ---------------------------------------------------------------------------

def test_a_missing_baseline_is_silent(tmp_path, monkeypatch):
    """An installation predating Layer A must not be reported as compromised.

    False alarms are how a warning becomes background noise, and this one has to
    still mean something the fifth time.
    """
    empty = tmp_path / "project_manifest.json"
    empty.write_text(json.dumps({"governance": {}}) + "\n", encoding="utf-8")
    monkeypatch.setattr(ConfigManager, "governed_manifest_path",
                        staticmethod(lambda: empty))

    assert ConfigManager.expected_config_digest() is None
    assert ConfigManager().check_config_integrity() is None


def test_an_unreadable_manifest_is_silent(tmp_path, monkeypatch):
    broken = tmp_path / "project_manifest.json"
    broken.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(ConfigManager, "governed_manifest_path",
                        staticmethod(lambda: broken))

    assert ConfigManager.expected_config_digest() is None
    assert ConfigManager().check_config_integrity() is None


def test_developer_scope_configurations_are_never_checked(tmp_path):
    """An explicit path is test/tooling scope; it has no governed digest."""
    scratch = tmp_path / "bundle_config.json"
    scratch.write_text("{}\n", encoding="utf-8")
    assert ConfigManager(str(scratch)).check_config_integrity() is None


# ---------------------------------------------------------------------------
# 4. It can never break the operation it observes
# ---------------------------------------------------------------------------

def test_integrity_checking_never_raises(tmp_path, monkeypatch):
    """Same guarantee the progress sink has, for the same reason."""
    monkeypatch.setattr(ConfigManager, "governed_manifest_path",
                        staticmethod(lambda: tmp_path / "does-not-exist.json"))
    assert ConfigManager().check_config_integrity() is None

    def explode():
        raise RuntimeError("boom")

    monkeypatch.setattr(ConfigManager, "expected_config_digest",
                        classmethod(lambda cls: explode()))
    assert ConfigManager().check_config_integrity() is None


def test_the_cli_still_succeeds_when_the_config_has_been_tampered_with(tmp_path):
    """A drifted config produces a loud warning and a working command."""
    source = tmp_path / "tree"
    source.mkdir()
    (source / "a.txt").write_text("alpha\n", encoding="utf-8")

    drifted = json.loads(
        ConfigManager.governed_config_path().read_text(encoding="utf-8"))
    drifted["global_settings"]["log_dir"] = "logs_tampered"
    payload = (json.dumps(drifted, indent=2) + "\n").encode("utf-8")

    with governed_config_temporarily(payload):
        result = subprocess.run(
            [sys.executable, "-m", "cli", "bundle", str(source),
             "--base-path", str(source), "--profile", "plain_marker",
             "-o", str(tmp_path / "out.txt"), "--progress", "none"],
            cwd=str(SRC), capture_output=True, text=True,
            env={**os.environ, "PYTHONPATH": str(SRC)},
        )

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "out.txt").is_file(), "the operation must still complete"
    assert "does not match its recorded digest" in result.stderr
    assert "Reinstall the delivery kit" in result.stderr


def test_the_integrity_alert_goes_to_stderr_not_stdout(tmp_path):
    """stdout carries the artifact; Build 105's rule holds for Layer A too."""
    source = tmp_path / "tree"
    source.mkdir()
    (source / "a.txt").write_text("alpha\n", encoding="utf-8")

    drifted = json.loads(
        ConfigManager.governed_config_path().read_text(encoding="utf-8"))
    drifted["global_settings"]["log_dir"] = "logs_tampered"
    payload = (json.dumps(drifted, indent=2) + "\n").encode("utf-8")

    with governed_config_temporarily(payload):
        result = subprocess.run(
            [sys.executable, "-m", "cli", "bundle", str(source),
             "--base-path", str(source), "--profile", "plain_marker",
             "--progress", "none"],
            cwd=str(SRC), capture_output=True, text=True,
            env={**os.environ, "PYTHONPATH": str(SRC)},
        )

    assert result.returncode == 0, result.stderr
    assert "WARNING" not in result.stdout
    assert "sha256" not in result.stdout.lower()
    assert result.stdout.lstrip().startswith("#"), "stdout must carry only the bundle"
    assert "does not match its recorded digest" in result.stderr


# ---------------------------------------------------------------------------
# BFT_B115_NONMODAL_INTEGRITY_ALERT - the alert must never block startup
# ---------------------------------------------------------------------------

def test_the_gui_integrity_alert_uses_no_blocking_dialog():
    """The GUI must report drift without waiting for a click.

    `_report_config_integrity` has always been documented as "never blocks
    startup", and until Build 115 it called `messagebox.showwarning()` - which
    blocks until dismissed. Any unattended launch with a drifted config hung:
    one test run spent 265 seconds sitting on that dialog, and in the field it
    would have been a hang rather than a slow test.

    George's Build 109 ruling still stands - the alert must reach the GUI - so
    it is now a persistent banner, which cannot be dismissed and forgotten
    while the drift is still present.
    """
    import ast
    import pathlib

    source = pathlib.Path("src/ui/main_window.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    reporter = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name == "_report_config_integrity"
    )
    called = {
        f"{ast.unparse(node.func)}"
        for node in ast.walk(reporter) if isinstance(node, ast.Call)
    }
    blocking = {name for name in called if "showwarning" in name
                or "showerror" in name or "askyesno" in name}
    assert not blocking, (
        f"_report_config_integrity calls a modal dialog: {sorted(blocking)}")


def test_the_alert_still_reaches_stderr_and_the_gui():
    """Making it non-blocking must not make it quieter."""
    import pathlib

    source = pathlib.Path("src/ui/main_window.py").read_text(encoding="utf-8")
    start = source.index("def _report_config_integrity")
    body = source[start:source.index("def _show_integrity_banner")]
    assert "file=sys.stderr" in body, "the alert no longer reaches stderr"
    assert "_show_integrity_banner" in body, "the alert no longer reaches the GUI"
