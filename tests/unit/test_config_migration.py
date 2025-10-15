# ============================================================================
# FILE: test_config_migration.py
# RELPATH: bundle_file_tool_v2/tests/unit/test_config_migration.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.0
# LIFECYCLE: Proposed
# DESCRIPTION: Comprehensive tests for v1.1.5 → v2.1 config migration
# ============================================================================

"""
Config Migration Test Suite.

Tests all aspects of v1.1.5 to v2.1 configuration migration including:
- Known key mapping
- Unknown key preservation (Option A - approved by Ringo)
- Backup creation
- Round-trip migration
- Production config validation
- Edge cases and error handling
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from core.config import ConfigManager
from core.exceptions import ConfigLoadError, ConfigMigrationError


class TestV115Detection:
    """Tests for v1.1.5 format detection."""
    
    def test_detect_v115_format(self, temp_dir):
        """Test detection of v1.1.5 flat format."""
        config_file = temp_dir / "test_config.json"
        
        # Create v1.1.5 format config
        v115_config = {
            "input_dir": "",
            "output_dir": "",
            "log_dir": "logs",
            "buttons_position": "bottom",
            "show_info_panel": True,
            "info_panel_position": "middle",
            "first_launch": True,
            "add_headers": True
        }
        
        config_file.write_text(json.dumps(v115_config, indent=2))
        
        # Load should detect and migrate
        manager = ConfigManager(str(config_file))
        
        # Should have v2.1 structure
        assert "global_settings" in manager.config
        assert "app_defaults" in manager.config
        assert "safety" in manager.config
    
    def test_detect_v21_format(self, temp_dir):
        """Test that v2.1 format is not migrated."""
        config_file = temp_dir / "test_config.json"
        
        # Create v2.1 format config
        v21_config = {
            "global_settings": {
                "input_dir": "/test"
            },
            "app_defaults": {
                "default_mode": "unbundle"
            },
            "safety": {
                "max_file_mb": 10
            }
        }
        
        config_file.write_text(json.dumps(v21_config, indent=2))
        
        manager = ConfigManager(str(config_file))
        
        # Should not be migrated - structure unchanged
        assert manager.config["global_settings"]["input_dir"] == "/test"


class TestKnownKeyMigration:
    """Tests for known v1.1.5 key migration to v2.1 locations."""
    
    def test_migrate_global_settings_keys(self, temp_dir):
        """Test migration of input_dir, output_dir, log_dir, relative_base_path."""
        config_file = temp_dir / "test_config.json"
        
        v115_config = {
            "input_dir": "C:/test/input",
            "output_dir": "C:/test/output",
            "log_dir": "C:/test/logs",
            "relative_base_path": "C:/test/base",
            "buttons_position": "bottom",
            "show_info_panel": True,
            "info_panel_position": "middle",
            "first_launch": False,
            "add_headers": True
        }
        
        config_file.write_text(json.dumps(v115_config, indent=2))
        manager = ConfigManager(str(config_file))
        
        # Check migration to global_settings
        assert manager.get("global_settings.input_dir") == "C:/test/input"
        assert manager.get("global_settings.output_dir") == "C:/test/output"
        assert manager.get("global_settings.log_dir") == "C:/test/logs"
        assert manager.get("global_settings.relative_base_path") == "C:/test/base"
    
    def test_migrate_ui_layout_keys(self, temp_dir):
        """Test migration of UI layout keys to nested structure."""
        config_file = temp_dir / "test_config.json"
        
        v115_config = {
            "input_dir": "",
            "output_dir": "",
            "log_dir": "logs",
            "buttons_position": "top",
            "show_info_panel": False,
            "info_panel_position": "bottom",
            "first_launch": True,
            "add_headers": True
        }
        
        config_file.write_text(json.dumps(v115_config, indent=2))
        manager = ConfigManager(str(config_file))
        
        # Check migration to ui_layout
        assert manager.get("global_settings.ui_layout.buttons_position") == "top"
        assert manager.get("global_settings.ui_layout.show_info_panel") is False
        assert manager.get("global_settings.ui_layout.info_panel_position") == "bottom"
    
    def test_migrate_session_keys(self, temp_dir):
        """Test migration of first_launch to session section."""
        config_file = temp_dir / "test_config.json"
        
        v115_config = {
            "input_dir": "",
            "output_dir": "",
            "log_dir": "logs",
            "buttons_position": "bottom",
            "show_info_panel": True,
            "info_panel_position": "middle",
            "first_launch": False,
            "add_headers": True
        }
        
        config_file.write_text(json.dumps(v115_config, indent=2))
        manager = ConfigManager(str(config_file))
        
        # Check migration to session
        assert manager.get("session.first_launch") is False
    
    def test_migrate_app_defaults_keys(self, temp_dir):
        """Test migration of add_headers to app_defaults."""
        config_file = temp_dir / "test_config.json"
        
        v115_config = {
            "input_dir": "",
            "output_dir": "",
            "log_dir": "logs",
            "buttons_position": "bottom",
            "show_info_panel": True,
            "info_panel_position": "middle",
            "first_launch": True,
            "add_headers": False
        }
        
        config_file.write_text(json.dumps(v115_config, indent=2))
        manager = ConfigManager(str(config_file))
        
        # Check migration to app_defaults
        assert manager.get("app_defaults.add_headers") is False


class TestUnknownKeyPreservation:
    """Tests for preserving unknown keys in global_settings (Option A - Approved)."""
    
    def test_preserve_show_splash_keys(self, temp_dir):
        """Test preservation of show_splash and splash_duration (production config)."""
        config_file = temp_dir / "test_config.json"
        
        # Production config with splash screen keys
        v115_config = {
            "input_dir": "C:/Users/mpw/Python/mp4_tool_project",
            "output_dir": "C:/Users/mpw/Python/mp4_tool_project",
            "log_dir": "C:/Users/mpw/Python/mp4_tool_project/logs",
            "buttons_position": "bottom",
            "show_info_panel": True,
            "info_panel_position": "middle",
            "first_launch": False,
            "add_headers": True,
            "show_splash": True,
            "splash_duration": 2000
        }
        
        config_file.write_text(json.dumps(v115_config, indent=2))
        manager = ConfigManager(str(config_file))
        
        # Unknown keys should be preserved in global_settings
        assert manager.get("global_settings.show_splash") is True
        assert manager.get("global_settings.splash_duration") == 2000
    
    def test_preserve_multiple_unknown_keys(self, temp_dir):
        """Test preservation of multiple unknown keys."""
        config_file = temp_dir / "test_config.json"
        
        v115_config = {
            "input_dir": "",
            "output_dir": "",
            "log_dir": "logs",
            "buttons_position": "bottom",
            "show_info_panel": True,
            "info_panel_position": "middle",
            "first_launch": True,
            "add_headers": True,
            "custom_key_1": "value1",
            "custom_key_2": 42,
            "custom_key_3": {"nested": "data"}
        }
        
        config_file.write_text(json.dumps(v115_config, indent=2))
        manager = ConfigManager(str(config_file))
        
        # All unknown keys preserved
        assert manager.get("global_settings.custom_key_1") == "value1"
        assert manager.get("global_settings.custom_key_2") == 42
        assert manager.get("global_settings.custom_key_3") == {"nested": "data"}
    
    def test_unknown_keys_saved_correctly(self, temp_dir):
        """Test that unknown keys persist after save/reload."""
        config_file = temp_dir / "test_config.json"
        
        v115_config = {
            "input_dir": "",
            "output_dir": "",
            "log_dir": "logs",
            "buttons_position": "bottom",
            "show_info_panel": True,
            "info_panel_position": "middle",
            "first_launch": True,
            "add_headers": True,
            "show_splash": True,
            "splash_duration": 2000
        }
        
        config_file.write_text(json.dumps(v115_config, indent=2))
        manager = ConfigManager(str(config_file))
        
        # Save and reload
        manager.save()
        manager2 = ConfigManager(str(config_file))
        
        # Unknown keys should still be there
        assert manager2.get("global_settings.show_splash") is True
        assert manager2.get("global_settings.splash_duration") == 2000


class TestBackupCreation:
    """Tests for backup file creation during migration."""
    
    def test_backup_created_during_migration(self, temp_dir):
        """Test that backup file is created before migration."""
        config_file = temp_dir / "test_config.json"
        
        v115_config = {
            "input_dir": "",
            "output_dir": "",
            "log_dir": "logs",
            "buttons_position": "bottom",
            "show_info_panel": True,
            "info_panel_position": "middle",
            "first_launch": True,
            "add_headers": True
        }
        
        config_file.write_text(json.dumps(v115_config, indent=2))
        
        # Trigger migration
        manager = ConfigManager(str(config_file))
        
        # Check for backup file
        backup_files = list(temp_dir.glob("test_config.*.backup"))
        assert len(backup_files) >= 1
    
    def test_backup_contains_original_data(self, temp_dir):
        """Test that backup file contains original v1.1.5 data."""
        config_file = temp_dir / "test_config.json"
        
        original_data = {
            "input_dir": "C:/original",
            "output_dir": "C:/original",
            "log_dir": "logs",
            "buttons_position": "bottom",
            "show_info_panel": True,
            "info_panel_position": "middle",
            "first_launch": True,
            "add_headers": True
        }
        
        config_file.write_text(json.dumps(original_data, indent=2))
        
        # Trigger migration
        manager = ConfigManager(str(config_file))
        
        # Find backup
        backup_files = list(temp_dir.glob("test_config.*.backup"))
        assert len(backup_files) >= 1
        
        # Verify backup contains original data
        backup_data = json.loads(backup_files[0].read_text())
        assert backup_data["input_dir"] == "C:/original"
        assert "global_settings" not in backup_data  # Should be v1.1.5 format


class TestProductionConfigMigration:
    """Tests using actual production config from Ringo."""
    
    def test_ringo_production_config_migration(self, temp_dir):
        """Test migration of Ringo's actual production config."""
        config_file = temp_dir / "bundle_config.json"
        
        # Actual production config
        production_config = {
            "input_dir": "C:/Users/mpw/Python/mp4_tool_project",
            "output_dir": "C:/Users/mpw/Python/mp4_tool_project",
            "log_dir": "C:/Users/mpw/Python/mp4_tool_project/logs",
            "buttons_position": "bottom",
            "show_info_panel": True,
            "info_panel_position": "middle",
            "first_launch": False,
            "add_headers": True,
            "show_splash": True,
            "splash_duration": 2000
        }
        
        config_file.write_text(json.dumps(production_config, indent=2))
        manager = ConfigManager(str(config_file))
        
        # Verify all known keys migrated correctly
        assert manager.get("global_settings.input_dir") == "C:/Users/mpw/Python/mp4_tool_project"
        assert manager.get("global_settings.output_dir") == "C:/Users/mpw/Python/mp4_tool_project"
        assert manager.get("global_settings.log_dir") == "C:/Users/mpw/Python/mp4_tool_project/logs"
        assert manager.get("global_settings.ui_layout.buttons_position") == "bottom"
        assert manager.get("global_settings.ui_layout.show_info_panel") is True
        assert manager.get("global_settings.ui_layout.info_panel_position") == "middle"
        assert manager.get("session.first_launch") is False
        assert manager.get("app_defaults.add_headers") is True
        
        # Verify unknown keys preserved (Option A)
        assert manager.get("global_settings.show_splash") is True
        assert manager.get("global_settings.splash_duration") == 2000
        
        # Verify new v2.1 defaults added
        assert manager.get("app_defaults.default_mode") == "unbundle"
        assert manager.get("app_defaults.bundle_profile") == "md_fence"
        assert manager.get("app_defaults.overwrite_policy") == "prompt"
        assert manager.get("safety.max_file_mb") == 10
    
    def test_save_and_reload_preserves_structure(self, temp_dir):
        """Test that save/reload cycle preserves v2.1 structure."""
        config_file = temp_dir / "test_config.json"
        
        v115_config = {
            "input_dir": "C:/test",
            "output_dir": "C:/test",
            "log_dir": "logs",
            "buttons_position": "bottom",
            "show_info_panel": True,
            "info_panel_position": "middle",
            "first_launch": False,
            "add_headers": True,
            "show_splash": True,
            "splash_duration": 2000
        }
        
        config_file.write_text(json.dumps(v115_config, indent=2))
        
        # Load and migrate
        manager1 = ConfigManager(str(config_file))
        manager1.save()
        
        # Reload
        manager2 = ConfigManager(str(config_file))
        
        # Should not migrate again (already v2.1)
        assert manager2.get("global_settings.input_dir") == "C:/test"
        assert manager2.get("global_settings.show_splash") is True
        assert manager2.get("app_defaults.default_mode") == "unbundle"


class TestEdgeCases:
    """Tests for edge cases and error conditions."""
    
    def test_empty_v115_config(self, temp_dir):
        """Test migration with minimal v1.1.5 config."""
        config_file = temp_dir / "test_config.json"
        
        # Minimal config
        v115_config = {
            "input_dir": "",
            "output_dir": "",
            "log_dir": "logs"
        }
        
        config_file.write_text(json.dumps(v115_config, indent=2))
        manager = ConfigManager(str(config_file))
        
        # Should have all v2.1 defaults filled in
        assert manager.get("global_settings.ui_layout.buttons_position") == "bottom"
        assert manager.get("app_defaults.add_headers") is True
        assert manager.get("session.first_launch") is True
    
    def test_missing_optional_keys(self, temp_dir):
        """Test that missing v1.1.5 keys get defaults."""
        config_file = temp_dir / "test_config.json"
        
        # Missing add_headers, first_launch
        v115_config = {
            "input_dir": "",
            "output_dir": "",
            "log_dir": "logs",
            "buttons_position": "bottom",
            "show_info_panel": True,
            "info_panel_position": "middle"
        }
        
        config_file.write_text(json.dumps(v115_config, indent=2))
        manager = ConfigManager(str(config_file))
        
        # Should have defaults
        assert manager.get("app_defaults.add_headers") is True
        assert manager.get("session.first_launch") is True
    
    def test_invalid_json_raises_error(self, temp_dir):
        """Test that invalid JSON raises ConfigLoadError."""
        config_file = temp_dir / "test_config.json"
        config_file.write_text("{ invalid json }")
        
        with pytest.raises(ConfigLoadError) as exc_info:
            ConfigManager(str(config_file))
        
        assert "Invalid JSON" in str(exc_info.value)


class TestDefaultValues:
    """Tests for v2.1 default values per specification §3.1."""
    
    def test_all_v21_defaults_present(self, temp_dir):
        """Test that all v2.1 default values are correctly set."""
        config_file = temp_dir / "test_config.json"
        
        # Minimal v1.1.5 config
        v115_config = {
            "input_dir": "",
            "output_dir": "",
            "log_dir": "logs"
        }
        
        config_file.write_text(json.dumps(v115_config, indent=2))
        manager = ConfigManager(str(config_file))
        
        # Check all v2.1 defaults per §3.1
        assert manager.get("app_defaults.default_mode") == "unbundle"
        assert manager.get("app_defaults.bundle_profile") == "md_fence"
        assert manager.get("app_defaults.encoding") == "auto"
        assert manager.get("app_defaults.eol") == "auto"
        assert manager.get("app_defaults.overwrite_policy") == "prompt"
        assert manager.get("app_defaults.dry_run_default") is True
        assert manager.get("app_defaults.treat_binary_as_base64") is True
        
        assert manager.get("safety.max_file_mb") == 10
        assert "src/**" in manager.get("safety.allow_globs")
        assert "**/.venv/**" in manager.get("safety.deny_globs")


# ============================================================================
# LIFECYCLE STATUS: Proposed
# COVERAGE: Complete v1.1.5 → v2.1 migration path
# NEXT STEPS: pyprojmgr scan to catalog, integration with GUI
# DEPENDENCIES: config.py, exceptions.py
# ============================================================================
