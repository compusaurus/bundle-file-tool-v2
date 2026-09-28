# ============================================================================
# SOURCEFILE: test_user_state.py
# RELPATH: bundle_file_tool_v2/tests/unit/test_user_state.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.104
# LIFECYCLE: Testing
# STATUS: Build 104 - BFT_B104_USER_STATE_TESTS
# DESCRIPTION: UserStateStore - the mutable half of the R-BFT-01 config split.
# ============================================================================
"""Tests for the user-state store introduced by R-BFT-01."""

import json
import os

import pytest

from core.config import ConfigManager
from core.exceptions import ReadOnlyConfigError
from core.user_state import (
    PORTABLE_ENV_VAR,
    PORTABLE_FILENAME,
    STATE_FILENAME,
    UserStateStore,
)


@pytest.fixture
def state_file(tmp_path):
    return tmp_path / "user_state.json"


# ---------------------------------------------------------------------------
# Round trip
# ---------------------------------------------------------------------------

def test_defaults_when_no_file(state_file):
    store = UserStateStore(str(state_file))
    assert store.get("window_geometry") == "1000x700"
    assert store.get("first_launch") is True
    assert store.get("last_source_dir") == ""
    assert store.get("last_bundle_open_dir") == ""
    assert store.startup_mode() == "restore"
    assert store.last_non_minimized_state() == "normal"
    assert store.get("remember_window_geometry") is True
    assert store.get("check_selection_before_create") is True
    assert store.get("check_bundle_on_load") is True
    assert store.get("check_before_extract") is True
    assert store.get("verify_output_after_create") is True
    assert not state_file.exists()          # reading must not create the file


def test_save_and_reload(state_file):
    store = UserStateStore(str(state_file))
    store.set("window_geometry", "1902x980+2+30")
    store.set("last_source_dir", r"C:/some/where")
    assert store.save() is True

    reloaded = UserStateStore(str(state_file))
    assert reloaded.get("window_geometry") == "1902x980+2+30"
    assert reloaded.get("last_source_dir") == r"C:/some/where"


def test_set_and_save_is_atomic_helper(state_file):
    store = UserStateStore(str(state_file))
    assert store.set_and_save("last_bundle_save_dir", r"D:/bundles") is True
    assert json.loads(state_file.read_text(encoding="utf-8"))["last_bundle_save_dir"] == r"D:/bundles"


def test_parent_directory_is_created(tmp_path):
    nested = tmp_path / "BundleFileTool" / STATE_FILENAME
    store = UserStateStore(str(nested))
    store.set("first_launch", False)
    assert store.save() is True
    assert nested.exists()


# ---------------------------------------------------------------------------
# Robustness - convenience state must never break the application
# ---------------------------------------------------------------------------

def test_corrupt_state_file_falls_back_to_defaults(state_file):
    state_file.write_text("{not json at all", encoding="utf-8")
    store = UserStateStore(str(state_file))
    assert store.get("window_geometry") == "1000x700"


def test_unknown_keys_in_file_are_ignored(state_file):
    state_file.write_text(json.dumps({"window_geometry": "800x600", "safety": "nope"}),
                          encoding="utf-8")
    store = UserStateStore(str(state_file))
    assert store.get("window_geometry") == "800x600"
    assert "safety" not in store.state


def test_save_failure_is_reported_not_raised(tmp_path):
    # a directory where the file should be makes the write fail
    blocked = tmp_path / "user_state.json"
    blocked.mkdir()
    store = UserStateStore(str(blocked))
    assert store.save() is False


# ---------------------------------------------------------------------------
# Ownership boundary
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("key", ["safety.allow_globs", "version", "app_defaults.encoding"])
def test_governed_keys_are_rejected(state_file, key):
    store = UserStateStore(str(state_file))
    with pytest.raises(KeyError):
        store.set(key, "x")
    with pytest.raises(KeyError):
        store.get(key)


def test_store_owns_only_the_declared_convenience_keys(state_file):
    assert set(UserStateStore.KEYS) == {
        "workspace_list_rule_matches",
        "workspace_layout",
        "last_source_dir",
        "last_bundle_open_dir",
        "last_bundle_save_dir",
        "window_geometry",
        "remember_window_geometry",
        "window_monitor",
        "startup_mode",
        "last_window_state",
        "last_non_minimized_geometry",
        "last_non_minimized_state",
        "check_selection_before_create",
        "check_bundle_on_load",
        "check_before_extract",
        "verify_output_after_create",
        "web_skin",
        "workspace_show_selections",
        "workspace_show_rules",
        "workspace_show_result_set",
        "workspace_show_guidance",
        "first_launch",
    }


def test_malformed_window_states_fall_back_to_visible_defaults(state_file):
    state_file.write_text(json.dumps({
        "startup_mode": "teleport",
        "last_non_minimized_state": "minimized",
    }), encoding="utf-8")

    store = UserStateStore(str(state_file))
    assert store.startup_mode() == "restore"
    assert store.last_non_minimized_state() == "normal"


# ---------------------------------------------------------------------------
# Location resolution
# ---------------------------------------------------------------------------

def test_portable_mode_uses_working_directory(monkeypatch, tmp_path):
    monkeypatch.setenv(PORTABLE_ENV_VAR, "1")
    monkeypatch.chdir(tmp_path)
    assert UserStateStore.resolve_path() == tmp_path / PORTABLE_FILENAME


def test_default_location_is_outside_the_project(monkeypatch, tmp_path):
    monkeypatch.delenv(PORTABLE_ENV_VAR, raising=False)
    resolved = UserStateStore.resolve_path()
    assert resolved.name == STATE_FILENAME
    if os.name == "nt":
        assert "BundleFileTool" in resolved.parts
    else:
        assert "bundle_file_tool" in resolved.parts


# ---------------------------------------------------------------------------
# Migration, and the defect this whole split exists to prevent
# ---------------------------------------------------------------------------

def test_seed_from_pre_104_config(state_file):
    legacy = {
        "global_settings": {"last_source_dir": r"C:/old/src", "last_bundle_save_dir": ""},
        "session": {"window_geometry": "1200x900+0+0", "first_launch": False},
    }
    store = UserStateStore(str(state_file))
    assert store.seed_from_config(legacy) is True
    assert store.get("last_source_dir") == r"C:/old/src"
    assert store.get("window_geometry") == "1200x900+0+0"
    assert store.get("first_launch") is False
    assert state_file.exists()


def test_seed_does_not_run_twice(state_file):
    store = UserStateStore(str(state_file))
    store.set_and_save("window_geometry", "999x999")
    assert store.seed_from_config({"session": {"window_geometry": "111x111"}}) is False
    assert UserStateStore(str(state_file)).get("window_geometry") == "999x999"


def test_governed_config_is_untouched_by_a_full_state_cycle(tmp_path):
    """The Build 103 regression, reproduced against the Build 104 architecture.

    A GUI session storing a window geometry previously rewrote the whole
    governed document, taking the ratified D-005 safety block with it.
    """
    config_file = tmp_path / "bundle_config.json"
    ConfigManager(str(config_file))                     # creates the default document
    before = config_file.read_text(encoding="utf-8")

    store = UserStateStore(str(tmp_path / "user_state.json"))
    store.set("window_geometry", "1902x980+2+30")
    store.set("last_source_dir", str(tmp_path))
    store.save()

    assert config_file.read_text(encoding="utf-8") == before

    reloaded = ConfigManager(str(config_file))
    assert reloaded.get("safety.allow_globs") == ["**/*"]
    with pytest.raises(ReadOnlyConfigError):
        reloaded.save()
