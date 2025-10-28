# ============================================================================
# SOURCEFILE: test_cli.py
# RELPATH: bundle_file_tool_v2/tests/integration/test_cli.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.0
# LIFECYCLE: Proposed
# DESCRIPTION: Integration tests for CLI commands
# ============================================================================

"""
CLI Integration Test Suite.

Tests all three CLI commands (unbundle, bundle, validate) with various
options and error conditions. Uses subprocess to test actual CLI invocation.
"""

import pytest
import subprocess
import sys
from pathlib import Path
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestCLIUnbundle:
    """Tests for unbundle command."""
    
    def test_unbundle_basic(self, temp_dir, sample_plain_marker_bundle):
        """Test basic unbundle operation."""
        bundle_file = temp_dir / "test_bundle.txt"
        bundle_file.write_text(sample_plain_marker_bundle)
        
        output_dir = temp_dir / "output"
        
        # Run CLI
        result = subprocess.run([
            sys.executable, "-m", "cli",
            "unbundle", str(bundle_file),
            "--output", str(output_dir)
        ], capture_output=True, text=True, cwd=str(Path(__file__).parent.parent.parent / "src"))
        
        assert result.returncode == 0
        assert "Extraction complete" in result.stdout
        assert output_dir.exists()
    
    def test_unbundle_with_profile(self, temp_dir, sample_plain_marker_bundle):
        """Test unbundle with explicit profile specification."""
        bundle_file = temp_dir / "test_bundle.txt"
        bundle_file.write_text(sample_plain_marker_bundle)
        
        output_dir = temp_dir / "output"
        
        result = subprocess.run([
            sys.executable, "-m", "cli",
            "unbundle", str(bundle_file),
            "--output", str(output_dir),
            "--profile", "plain_marker"
        ], capture_output=True, text=True, cwd=str(Path(__file__).parent.parent.parent / "src"))
        
        assert result.returncode == 0
        assert "plain_marker" in result.stdout
    
    def test_unbundle_dry_run(self, temp_dir, sample_plain_marker_bundle):
        """Test dry run mode doesn't write files."""
        bundle_file = temp_dir / "test_bundle.txt"
        bundle_file.write_text(sample_plain_marker_bundle)
        
        output_dir = temp_dir / "output"
        
        result = subprocess.run([
            sys.executable, "-m", "cli",
            "unbundle", str(bundle_file),
            "--output", str(output_dir),
            "--dry-run"
        ], capture_output=True, text=True, cwd=str(Path(__file__).parent.parent.parent / "src"))
        
        assert result.returncode == 0
        assert "DRY RUN" in result.stdout
        # Output dir should not exist or be empty
        if output_dir.exists():
            assert len(list(output_dir.rglob("*"))) == 0
    
    def test_unbundle_missing_file(self, temp_dir):
        """Test error handling for missing input file."""
        result = subprocess.run([
            sys.executable, "-m", "cli",
            "unbundle", str(temp_dir / "nonexistent.txt"),
            "--output", str(temp_dir / "output")
        ], capture_output=True, text=True, cwd=str(Path(__file__).parent.parent.parent / "src"))
        
        assert result.returncode == 1
        assert "ERROR" in result.stderr or "not found" in result.stderr.lower()
    
    def test_unbundle_no_output_specified(self, temp_dir, sample_plain_marker_bundle):
        """Test error when no output directory specified and not in config."""
        bundle_file = temp_dir / "test_bundle.txt"
        bundle_file.write_text(sample_plain_marker_bundle)
        
        # Create empty config
        config_file = temp_dir / "bundle_config.json"
        config_file.write_text(json.dumps({
            "global_settings": {"output_dir": ""}
        }))
        
        result = subprocess.run([
            sys.executable, "-m", "cli",
            "unbundle", str(bundle_file)
        ], capture_output=True, text=True, cwd=str(Path(__file__).parent.parent.parent / "src"))
        
        assert result.returncode == 1
        assert "Output directory must be specified" in result.stderr
    
    def test_unbundle_overwrite_policy(self, temp_dir, sample_plain_marker_bundle):
        """Test overwrite policy options."""
        bundle_file = temp_dir / "test_bundle.txt"
        bundle_file.write_text(sample_plain_marker_bundle)
        
        output_dir = temp_dir / "output"
        
        # Run with skip policy
        result = subprocess.run([
            sys.executable, "-m", "cli",
            "unbundle", str(bundle_file),
            "--output", str(output_dir),
            "--overwrite", "skip"
        ], capture_output=True, text=True, cwd=str(Path(__file__).parent.parent.parent / "src"))
        
        assert result.returncode == 0


class TestCLIBundle:
    """Tests for bundle command."""
    
    def test_bundle_single_file(self, temp_dir):
        """Test bundling a single file."""
        source_file = temp_dir / "test.txt"
        source_file.write_text("Hello, World!")
        
        output_file = temp_dir / "bundle.txt"
        
        result = subprocess.run([
            sys.executable, "-m", "cli",
            "bundle", str(source_file),
            "--output", str(output_file)
        ], capture_output=True, text=True, cwd=str(Path(__file__).parent.parent.parent / "src"))
        
        assert result.returncode == 0
        assert output_file.exists()
        assert "Bundle created" in result.stdout
    
    def test_bundle_directory(self, sample_project_structure):
        """Test bundling an entire directory."""
        output_file = sample_project_structure / "bundle.txt"
        
        result = subprocess.run([
            sys.executable, "-m", "cli",
            "bundle", str(sample_project_structure / "src"),
            "--output", str(output_file)
        ], capture_output=True, text=True, cwd=str(Path(__file__).parent.parent.parent / "src"))
        
        assert result.returncode == 0
        assert output_file.exists()
    
    def test_bundle_with_profile(self, temp_dir):
        """Test bundle with specific profile."""
        source_file = temp_dir / "test.py"
        source_file.write_text("print('test')")
        
        output_file = temp_dir / "bundle.txt"
        
        result = subprocess.run([
            sys.executable, "-m", "cli",
            "bundle", str(source_file),
            "--output", str(output_file),
            "--profile", "plain_marker"
        ], capture_output=True, text=True, cwd=str(Path(__file__).parent.parent.parent / "src"))
        
        assert result.returncode == 0
        assert "plain_marker" in result.stdout
    
    def test_bundle_to_stdout(self, temp_dir):
        """Test bundle output to stdout."""
        source_file = temp_dir / "test.txt"
        source_file.write_text("Content")
        
        result = subprocess.run([
            sys.executable, "-m", "cli",
            "bundle", str(source_file)
        ], capture_output=True, text=True, cwd=str(Path(__file__).parent.parent.parent / "src"))
        
        assert result.returncode == 0
        # Should have bundle content in stdout
        assert "FILE" in result.stdout or "```" in result.stdout
    
    def test_bundle_with_include_exclude(self, sample_project_structure):
        """Test bundle with include/exclude patterns."""
        output_file = sample_project_structure / "bundle.txt"
        
        result = subprocess.run([
            sys.executable, "-m", "cli",
            "bundle", str(sample_project_structure),
            "--output", str(output_file),
            "--include", "*.py",
            "--exclude", "test_*"
        ], capture_output=True, text=True, cwd=str(Path(__file__).parent.parent.parent / "src"))
        
        assert result.returncode == 0
    
    def test_bundle_nonexistent_source(self, temp_dir):
        """Test error for nonexistent source path."""
        result = subprocess.run([
            sys.executable, "-m", "cli",
            "bundle", str(temp_dir / "nonexistent"),
            "--output", str(temp_dir / "bundle.txt")
        ], capture_output=True, text=True, cwd=str(Path(__file__).parent.parent.parent / "src"))
        
        assert result.returncode == 1
        assert "ERROR" in result.stderr or "not found" in result.stderr.lower()
    
    def test_bundle_invalid_profile(self, temp_dir):
        """Test error for invalid profile name."""
        source_file = temp_dir / "test.txt"
        source_file.write_text("Content")
        
        result = subprocess.run([
            sys.executable, "-m", "cli",
            "bundle", str(source_file),
            "--profile", "invalid_profile"
        ], capture_output=True, text=True, cwd=str(Path(__file__).parent.parent.parent / "src"))
        
        assert result.returncode == 1
        assert "Invalid profile" in result.stderr
    
    def test_bundle_no_files_found(self, temp_dir):
        """Test error when no files match criteria."""
        empty_dir = temp_dir / "empty"
        empty_dir.mkdir()
        
        result = subprocess.run([
            sys.executable, "-m", "cli",
            "bundle", str(empty_dir),
            "--include", "*.nonexistent"
        ], capture_output=True, text=True, cwd=str(Path(__file__).parent.parent.parent / "src"))
        
        assert result.returncode == 1
        assert "No files found" in result.stderr


class TestCLIValidate:
    """Tests for validate command."""
    
    def test_validate_valid_bundle(self, temp_dir, sample_plain_marker_bundle):
        """Test validation of valid bundle."""
        bundle_file = temp_dir / "test_bundle.txt"
        bundle_file.write_text(sample_plain_marker_bundle)
        
        result = subprocess.run([
            sys.executable, "-m", "cli",
            "validate", str(bundle_file)
        ], capture_output=True, text=True, cwd=str(Path(__file__).parent.parent.parent / "src"))
        
        assert result.returncode == 0
        assert "VALID" in result.stdout
        assert "VALIDATION REPORT" in result.stdout
    
    def test_validate_invalid_bundle(self, temp_dir):
        """Test validation of invalid bundle."""
        bundle_file = temp_dir / "invalid.txt"
        bundle_file.write_text("This is not a valid bundle format")
        
        result = subprocess.run([
            sys.executable, "-m", "cli",
            "validate", str(bundle_file)
        ], capture_output=True, text=True, cwd=str(Path(__file__).parent.parent.parent / "src"))
        
        assert result.returncode == 1
        assert "INVALID" in result.stdout
    
    def test_validate_with_profile(self, temp_dir, sample_plain_marker_bundle):
        """Test validation with explicit profile."""
        bundle_file = temp_dir / "test_bundle.txt"
        bundle_file.write_text(sample_plain_marker_bundle)
        
        result = subprocess.run([
            sys.executable, "-m", "cli",
            "validate", str(bundle_file),
            "--profile", "plain_marker"
        ], capture_output=True, text=True, cwd=str(Path(__file__).parent.parent.parent / "src"))
        
        assert result.returncode == 0
        assert "plain_marker" in result.stdout
    
    def test_validate_missing_file(self, temp_dir):
        """Test error for missing bundle file."""
        result = subprocess.run([
            sys.executable, "-m", "cli",
            "validate", str(temp_dir / "nonexistent.txt")
        ], capture_output=True, text=True, cwd=str(Path(__file__).parent.parent.parent / "src"))
        
        assert result.returncode == 1
        assert "ERROR" in result.stderr or "not found" in result.stderr.lower()
    
    def test_validate_shows_file_count(self, temp_dir, sample_plain_marker_bundle):
        """Test that validation report shows file count."""
        bundle_file = temp_dir / "test_bundle.txt"
        bundle_file.write_text(sample_plain_marker_bundle)
        
        result = subprocess.run([
            sys.executable, "-m", "cli",
            "validate", str(bundle_file)
        ], capture_output=True, text=True, cwd=str(Path(__file__).parent.parent.parent / "src"))
        
        assert result.returncode == 0
        assert "File count:" in result.stdout
        assert "Format:" in result.stdout


class TestCLIHelp:
    """Tests for help output."""
    
    def test_main_help(self):
        """Test main help output."""
        result = subprocess.run([
            sys.executable, "-m", "cli",
            "--help"
        ], capture_output=True, text=True, cwd=str(Path(__file__).parent.parent.parent / "src"))
        
        assert result.returncode == 0
        assert "unbundle" in result.stdout
        assert "bundle" in result.stdout
        assert "validate" in result.stdout
    
    def test_unbundle_help(self):
        """Test unbundle command help."""
        result = subprocess.run([
            sys.executable, "-m", "cli",
            "unbundle", "--help"
        ], capture_output=True, text=True, cwd=str(Path(__file__).parent.parent.parent / "src"))
        
        assert result.returncode == 0
        assert "input_file" in result.stdout
        assert "--output" in result.stdout
        assert "--profile" in result.stdout
    
    def test_bundle_help(self):
        """Test bundle command help."""
        result = subprocess.run([
            sys.executable, "-m", "cli",
            "bundle", "--help"
        ], capture_output=True, text=True, cwd=str(Path(__file__).parent.parent.parent / "src"))
        
        assert result.returncode == 0
        assert "source_paths" in result.stdout
        assert "--output" in result.stdout
    
    def test_validate_help(self):
        """Test validate command help."""
        result = subprocess.run([
            sys.executable, "-m", "cli",
            "validate", "--help"
        ], capture_output=True, text=True, cwd=str(Path(__file__).parent.parent.parent / "src"))
        
        assert result.returncode == 0
        assert "input_file" in result.stdout


class TestCLIEdgeCases:
    """Tests for edge cases and error conditions."""
    
    def test_no_command(self):
        """Test error when no command specified."""
        result = subprocess.run([
            sys.executable, "-m", "cli"
        ], capture_output=True, text=True, cwd=str(Path(__file__).parent.parent.parent / "src"))
        
        assert result.returncode != 0
    
    def test_invalid_command(self):
        """Test error for invalid command."""
        result = subprocess.run([
            sys.executable, "-m", "cli",
            "invalid_command"
        ], capture_output=True, text=True, cwd=str(Path(__file__).parent.parent.parent / "src"))
        
        assert result.returncode != 0
    
    def test_keyboard_interrupt(self, temp_dir, monkeypatch):
        """Test handling of keyboard interrupt."""
        # This test would require more complex setup to properly test
        # Documented as a known limitation of the test suite
        pass


class TestCLIConfigPrecedence:
    """Tests for configuration precedence (CLI > config > defaults)."""
    
    def test_cli_overrides_config(self, temp_dir, sample_plain_marker_bundle):
        """Test that CLI arguments override config file."""
        bundle_file = temp_dir / "test_bundle.txt"
        bundle_file.write_text(sample_plain_marker_bundle)
        
        # Create config with specific settings
        config_file = temp_dir / "bundle_config.json"
        config = {
            "global_settings": {
                "output_dir": str(temp_dir / "config_output")
            },
            "app_defaults": {
                "add_headers": False
            }
        }
        config_file.write_text(json.dumps(config))
        
        # Override with CLI
        cli_output = temp_dir / "cli_output"
        result = subprocess.run([
            sys.executable, "-m", "cli",
            "unbundle", str(bundle_file),
            "--output", str(cli_output)
        ], capture_output=True, text=True, cwd=str(Path(__file__).parent.parent.parent / "src"))
        
        assert result.returncode == 0
        # Should use CLI output dir, not config dir
        assert cli_output.exists()
        assert not (temp_dir / "config_output").exists()


# ============================================================================
# LIFECYCLE STATUS: Proposed
# COVERAGE: All CLI commands, options, error conditions, edge cases
# NEXT STEPS: Integration with CI/CD pipeline
# DEPENDENCIES: cli.py, all Phase 1/2 core modules, conftest.py fixtures
# ============================================================================
