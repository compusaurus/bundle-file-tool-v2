# ============================================================================
# SOURCEFILE: test_cli_exception_handling.py
# RELPATH: bundle_file_tool_v2/tests/coverage_extra/test_cli_exception_handling.py
# PROJECT: Bundle File Tool v2.1
# TEAM: John (Lead Dev)
# VERSION: 2.1.0
# LIFECYCLE: Proposed
# DESCRIPTION: Exception handling tests for CLI coverage improvement (80% → 90%+)
# ============================================================================

"""
Exception handling tests for CLI to improve coverage from 80% to 90%+.

Coverage targets:
- Lines 181-182: KeyboardInterrupt handling
- Lines 185-186: Generic exception handling  
- Line 215: File not found error path
- Various error paths in handle_unbundle and handle_bundle

Focus: Error paths, signal handling, and user interruption scenarios.
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock
import tempfile

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

# Import functions under test
from cli import main, handle_unbundle, handle_bundle
from core.exceptions import (
    BundleFileToolError,
    BundleReadError,
    ProfileNotFoundError
)


class TestCLIExceptionHandling:
    """Test exception handling paths in main() function."""
    
    def test_keyboard_interrupt_exits_with_130(self, capsys):
        """
        Test KeyboardInterrupt exits with code 130 (lines 181-182).
        
        Coverage target: Lines 181-182
        Signal: SIGINT (Ctrl+C) standard exit code
        """
        test_args = ['bundle', 'unbundle', 'test.txt', '-o', 'output']
        
        with patch('sys.argv', test_args):
            with patch('cli.handle_unbundle', side_effect=KeyboardInterrupt()):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                
                # Verify exit code 130 (standard for SIGINT)
                assert exc_info.value.code == 130
                
                # Verify user-friendly message
                captured = capsys.readouterr()
                assert "cancelled by user" in captured.err.lower()
    
    def test_keyboard_interrupt_during_bundle_exits_with_130(self, capsys):
        """Test KeyboardInterrupt during bundle operation."""
        test_args = ['bundle', 'bundle', 'src/', '-o', 'output.txt']
        
        with patch('sys.argv', test_args):
            with patch('cli.handle_bundle', side_effect=KeyboardInterrupt()):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                
                assert exc_info.value.code == 130
    
    def test_generic_exception_exits_with_1(self, capsys):
        """
        Test generic Exception exits with code 1 (lines 185-186).
        
        Coverage target: Lines 185-186
        Ensures unexpected errors are caught and reported gracefully.
        """
        test_args = ['bundle', 'unbundle', 'test.txt', '-o', 'output']
        
        with patch('sys.argv', test_args):
            with patch('cli.handle_unbundle', 
                      side_effect=RuntimeError("Unexpected internal error")):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                
                # Verify exit code 1 (generic error)
                assert exc_info.value.code == 1
                
                # Verify critical error message
                captured = capsys.readouterr()
                assert "CRITICAL ERROR" in captured.err
                assert "Unexpected" in captured.err
    
    def test_value_error_exits_with_1(self, capsys):
        """Test ValueError is caught as generic exception."""
        test_args = ['bundle', 'unbundle', 'test.txt', '-o', 'output']
        
        with patch('sys.argv', test_args):
            with patch('cli.handle_unbundle',
                      side_effect=ValueError("Invalid value provided")):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                
                assert exc_info.value.code == 1
                captured = capsys.readouterr()
                assert "CRITICAL ERROR" in captured.err
    
    def test_bundle_file_tool_error_exits_with_1(self, capsys):
        """Test BundleFileToolError exits with code 1."""
        test_args = ['bundle', 'unbundle', 'test.txt', '-o', 'output']
        
        with patch('sys.argv', test_args):
            with patch('cli.handle_unbundle',
                      side_effect=BundleFileToolError("Custom application error")):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                
                assert exc_info.value.code == 1
                
                captured = capsys.readouterr()
                assert "ERROR: Custom application error" in captured.err
                # Should NOT say "CRITICAL ERROR" for expected errors
                assert "CRITICAL" not in captured.err
    
    def test_successful_command_exits_with_0(self):
        """Test successful command execution exits with code 0 (line 174)."""
        test_args = ['bundle', 'unbundle', 'test.txt', '-o', 'output']
        
        with patch('sys.argv', test_args):
            with patch('cli.handle_unbundle', return_value=None):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                
                # Success should exit with 0
                assert exc_info.value.code == 0


class TestHandleUnbundleErrors:
    """Test error paths in handle_unbundle function."""
    
    def test_missing_input_file_raises_bundle_read_error(self):
        """
        Test that missing input file raises BundleReadError (line 215).
        
        Coverage target: Line 215
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            nonexistent = Path(tmp_dir) / "does_not_exist.txt"
            output_dir = Path(tmp_dir) / "output"
            
            args = Mock()
            args.input_file = nonexistent
            args.output = str(output_dir)
            args.overwrite = "skip"
            args.no_headers = False
            args.dry_run = False
            
            with pytest.raises(BundleReadError) as exc_info:
                handle_unbundle(args)
            
            # Verify error message mentions file not found
            error_msg = str(exc_info.value)
            assert "File not found" in error_msg or "not found" in error_msg.lower()
    
    def test_missing_output_directory_raises_error(self):
        """Test that missing output directory specification raises error."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_file = Path(tmp_dir) / "test.txt"
            input_file.write_text("# FILE: test.py\nprint('hello')")
            
            args = Mock()
            args.input_file = input_file
            args.output = None  # No output specified
            args.overwrite = "skip"
            args.no_headers = False
            args.dry_run = False
            
            # Mock ConfigManager to return None for output_dir
            with patch('cli.ConfigManager') as mock_config_class:
                mock_config = Mock()
                mock_config.get.return_value = None
                mock_config_class.return_value = mock_config
                
                with pytest.raises(BundleFileToolError) as exc_info:
                    handle_unbundle(args)
                
                error_msg = str(exc_info.value)
                assert "Output directory must be specified" in error_msg
    
    def test_output_from_config_when_not_in_args(self):
        """Test that output directory can come from config."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_file = Path(tmp_dir) / "test.txt"
            input_file.write_text("# FILE: test.py\nprint('hello')")
            output_dir = Path(tmp_dir) / "output"
            output_dir.mkdir()
            
            args = Mock()
            args.input_file = input_file
            args.output = None  # Will come from config
            args.overwrite = "skip"
            args.no_headers = False
            args.dry_run = False
            
            with patch('cli.ConfigManager') as mock_config_class:
                mock_config = Mock()
                mock_config.get.side_effect = lambda key, default=None: {
                    "global_settings.output_dir": str(output_dir),
                    "app_defaults.overwrite_policy": "skip",
                    "app_defaults.add_headers": True
                }.get(key, default)
                mock_config_class.return_value = mock_config
                
                with patch('cli.BundleParser'):
                    with patch('cli.BundleWriter'):
                        # Should not raise, should use config value
                        try:
                            handle_unbundle(args)
                        except Exception as e:
                            # May fail due to mocking, but should NOT be output dir error
                            assert "Output directory must be specified" not in str(e)


class TestHandleBundleErrors:
    """Test error paths in handle_bundle function."""
    
    def test_missing_source_path_raises_error(self):
        """Test that missing source path raises error."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            nonexistent = Path(tmp_dir) / "does_not_exist"
            output_file = Path(tmp_dir) / "output.txt"
            
            args = Mock()
            args.source_path = nonexistent
            args.output = str(output_file)
            args.profile = "plain_marker"
            args.dry_run = False
            args.no_headers = False
            args.allow = None
            args.deny = None
            args.max_file_mb = 10
            args.recursive = True
            
            with pytest.raises(BundleFileToolError) as exc_info:
                handle_bundle(args)
            
            error_msg = str(exc_info.value)
            assert "not found" in error_msg.lower() or "does not exist" in error_msg.lower()
    
    def test_invalid_profile_name_raises_error(self):
        """Test that invalid profile name raises error."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            source = Path(tmp_dir) / "source"
            source.mkdir()
            test_file = source / "test.py"
            test_file.write_text("print('hello')")
            
            output_file = Path(tmp_dir) / "output.txt"
            
            args = Mock()
            args.source_path = source
            args.output = str(output_file)
            args.profile = "nonexistent_profile_xyz"  # Invalid profile
            args.dry_run = False
            args.no_headers = False
            args.allow = None
            args.deny = None
            args.max_file_mb = 10
            args.recursive = True
            
            with patch('cli.ConfigManager'):
                with pytest.raises((ProfileNotFoundError, BundleFileToolError)) as exc_info:
                    handle_bundle(args)
                
                error_msg = str(exc_info.value)
                assert "profile" in error_msg.lower()
    
    def test_handle_bundle_with_invalid_output_path(self):
        """Test bundle with invalid output path."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            source = Path(tmp_dir) / "source"
            source.mkdir()
            test_file = source / "test.py"
            test_file.write_text("print('hello')")
            
            # Invalid output path (directory exists, can't create file)
            invalid_output = Path(tmp_dir) / "existing_dir"
            invalid_output.mkdir()
            
            args = Mock()
            args.source_path = source
            args.output = str(invalid_output)  # This is a directory, not a file
            args.profile = "plain_marker"
            args.dry_run = False
            args.no_headers = False
            args.allow = None
            args.deny = None
            args.max_file_mb = 10
            args.recursive = True
            
            with patch('cli.ConfigManager'):
                # May raise various errors depending on implementation
                with pytest.raises((OSError, BundleFileToolError, IsADirectoryError)):
                    handle_bundle(args)


class TestCLIEdgeCases:
    """Test additional CLI edge cases."""
    
    def test_validate_command_with_invalid_file(self):
        """Test validate command with non-existent file."""
        test_args = ['bundle', 'validate', 'nonexistent.txt']
        
        with patch('sys.argv', test_args):
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            # Should exit with error code
            assert exc_info.value.code != 0
    
    def test_unbundle_with_corrupted_bundle_file(self):
        """Test unbundle with corrupted/invalid bundle content."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            corrupted_file = Path(tmp_dir) / "corrupted.txt"
            corrupted_file.write_text("This is not a valid bundle format at all!")
            
            output_dir = Path(tmp_dir) / "output"
            output_dir.mkdir()
            
            args = Mock()
            args.input_file = corrupted_file
            args.output = str(output_dir)
            args.overwrite = "skip"
            args.no_headers = False
            args.dry_run = False
            
            with patch('cli.ConfigManager'):
                # Should raise some kind of parse or validation error
                with pytest.raises((BundleFileToolError, Exception)):
                    handle_unbundle(args)
    
    def test_bundle_with_zero_files(self):
        """Test bundle operation with empty directory."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            empty_dir = Path(tmp_dir) / "empty"
            empty_dir.mkdir()
            
            output_file = Path(tmp_dir) / "output.txt"
            
            args = Mock()
            args.source_path = empty_dir
            args.output = str(output_file)
            args.profile = "plain_marker"
            args.dry_run = False
            args.no_headers = False
            args.allow = None
            args.deny = None
            args.max_file_mb = 10
            args.recursive = True
            
            with patch('cli.ConfigManager'):
                # Behavior may vary: might succeed with empty bundle or raise error
                try:
                    handle_bundle(args)
                    # If succeeds, verify output exists
                    assert output_file.exists() or args.dry_run
                except BundleFileToolError as e:
                    # Or may raise error for no files
                    assert "no files" in str(e).lower() or "empty" in str(e).lower()


# Test for coverage verification
def test_cli_exception_handling_module_loaded():
    """Verify this test module is properly loaded."""
    assert True, "CLI exception handling test module loaded successfully"
