# ============================================================================
# FILE: config.py
# RELPATH: bundle_file_tool_v2/src/core/config.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.0
# LIFECYCLE: Proposed
# DESCRIPTION: Configuration manager with v1.1.5 migration and unknown key preservation
# ============================================================================

"""
Configuration Manager for Bundle File Tool v2.1.

Handles loading, saving, validating, and migrating configuration files.
Provides backward compatibility with v1.1.5 flat structure while supporting
the new v2.1 nested schema. Preserves unknown keys in global_settings.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime
import shutil
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.exceptions import (
    ConfigError,
    ConfigLoadError,
    ConfigMigrationError,
    ConfigValidationError
)


class ConfigManager:
    """
    Manages application configuration with migration support.
    
    Supports both v1.1.5 (flat) and v2.1 (nested) configuration formats,
    with automatic migration and backward compatibility. Preserves unknown
    keys in global_settings for forward compatibility.
    """
    
    # Default configuration for v2.1
    DEFAULT_CONFIG = {
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
        "safety": {
            "allow_globs": ["src/**", "docs/**"],
            "deny_globs": ["**/.venv/**", "**/__pycache__/**", "*.log"],
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
    
    def __init__(self, config_file: str = "bundle_config.json"):
        """
        Initialize configuration manager.
        
        Args:
            config_file: Path to configuration file
        """
        self.config_file = Path(config_file)
        self.config: Dict = {}
        self.version: str = "2.1"
        self._load_or_create()
    
    def _load_or_create(self) -> None:
        """Load existing config or create default."""
        if self.config_file.exists():
            self.load()
        else:
            self.config = self._deep_copy(self.DEFAULT_CONFIG)
            self.save()
    
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
        Save configuration to file.
        
        Raises:
            ConfigError: If file cannot be written
        """
        try:
            text = json.dumps(self.config, indent=2, ensure_ascii=False)
            self.config_file.write_text(text, encoding='utf-8')
        except Exception as e:
            raise ConfigError(f"Failed to save config: {str(e)}")
    
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
    
    def _validate_buttons_position(self) -> None:
        """Validate buttons_position value."""
        value = self.get('global_settings.ui_layout.buttons_position')
        if value not in ['top', 'bottom']:
            raise ConfigValidationError(
                'global_settings.ui_layout.buttons_position',
                value,
                "Must be 'top' or 'bottom'"
            )
    
    def _validate_info_panel_position(self) -> None:
        """Validate info_panel_position value."""
        value = self.get('global_settings.ui_layout.info_panel_position')
        if value not in ['top', 'middle', 'bottom']:
            raise ConfigValidationError(
                'global_settings.ui_layout.info_panel_position',
                value,
                "Must be 'top', 'middle', or 'bottom'"
            )
    
    def _validate_mode(self) -> None:
        """Validate default_mode value."""
        value = self.get('app_defaults.default_mode')
        if value not in ['unbundle', 'bundle']:
            raise ConfigValidationError(
                'app_defaults.default_mode',
                value,
                "Must be 'unbundle' or 'bundle'"
            )
    
    def _validate_profile(self) -> None:
        """Validate bundle_profile value."""
        value = self.get('app_defaults.bundle_profile')
        valid_profiles = ['plain_marker', 'md_fence', 'jsonl']
        if value not in valid_profiles:
            raise ConfigValidationError(
                'app_defaults.bundle_profile',
                value,
                f"Must be one of: {', '.join(valid_profiles)}"
            )
    
    def _validate_overwrite_policy(self) -> None:
        """Validate overwrite_policy value."""
        value = self.get('app_defaults.overwrite_policy')
        valid_policies = ['prompt', 'skip', 'rename', 'overwrite']
        if value not in valid_policies:
            raise ConfigValidationError(
                'app_defaults.overwrite_policy',
                value,
                f"Must be one of: {', '.join(valid_policies)}"
            )
    
    def _validate_max_file_mb(self) -> None:
        """Validate max_file_mb value."""
        value = self.get('safety.max_file_mb')
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
        """Reset configuration to default values."""
        self.config = self._deep_copy(self.DEFAULT_CONFIG)
        self.save()
    
    def export_dict(self) -> Dict:
        """
        Export configuration as dictionary.
        
        Returns:
            Deep copy of configuration
        """
        return self._deep_copy(self.config)


# ============================================================================
# LIFECYCLE STATUS: Proposed
# NEXT STEPS: pyprojmgr scan to catalog, Phase 3 bootstrap
# DEPENDENCIES: exceptions.py
# TESTS: test_config_migration.py
# ============================================================================
