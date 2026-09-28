# SOURCEFILE: config.py
# RELPATH: bundle_file_tool_v2/src/core/config.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.0
# LIFECYCLE: Proposed
# Status: Proposed
# DESCRIPTION: Configuration manager with v1.1.5 migration and unknown key preservation
# Relative Path: src/core/config.py
# Purpose:
# independent_entry_point:
# ===================================================================================================
# BFT_B104_READONLY_CONFIG - governed document is read-only at runtime (R-BFT-01)
# BFT_B105_GOVERNED_CONFIG_RESOLUTION - resolved from the application root

"""
Configuration Manager for Bundle File Tool v2.1.

Handles loading, saving, validating, and migrating configuration files.
Provides backward compatibility with v1.1.5 flat structure while supporting
the new v2.1 nested schema. Preserves unknown keys in global_settings.
"""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import shutil
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.exceptions import (
    ConfigError,
    ConfigLoadError,
    ConfigMigrationError,
    ConfigValidationError,
    ReadOnlyConfigError
)
from core.version import __version__


class _Unset:
    """Marker type for a configuration key that is absent altogether."""

    __slots__ = ()

    def __repr__(self) -> str:
        return "<unset>"


class ConfigManager:
    """
    Manages application configuration with migration support.
    
    Supports both v1.1.5 (flat) and v2.1 (nested) configuration formats,
    with automatic migration and backward compatibility. Preserves unknown
    keys in global_settings for forward compatibility.
    """
    
    # Default configuration for v2.1
    DEFAULT_CONFIG = {
        "version": __version__,
        "schema_version": "2.1",
        "global_settings": {
            "input_dir": "",
            "output_dir": "",
            "log_dir": "logs",
            "relative_base_path": "",
            "ui_layout": {
                "buttons_position": "bottom",
                "show_info_panel": True,
                "info_panel_position": "middle"
            }
        },
        "session": {
            "first_launch": True,
            "window_geometry": ""
        },
        "app_defaults": {
            "default_mode": "unbundle",
            "bundle_profile": "md_fence",
            "add_headers": True,
            "encoding": "auto",
            "eol": "auto",
            "overwrite_policy": "prompt",
            "dry_run_default": True,
            "treat_binary_as_base64": True
        },
        # Build 108: Tkinter progress. Configurable per Ringo's standing rule -
        # every surface the operator might want to tune is a config key, not a
        # constant. min_files exists because a modal dialog for eleven files is
        # worse than no dialog at all.
        "ui": {
            "progress": {
                "enabled": True,
                "min_files": 200,
                # Build 111: Open Bundle cannot use min_files - the entry count
                # is the result of the work being measured, not an input to it.
                # Size is the honest proxy and stat() has it before the read.
                "min_parse_mb": 2.0,
                "show_elapsed": True,
                "show_rate": True
            }
        },
        "safety": {
            "allow_globs": ["**/*"],
            # Build 110 (GOV-BFT-002, ARCH-RULING-2026-08-24-01 §3.3 Tier 1).
            # Tier 1 covers infrastructure that is never source: environments,
            # tool caches and backup trees. Each is written as `**/NAME/**` so
            # that discovery can prune the directory rather than walk it and
            # discard the contents - see writer.prunable_dir_names().
            # Tier 2 (deliverables/, reports/, htmlcov/) is deliberately absent:
            # those are project output directories and remain user-governed.
            "deny_globs": [
                "**/.venv/**", "**/.venv311/**", "**/.venv312/**",
                "**/.venv313/**", "**/venv/**",
                "**/__pycache__/**",
                "**/.pytest_cache/**", "**/.mypy_cache/**", "**/.ruff_cache/**",
                "**/node_modules/**",
                "**/*_bak*/**", "**/_legacy_backup/**",
                "**/.governance_backups/**", "**/_governance_backups/**",
                "**/archives/**",
                "*.log", "**/*_bundle_*.txt",
                "**/*.zip", "**/*.tar", "**/*.tar.*", "**/*.whl",
            ],
            "max_file_mb": 10
        }
    }
    
    # Known v1.1.5 keys that map to specific v2.1 locations
    V115_KEY_MAPPING = {
        "input_dir": ("global_settings", "input_dir"),
        "output_dir": ("global_settings", "output_dir"),
        "log_dir": ("global_settings", "log_dir"),
        "relative_base_path": ("global_settings", "relative_base_path"),
        "buttons_position": ("global_settings", "ui_layout", "buttons_position"),
        "show_info_panel": ("global_settings", "ui_layout", "show_info_panel"),
        "info_panel_position": ("global_settings", "ui_layout", "info_panel_position"),
        "first_launch": ("session", "first_launch"),
        "add_headers": ("app_defaults", "add_headers"),
    }
    
    #: Ratified policy invariants. Drift against these is reported, not silently
    #: tolerated - see check_governed_policy().
    GOVERNED_POLICY = {
        "safety.allow_globs": ["**/*"],
        "safety.deny_globs.contains": [
            "**/*_bundle_*.txt", "**/*.zip", "**/*.tar", "**/*.tar.*", "**/archives/**",
        ],
    }

    #: Sentinel for "key not present". Distinct from None so that a key which
    #: is present and explicitly null is still validated rather than silently
    #: replaced by its default - see _effective_value().
    _UNSET = _Unset()

    @staticmethod
    def governed_config_path() -> Path:
        """Resolve the governed configuration from the application root.

        Build 105. This used to default to a bare relative name, so the file
        resolved against the process working directory: launching from `src`, or
        from an unrelated directory, or launching a stale copy of the
        application with the live root as the working directory, all pointed at
        a different file than intended. The governed document is part of the
        delivery payload and its location is a property of the installation, not
        of how the process happened to be started.
        """
        return Path(__file__).resolve().parents[2] / "bundle_config.json"

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration manager.

        Args:
            config_file: Explicit path to a configuration file. When omitted the
                governed configuration is resolved from the application root.
                An explicit path is developer/test scope and may be created if
                absent; the governed document is never created implicitly.
        """
        self.is_governed = config_file is None
        self.config_file = (
            self.governed_config_path() if self.is_governed else Path(config_file)
        )
        self.config: Dict = {}
        self.version: str = "2.1"
        self._load_or_create()

    def _load_or_create(self) -> None:
        """Load the configuration, or fall back to packaged defaults.

        Build 105: a missing GOVERNED document yields read-only packaged
        defaults in memory and a warning on stderr. It is never created. Writing
        a governed-looking file into whatever directory the process happened to
        start in is how policy drift becomes invisible.
        """
        if self.config_file.exists():
            self.load()
        elif self.is_governed:
            print(
                f"Warning: governed configuration not found at {self.config_file}; "
                "using packaged defaults in memory. Reinstall to restore it.",
                file=sys.stderr,
            )
            self.config = self._deep_copy(self.DEFAULT_CONFIG)
        else:
            self.config = self._deep_copy(self.DEFAULT_CONFIG)
            self._create_default_file()

    # --- Layer A: integrity verification and telemetry ---------------------
    #
    # BFT_B109_LAYER_A_INTEGRITY. Layers D and C remove and block foreign
    # writers; this layer is what tells us when one got through anyway. It never
    # raises and never blocks the operation - the fourth config drift cost an
    # afternoon of forensics precisely because nothing recorded who wrote the
    # file, so the goal here is that a fifth occurrence names its own cause.

    @staticmethod
    def governed_manifest_path() -> Path:
        """The governed manifest, resolved from the application root."""
        return Path(__file__).resolve().parents[2] / ".pyprojectmgr" / "project_manifest.json"

    @staticmethod
    def file_digest(path: Path) -> Optional[str]:
        """SHA-256 of a file, or None when it cannot be read."""
        try:
            digest = hashlib.sha256()
            with Path(path).open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            return digest.hexdigest()
        except Exception:
            return None

    @classmethod
    def expected_config_digest(cls) -> Optional[str]:
        """The governed configuration digest recorded in the manifest.

        Returns None when the manifest is missing, unreadable, or does not
        record one. A missing record is not a violation: it means this
        installation predates Layer A, and an absent baseline must not be
        reported as tampering.
        """
        try:
            manifest = json.loads(cls.governed_manifest_path().read_text(encoding="utf-8"))
            value = manifest.get("governance", {}).get("governed_config_sha256")
            return value if isinstance(value, str) and len(value) == 64 else None
        except Exception:
            return None

    def check_config_integrity(self) -> Optional[Dict[str, str]]:
        """Compare the on-disk configuration against its governed digest.

        Returns:
            None when the file matches, when no baseline is recorded, or when
            this is a developer-scope configuration. Otherwise a telemetry
            record naming both digests and the process that observed the
            mismatch.
        """
        if not self.is_governed:
            return None
        try:
            expected = self.expected_config_digest()
            if expected is None:
                return None
            actual = self.file_digest(self.config_file)
            if actual is None or actual == expected:
                return None
            return {
                "path": str(self.config_file),
                "expected_sha256": expected,
                "actual_sha256": actual,
                "application_version": __version__,
                "executable": sys.executable,
                "observed_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        except Exception:
            # A diagnostic must never take down the command it is reporting on.
            return None

    @staticmethod
    def format_integrity_alert(finding: Dict[str, str]) -> List[str]:
        """Render a telemetry record as high-visibility operator lines."""
        return [
            "WARNING: the governed configuration does not match its recorded digest.",
            f"  file      : {finding['path']}",
            f"  expected  : {finding['expected_sha256']}",
            f"  actual    : {finding['actual_sha256']}",
            f"  app       : Bundle File Tool {finding['application_version']}",
            f"  observed  : {finding['observed_utc']} by {finding['executable']}",
            "  A process other than the installer has written this file.",
            "  Reinstall the delivery kit to restore it.",
        ]

    def check_governed_policy(self) -> List[str]:
        """Return a list of ratified-policy violations in the loaded config.

        Build 105. Governed policy drift has recurred three times; each time it
        was found by a test run rather than by the application, which happily
        used the drifted values. This reports it where the operator can see it.
        """
        findings: List[str] = []

        expected_allow = self.GOVERNED_POLICY["safety.allow_globs"]
        actual_allow = self.get("safety.allow_globs", None)
        if actual_allow != expected_allow:
            findings.append(
                f"safety.allow_globs is {actual_allow!r}, ratified value is {expected_allow!r}"
            )

        actual_deny = self.get("safety.deny_globs", []) or []
        missing = [d for d in self.GOVERNED_POLICY["safety.deny_globs.contains"]
                   if d not in actual_deny]
        if missing:
            findings.append(f"safety.deny_globs is missing ratified entries: {missing}")

        declared = self.get("version", None)
        if declared != __version__:
            findings.append(
                f"config version is {declared!r}, package version is {__version__!r}"
            )

        return findings

    def load(self) -> Dict:
        """
        Load configuration from file.
        
        Automatically detects format version and migrates if needed.
        
        Returns:
            Loaded configuration dictionary
            
        Raises:
            ConfigLoadError: If file cannot be loaded or parsed
        """
        try:
            text = self.config_file.read_text(encoding='utf-8')
            data = json.loads(text)
        except FileNotFoundError:
            raise ConfigLoadError(str(self.config_file), "File not found")
        except json.JSONDecodeError as e:
            raise ConfigLoadError(str(self.config_file), f"Invalid JSON: {str(e)}")
        except Exception as e:
            raise ConfigLoadError(str(self.config_file), str(e))
        
        # Detect version and migrate if needed
        if self._is_v115_format(data):
            data = self._migrate_from_v115(data)
        
        self.config = data
        return self.config
    
    def save(self) -> None:
        """
        Refuse to write the governed configuration.

        Build 104, R-BFT-01. `bundle_config.json` is a delivery payload: the
        installer verifies its SHA256 before and after placement and the
        release-contract test asserts its ratified D-005 safety defaults. It is
        read-only at runtime.

        Before Build 104 this method serialised the whole document, so the GUI
        persisting a window position rewrote the safety block as a side effect.
        The ratified defaults were lost twice in the five days after Build 103.

        User convenience state belongs in `UserStateStore` (core/user_state.py).
        Schema migration from v1.1.5 happens in memory on every load and is not
        persisted.

        Raises:
            ReadOnlyConfigError: always
        """
        raise ReadOnlyConfigError(str(self.config_file))

    def _create_default_file(self) -> None:
        """Write the default document, for a config file that does not exist yet.

        Creation only. This never overwrites an existing governed file, and is
        the sole write path remaining in this class.
        """
        try:
            text = json.dumps(self.config, indent=2, ensure_ascii=False)
            self.config_file.write_text(text, encoding='utf-8')
        except Exception as e:
            raise ConfigError(f"Failed to create config: {str(e)}")
    
    def _is_v115_format(self, data: Dict) -> bool:
        """
        Detect if configuration is in v1.1.5 flat format.
        
        Args:
            data: Configuration dictionary
            
        Returns:
            True if v1.1.5 format detected
        """
        # v1.1.5 format has flat keys, not nested sections
        v115_keys = {"input_dir", "output_dir", "log_dir", "buttons_position"}
        v21_keys = {"global_settings", "app_defaults", "safety"}
        
        has_v115_keys = any(key in data for key in v115_keys)
        has_v21_keys = any(key in data for key in v21_keys)
        
        # If it has v1.1.5 keys but not v2.1 keys, it's v1.1.5
        return has_v115_keys and not has_v21_keys
    
    def _migrate_from_v115(self, old_config: Dict) -> Dict:
        """
        Migrate v1.1.5 configuration to v2.1 format.
        
        Creates backup before migration. Maps known v1.1.5 keys to their
        v2.1 locations and preserves unknown keys in global_settings.
        
        Args:
            old_config: v1.1.5 configuration dictionary
            
        Returns:
            Migrated v2.1 configuration dictionary
            
        Raises:
            ConfigMigrationError: If migration fails
        """
        try:
            # Create backup
            self._create_backup()
            
            # Start with default v2.1 structure
            new_config = self._deep_copy(self.DEFAULT_CONFIG)
            
            # Track which keys we've processed
            processed_keys = set()
            
            # Migrate known v1.1.5 keys to their v2.1 locations
            for v115_key, v21_path in self.V115_KEY_MAPPING.items():
                if v115_key in old_config:
                    self._set_nested_value(new_config, v21_path, old_config[v115_key])
                    processed_keys.add(v115_key)
            
            # Preserve unknown keys in global_settings (Option A - Approved by Ringo)
            for key, value in old_config.items():
                if key not in processed_keys:
                    # Unknown key - preserve it in global_settings
                    new_config["global_settings"][key] = value
            
            return new_config
            
        except Exception as e:
            raise ConfigMigrationError("1.1.5", "2.1", str(e))
    
    def _set_nested_value(self, config: Dict, path: tuple, value: Any) -> None:
        """
        Set a value at a nested path in the config dictionary.
        
        Args:
            config: Configuration dictionary to modify
            path: Tuple of keys representing the path
            value: Value to set
        """
        current = config
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[path[-1]] = value
    
    def _create_backup(self) -> None:
        """Create timestamped backup of configuration file."""
        if not self.config_file.exists():
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.config_file.parent / f"{self.config_file.stem}.{timestamp}.backup"
        
        try:
            shutil.copy2(self.config_file, backup_path)
        except Exception:
            # Backup failure is not critical
            pass
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot-notation path.
        
        Args:
            key_path: Dot-separated path (e.g., 'global_settings.input_dir')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def set(self, key_path: str, value: Any) -> None:
        """
        Set configuration value using dot-notation path.
        
        Args:
            key_path: Dot-separated path
            value: Value to set
        """
        keys = key_path.split('.')
        target = self.config
        
        # Navigate to parent of target key
        for key in keys[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]
        
        # Set final value
        target[keys[-1]] = value
    
    def validate(self) -> bool:
        """
        Validate configuration against schema.
        
        Returns:
            True if valid
            
        Raises:
            ConfigValidationError: If validation fails
        """
        # Check required top-level sections
        required_sections = ["global_settings", "app_defaults"]
        for section in required_sections:
            if section not in self.config:
                raise ConfigValidationError(
                    section,
                    None,
                    f"Required section '{section}' missing"
                )
        
        # Validate specific fields
        self._validate_buttons_position()
        self._validate_info_panel_position()
        self._validate_mode()
        self._validate_profile()
        self._validate_overwrite_policy()
        self._validate_max_file_mb()
        
        return True

    def _effective_value(self, key_path: str) -> Any:
        """Resolve a value for validation, falling back to the packaged default.

        An absent key is not an invalid value - it means "use the default".
        The governed configuration carries no global_settings.ui_layout
        section at all (nothing in the application reads one; the keys survive
        only as v1.1.5 migration targets), so validate() was rejecting the
        shipped document over values it was never supposed to carry. A key
        that IS present is still checked against the permitted set, an explicit
        null included - only omission defers to the default.
        """
        value = self.get(key_path, self._UNSET)
        if value is not self._UNSET:
            return value

        default: Any = self.DEFAULT_CONFIG
        for key in key_path.split('.'):
            if not isinstance(default, dict) or key not in default:
                return self._UNSET
            default = default[key]
        return default

    def _validate_buttons_position(self) -> None:
        """Validate buttons_position value."""
        value = self._effective_value('global_settings.ui_layout.buttons_position')
        if value not in ['top', 'bottom']:
            raise ConfigValidationError(
                'global_settings.ui_layout.buttons_position',
                value,
                "Must be 'top' or 'bottom'"
            )
    
    def _validate_info_panel_position(self) -> None:
        """Validate info_panel_position value."""
        value = self._effective_value('global_settings.ui_layout.info_panel_position')
        if value not in ['top', 'middle', 'bottom']:
            raise ConfigValidationError(
                'global_settings.ui_layout.info_panel_position',
                value,
                "Must be 'top', 'middle', or 'bottom'"
            )
    
    def _validate_mode(self) -> None:
        """Validate default_mode value."""
        value = self._effective_value('app_defaults.default_mode')
        if value not in ['unbundle', 'bundle']:
            raise ConfigValidationError(
                'app_defaults.default_mode',
                value,
                "Must be 'unbundle' or 'bundle'"
            )
    
    def _validate_profile(self) -> None:
        """Validate bundle_profile value."""
        value = self._effective_value('app_defaults.bundle_profile')
        valid_profiles = ['plain_marker', 'md_fence']
        if value not in valid_profiles:
            raise ConfigValidationError(
                'app_defaults.bundle_profile',
                value,
                f"Must be one of: {', '.join(valid_profiles)}"
            )
    
    def _validate_overwrite_policy(self) -> None:
        """Validate overwrite_policy value."""
        value = self._effective_value('app_defaults.overwrite_policy')
        valid_policies = ['prompt', 'skip', 'rename', 'overwrite']
        if value not in valid_policies:
            raise ConfigValidationError(
                'app_defaults.overwrite_policy',
                value,
                f"Must be one of: {', '.join(valid_policies)}"
            )
    
    def _validate_max_file_mb(self) -> None:
        """Validate max_file_mb value."""
        value = self._effective_value('safety.max_file_mb')
        if not isinstance(value, (int, float)) or value <= 0:
            raise ConfigValidationError(
                'safety.max_file_mb',
                value,
                "Must be a positive number"
            )
    
    def _deep_copy(self, obj: Any) -> Any:
        """Deep copy a configuration object."""
        if isinstance(obj, dict):
            return {k: self._deep_copy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._deep_copy(item) for item in obj]
        else:
            return obj
    
    def reset_to_defaults(self) -> None:
        """Reset the in-memory configuration to default values.

        Build 104, R-BFT-01: this no longer writes to disk. The governed file is
        the delivery payload and is restored by reinstalling, not by the running
        application.
        """
        self.config = self._deep_copy(self.DEFAULT_CONFIG)
    
    def export_dict(self) -> Dict:
        """
        Export configuration as dictionary.
        
        Returns:
            Deep copy of configuration
        """
        return self._deep_copy(self.config)


# ===================================================================================================
# LIFECYCLE STATUS: Proposed
# NEXT STEPS: pyprojmgr scan to catalog, Phase 3 bootstrap
# DEPENDENCIES: exceptions.py
# TESTS: test_config_migration.py
# ===================================================================================================
# ===================================================================
