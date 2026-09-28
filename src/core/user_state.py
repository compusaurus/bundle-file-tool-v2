# ===================================================================================================
# SOURCEFILE: user_state.py
# RELPATH: bundle_file_tool_v2/src/core/user_state.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.104
# LIFECYCLE: Testing
# STATUS: Build 104 - BFT_B104_USER_STATE_STORE
# DESCRIPTION: Mutable per-user convenience state, held outside the governed
#              delivery payload. Ratified as R-BFT-01 (George, 2026-08-18).
# Relative Path: src/core/user_state.py
# Purpose:
# independent_entry_point:
# ===================================================================================================
"""User convenience state, stored outside the governed configuration.

`bundle_config.json` is a delivery payload: the installer verifies its SHA256
before and after placement, and the release-contract test asserts its ratified
D-005 safety defaults. Before Build 104 it was also the application's scratchpad
- the GUI wrote a window geometry and the last-used folders straight into it, and
because the writer serialised the whole document, saving a window position
rewrote the safety block as a side effect. The governed values were lost twice in
five days.

R-BFT-01 splits the two roles. Governed defaults stay in `bundle_config.json`,
read-only at runtime. Everything below lives here instead.

Storage location:

    Windows        %LOCALAPPDATA%\\BundleFileTool\\user_state.json
    POSIX / macOS  $XDG_CONFIG_HOME/bundle_file_tool/user_state.json
                   or ~/.config/bundle_file_tool/user_state.json
    Portable       .bft_user_state.json in the working directory,
                   when BFT_PORTABLE=1

User state is never written to the application root outside portable mode.
Writing there causes self-bundling contamination, a dirty working tree and
installer signature invalidation.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

APP_DIR_NAME = "BundleFileTool"
POSIX_DIR_NAME = "bundle_file_tool"
STATE_FILENAME = "user_state.json"
PORTABLE_FILENAME = ".bft_user_state.json"
PORTABLE_ENV_VAR = "BFT_PORTABLE"
STARTUP_MODES = ("restore", "normal", "maximized", "minimized")
NON_MINIMIZED_STATES = ("normal", "maximized")


class UserStateStore:
    """Load, mutate and persist per-user convenience state.

    Failures are non-fatal by design. Remembering a folder is a convenience; it
    must never take down an operation that would otherwise have succeeded.
    """

    #: Keys this store owns. Anything not listed here belongs to the governed config.
    KEYS = (
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
        "workspace_list_rule_matches",
        "workspace_layout",
        "first_launch",
    )

    DEFAULTS: Dict[str, Any] = {
        "last_source_dir": "",
        "last_bundle_open_dir": "",
        "last_bundle_save_dir": "",
        "window_geometry": "1000x700",
        "remember_window_geometry": True,
        "window_monitor": "",
        "startup_mode": "restore",
        "last_window_state": "normal",
        "last_non_minimized_geometry": "1000x700",
        "last_non_minimized_state": "normal",
        "check_selection_before_create": True,
        "check_bundle_on_load": True,
        "check_before_extract": True,
        "verify_output_after_create": True,
        "web_skin": "studio",
        "workspace_show_selections": True,
        "workspace_list_rule_matches": True,
        "workspace_layout": "Tabs",
        "workspace_show_rules": False,
        "workspace_show_result_set": False,
        "workspace_show_guidance": True,
        "first_launch": True,
    }

    #: Where these keys used to live inside bundle_config.json, for one-time seeding.
    LEGACY_PATHS = {
        "last_source_dir": ("global_settings", "last_source_dir"),
        "last_bundle_save_dir": ("global_settings", "last_bundle_save_dir"),
        "window_geometry": ("session", "window_geometry"),
        "first_launch": ("session", "first_launch"),
    }

    def __init__(self, state_file: Optional[str] = None) -> None:
        self.state_file = Path(state_file) if state_file else self.resolve_path()
        self.state: Dict[str, Any] = dict(self.DEFAULTS)
        self.load()

    # -----------------------------------------------------------------
    # Location
    # -----------------------------------------------------------------

    @staticmethod
    def resolve_path() -> Path:
        """Return the platform-appropriate user-state path."""
        if os.environ.get(PORTABLE_ENV_VAR) == "1":
            return Path.cwd() / PORTABLE_FILENAME

        if os.name == "nt":
            base = os.environ.get("LOCALAPPDATA")
            if base:
                return Path(base) / APP_DIR_NAME / STATE_FILENAME
            return Path.home() / "AppData" / "Local" / APP_DIR_NAME / STATE_FILENAME

        xdg = os.environ.get("XDG_CONFIG_HOME")
        base_dir = Path(xdg) if xdg else Path.home() / ".config"
        return base_dir / POSIX_DIR_NAME / STATE_FILENAME

    # -----------------------------------------------------------------
    # Persistence
    # -----------------------------------------------------------------

    def load(self) -> Dict[str, Any]:
        """Read state from disk, falling back to defaults for anything absent."""
        if not self.state_file.exists():
            return self.state

        try:
            raw = json.loads(self.state_file.read_text(encoding="utf-8"))
        except Exception:
            # A corrupt state file must not stop the application starting.
            return self.state

        if isinstance(raw, dict):
            for key in self.KEYS:
                if key in raw:
                    self.state[key] = raw[key]
        return self.state

    def save(self) -> bool:
        """Write state to disk. Returns True on success, False on failure.

        Never raises: persisting a window position is a convenience, not a
        precondition for anything.
        """
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            text = json.dumps(self.state, indent=2, ensure_ascii=False)
            self.state_file.write_text(text, encoding="utf-8")
            return True
        except Exception:
            return False

    # -----------------------------------------------------------------
    # Access
    # -----------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        if key not in self.KEYS:
            raise KeyError(
                f"'{key}' is not user state. Governed settings are read through "
                "ConfigManager and are not writable at runtime."
            )
        return self.state.get(key, self.DEFAULTS.get(key, default))

    def set(self, key: str, value: Any) -> None:
        if key not in self.KEYS:
            raise KeyError(
                f"'{key}' is not user state. Governed settings are read through "
                "ConfigManager and are not writable at runtime."
            )
        self.state[key] = value

    def set_and_save(self, key: str, value: Any) -> bool:
        self.set(key, value)
        return self.save()

    def startup_mode(self) -> str:
        """Return a supported launch choice, falling back safely to Restore."""
        value = str(self.get("startup_mode", "restore")).strip().lower()
        return value if value in STARTUP_MODES else "restore"

    def last_non_minimized_state(self) -> str:
        """Return the remembered visible state, never an invisible one."""
        value = str(
            self.get("last_non_minimized_state", "normal")).strip().lower()
        return value if value in NON_MINIMIZED_STATES else "normal"

    # -----------------------------------------------------------------
    # Migration
    # -----------------------------------------------------------------

    def seed_from_config(self, config: Dict[str, Any]) -> bool:
        """One-time seed from convenience keys left in a pre-104 config document.

        Only runs when no state file exists yet. The governed configuration is
        read, never written.
        """
        if self.state_file.exists():
            return False

        seeded = False
        for key, (section, name) in self.LEGACY_PATHS.items():
            value = (config or {}).get(section, {}).get(name)
            if value not in (None, ""):
                self.state[key] = value
                seeded = True

        self.save()
        return seeded
