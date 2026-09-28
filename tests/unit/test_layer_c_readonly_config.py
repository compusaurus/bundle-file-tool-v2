# BFT_B109_LAYER_C_READONLY_CONFIG
# ============================================================================
# SOURCEFILE: test_layer_c_readonly_config.py
# RELPATH: bundle_file_tool_v2/tests/unit/test_layer_c_readonly_config.py
# PROJECT: Bundle File Tool v2.1
# VERSION: 2.1.109
# LIFECYCLE: Testing
# STATUS: Build 109 - BFT_B109_LAYER_C_READONLY_CONFIG
# ============================================================================
"""Layer C: the application must behave correctly on a write-protected config.

`ARCH-RULING-2026-08-23-02` §3.4 ratifies filesystem write-protection on the
governed configuration. The installer applies it; these tests cover the half
that lives in the application.

The point of Layer C is that a stale, foreign writer meets a hard
`PermissionError` from the operating system before it can rewrite a byte. That
only helps if the *current* build reads such a file perfectly happily, and if
our own read-only guard still fires ahead of the filesystem's — an application
that started reporting `PermissionError` instead of `ReadOnlyConfigError` would
be reporting the symptom rather than the rule.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from core.config import ConfigManager
from core.exceptions import ReadOnlyConfigError

SRC = Path(__file__).resolve().parents[2] / "src"


def _write_protect(path: Path) -> None:
    """Apply the OS read-only attribute, the way the installer will."""
    path.chmod(stat.S_IREAD)


def _unprotect(path: Path) -> None:
    path.chmod(stat.S_IWRITE | stat.S_IREAD)


@pytest.fixture
def protected_config(tmp_path):
    """A governed-shaped config file carrying the read-only attribute."""
    source = json.loads(ConfigManager.governed_config_path().read_text(encoding="utf-8"))
    target = tmp_path / "bundle_config.json"
    target.write_text(json.dumps(source, indent=2) + "\n", encoding="utf-8")
    _write_protect(target)
    yield target
    _unprotect(target)          # so pytest can clean the temp tree up


def test_a_write_protected_config_still_loads_completely(protected_config):
    """Read access is unaffected; every governed value is present."""
    manager = ConfigManager(str(protected_config))

    assert manager.get("safety.allow_globs") == ["**/*"]
    assert "**/*.whl" in manager.get("safety.deny_globs")
    assert manager.get("ui.progress.enabled") is True
    assert manager.check_governed_policy() == []


def test_our_own_guard_still_fires_ahead_of_the_filesystem(protected_config):
    """`save()` must raise ReadOnlyConfigError, not PermissionError.

    The distinction matters for diagnosis. `ReadOnlyConfigError` says "this
    document is governed and the application refuses to write it".
    `PermissionError` says "the filesystem stopped you", which is true but
    tells an operator nothing about why the rule exists.
    """
    manager = ConfigManager(str(protected_config))
    manager.set("app_defaults.bundle_profile", "md_fence")

    with pytest.raises(ReadOnlyConfigError):
        manager.save()


def test_the_os_attribute_actually_blocks_a_foreign_writer(protected_config):
    """The threat model, reproduced directly.

    This is what a stale pre-Build-104 copy does: an ordinary open-for-write on
    the governed path. Layer C's whole value is that this raises before any
    content is replaced.
    """
    original = protected_config.read_bytes()

    with pytest.raises(PermissionError):
        with open(protected_config, "w", encoding="utf-8") as handle:
            handle.write("{}")

    assert protected_config.read_bytes() == original, "content was modified"


def test_protection_survives_a_read_only_copy_and_restore(protected_config, tmp_path):
    """Rollback safety, which is where this quietly goes wrong.

    The installer backs the config up before replacing it. A read-only source
    copies fine, but the copy inherits the attribute, so a later restore of that
    backup fails unless the attribute is cleared first. Proving the mechanic
    here is what makes the installer's strip-before-restore step non-optional.
    """
    import shutil

    backup = tmp_path / "rollback" / "bundle_config.json"
    backup.parent.mkdir()
    shutil.copy2(protected_config, backup)

    assert not os.access(backup, os.W_OK), "the backup did not inherit protection"

    # restoring without clearing the attribute fails ...
    with pytest.raises(PermissionError):
        with open(backup, "w", encoding="utf-8") as handle:
            handle.write("{}")

    # ... and clearing it first is what the installer must do.
    _unprotect(backup)
    backup.write_text("{}", encoding="utf-8")
    assert backup.read_text(encoding="utf-8") == "{}"


def test_the_cli_runs_normally_against_a_write_protected_governed_config(tmp_path):
    """End to end: protection must not degrade ordinary operation."""
    governed = ConfigManager.governed_config_path()
    was_writable = os.access(governed, os.W_OK)
    source = tmp_path / "tree"
    source.mkdir()
    (source / "a.txt").write_text("alpha\n", encoding="utf-8")

    try:
        _write_protect(governed)
        result = subprocess.run(
            [sys.executable, "-m", "cli", "bundle", str(source),
             "--base-path", str(source), "--profile", "plain_marker",
             "-o", str(tmp_path / "out.txt"), "--progress", "none"],
            cwd=str(SRC), capture_output=True, text=True,
            env={**os.environ, "PYTHONPATH": str(SRC)},
        )
    finally:
        if was_writable:
            _unprotect(governed)

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "out.txt").is_file()
