# ============================================================================
# SOURCEFILE: test_exceptions.py
# RELPATH: bundle_file_tool_v2/tests/unit/test_exceptions.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.0
# LIFECYCLE: Proposed
# DESCRIPTION: Unit tests for exception hierarchy and error messages
# ============================================================================

"""
Unit tests for exception classes.

Tests exception instantiation, message formatting, and hierarchy.
Ensures all exceptions provide clear, actionable error information.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from core.exceptions import (
    BundleFileToolError,
    ProfileError,
    ProfileParseError,
    ProfileFormatError,
    ProfileNotFoundError,
    ProfileDetectionError,
    ValidationError,
    PathTraversalError,
    FileSizeError,
    ChecksumMismatchError,
    GlobFilterError,
    ConfigError,
    ConfigLoadError,
    ConfigMigrationError,
    ConfigValidationError,
    BundleIOError,
    BundleReadError,
    BundleWriteError,
    EncodingError,
    OperationError,
    OverwriteError,
    DryRunError
)


class TestExceptionHierarchy:
    """Tests for exception hierarchy structure."""
    
    def test_base_exception(self):
        """Test base BundleFileToolError."""
        exc = BundleFileToolError("base error")
        
        assert isinstance(exc, Exception)
        assert str(exc) == "base error"
    
    def test_profile_errors_inherit_base(self):
        """Test profile errors inherit from ProfileError."""
        assert issubclass(ProfileParseError, ProfileError)
        assert issubclass(ProfileFormatError, ProfileError)
        assert issubclass(ProfileNotFoundError, ProfileError)
        assert issubclass(ProfileDetectionError, ProfileError)
        assert issubclass(ProfileError, BundleFileToolError)
    
    def test_validation_errors_inherit_base(self):
        """Test validation errors inherit from ValidationError."""
        assert issubclass(PathTraversalError, ValidationError)
        assert issubclass(FileSizeError, ValidationError)
        assert issubclass(ChecksumMismatchError, ValidationError)
        assert issubclass(GlobFilterError, ValidationError)
        assert issubclass(ValidationError, BundleFileToolError)
    
    def test_config_errors_inherit_base(self):
        """Test config errors inherit from ConfigError."""
        assert issubclass(ConfigLoadError, ConfigError)
        assert issubclass(ConfigMigrationError, ConfigError)
        assert issubclass(ConfigValidationError, ConfigError)
        assert issubclass(ConfigError, BundleFileToolError)
    
    def test_io_errors_inherit_base(self):
        """Test I/O errors inherit from BundleIOError."""
        assert issubclass(BundleReadError, BundleIOError)
        assert issubclass(BundleWriteError, BundleIOError)
        assert issubclass(EncodingError, BundleIOError)
        assert issubclass(BundleIOError, BundleFileToolError)
    
    def test_operation_errors_inherit_base(self):
        """Test operation errors inherit from OperationError."""
        assert issubclass(OverwriteError, OperationError)
        assert issubclass(DryRunError, OperationError)
        assert issubclass(OperationError, BundleFileToolError)


class TestProfileExceptions:
    """Tests for profile-related exceptions."""
    
    def test_profile_parse_error(self):
        """Test ProfileParseError."""
        exc = ProfileParseError('plain_marker', 'invalid syntax', line_number=42)
        
        assert exc.profile_name == 'plain_marker'
        assert exc.reason == 'invalid syntax'
        assert exc.line_number == 42
        assert 'plain_marker' in str(exc)
        assert 'invalid syntax' in str(exc)
        assert '42' in str(exc)
    
    def test_profile_parse_error_without_line_number(self):
        """Test ProfileParseError without line number."""
        exc = ProfileParseError('plain_marker', 'error')
        
        assert exc.line_number is None
        assert 'line' not in str(exc).lower() or 'None' not in str(exc)
    
    def test_profile_format_error(self):
        """Test ProfileFormatError."""
        exc = ProfileFormatError('md_fence', 'unsupported binary')
        
        assert exc.profile_name == 'md_fence'
        assert exc.reason == 'unsupported binary'
        assert 'md_fence' in str(exc)
        assert 'unsupported binary' in str(exc)
    
    def test_profile_not_found_error(self):
        """Test ProfileNotFoundError."""
        exc = ProfileNotFoundError('nonexistent', ['plain_marker', 'md_fence'])
        
        assert exc.profile_name == 'nonexistent'
        assert exc.available_profiles == ['plain_marker', 'md_fence']
        assert 'nonexistent' in str(exc)
        assert 'plain_marker' in str(exc)
        assert 'md_fence' in str(exc)
    
    def test_profile_not_found_error_no_suggestions(self):
        """Test ProfileNotFoundError without available profiles."""
        exc = ProfileNotFoundError('nonexistent')
        
        assert exc.available_profiles == []
        # Should still mention the missing profile
        assert 'nonexistent' in str(exc)
    
    def test_profile_detection_error(self):
        """Test ProfileDetectionError."""
        exc = ProfileDetectionError(['plain_marker', 'md_fence', 'jsonl'])
        
        assert exc.attempted_profiles == ['plain_marker', 'md_fence', 'jsonl']
        assert 'plain_marker' in str(exc)
        assert 'detect' in str(exc).lower()


class TestValidationExceptions:
    """Tests for validation-related exceptions."""
    
    def test_path_traversal_error(self):
        """Test PathTraversalError."""
        exc = PathTraversalError('../../../etc/passwd', 'Path traversal detected')
        
        assert exc.path == '../../../etc/passwd'
        assert exc.reason == 'Path traversal detected'
        assert '../../../etc/passwd' in str(exc)
        assert 'traversal' in str(exc).lower()
    
    def test_path_traversal_error_default_reason(self):
        """Test PathTraversalError with default reason."""
        exc = PathTraversalError('../../unsafe')
        
        assert exc.reason == 'Path traversal detected'
    
    def test_file_size_error(self):
        """Test FileSizeError."""
        exc = FileSizeError('large.bin', 15.5, 10.0)
        
        assert exc.path == 'large.bin'
        assert exc.size_mb == 15.5
        assert exc.max_mb == 10.0
        assert 'large.bin' in str(exc)
        assert '15.5' in str(exc) or '15.50' in str(exc)
        assert '10.0' in str(exc) or '10.00' in str(exc)
    
    def test_checksum_mismatch_error(self):
        """Test ChecksumMismatchError."""
        expected = 'abc123def456' * 5 + '1234'
        actual = 'fed654cba321' * 5 + '4321'
        
        exc = ChecksumMismatchError('file.txt', expected, actual)
        
        assert exc.path == 'file.txt'
        assert exc.expected == expected
        assert exc.actual == actual
        assert 'file.txt' in str(exc)
        # Should show truncated checksums (first 16 chars)
        assert expected[:16] in str(exc)
        assert actual[:16] in str(exc)
    
    def test_glob_filter_error(self):
        """Test GlobFilterError."""
        exc = GlobFilterError('[unclosed', 'Unmatched brackets')
        
        assert exc.pattern == '[unclosed'
        assert exc.reason == 'Unmatched brackets'
        assert '[unclosed' in str(exc)
        assert 'Unmatched brackets' in str(exc)


class TestConfigExceptions:
    """Tests for config-related exceptions."""
    
    def test_config_load_error(self):
        """Test ConfigLoadError."""
        exc = ConfigLoadError('config.json', 'File not found')
        
        assert exc.config_file == 'config.json'
        assert exc.reason == 'File not found'
        assert 'config.json' in str(exc)
        assert 'not found' in str(exc).lower()
    
    def test_config_migration_error(self):
        """Test ConfigMigrationError."""
        exc = ConfigMigrationError('1.1.5', '2.1', 'Invalid key structure')
        
        assert exc.old_version == '1.1.5'
        assert exc.new_version == '2.1'
        assert exc.reason == 'Invalid key structure'
        assert '1.1.5' in str(exc)
        assert '2.1' in str(exc)
        assert 'Invalid key structure' in str(exc)
    
    def test_config_validation_error(self):
        """Test ConfigValidationError."""
        exc = ConfigValidationError('app_defaults.bundle_profile', 'invalid_profile', 'Must be plain_marker or md_fence')
        
        assert exc.key == 'app_defaults.bundle_profile'
        assert exc.value == 'invalid_profile'
        assert exc.reason == 'Must be plain_marker or md_fence'
        assert 'app_defaults.bundle_profile' in str(exc)
        assert 'Must be' in str(exc)


class TestIOExceptions:
    """Tests for I/O-related exceptions."""
    
    def test_bundle_read_error(self):
        """Test BundleReadError."""
        exc = BundleReadError('bundle.txt', 'Permission denied')
        
        assert exc.path == 'bundle.txt'
        assert exc.reason == 'Permission denied'
        assert 'bundle.txt' in str(exc)
        assert 'Permission denied' in str(exc)
    
    def test_bundle_write_error(self):
        """Test BundleWriteError."""
        exc = BundleWriteError('output/file.py', 'Disk full')
        
        assert exc.path == 'output/file.py'
        assert exc.reason == 'Disk full'
        assert 'output/file.py' in str(exc)
        assert 'Disk full' in str(exc)
    
    def test_encoding_error(self):
        """Test EncodingError."""
        exc = EncodingError('file.txt', 'utf-8', 'Invalid byte sequence')
        
        assert exc.path == 'file.txt'
        assert exc.encoding == 'utf-8'
        assert exc.reason == 'Invalid byte sequence'
        assert 'file.txt' in str(exc)
        assert 'utf-8' in str(exc)
        assert 'Invalid byte sequence' in str(exc)


class TestOperationExceptions:
    """Tests for operation-related exceptions."""
    
    def test_overwrite_error(self):
        """Test OverwriteError."""
        exc = OverwriteError('existing.txt')
        
        assert exc.path == 'existing.txt'
        assert 'existing.txt' in str(exc)
        assert 'exists' in str(exc).lower()
    
    def test_dry_run_error(self):
        """Test DryRunError."""
        exc = DryRunError('write file')
        
        assert exc.operation == 'write file'
        assert 'write file' in str(exc)
        assert 'dry-run' in str(exc).lower() or 'dry run' in str(exc).lower()


class TestExceptionUsage:
    """Tests for typical exception usage patterns."""
    
    def test_exception_can_be_caught_by_base(self):
        """Test specific exceptions can be caught by base class."""
        try:
            raise ProfileParseError('plain_marker', 'error')
        except BundleFileToolError:
            pass  # Should catch it
        else:
            pytest.fail("Exception not caught by base class")
    
    def test_exception_can_be_caught_by_category(self):
        """Test exceptions can be caught by category."""
        try:
            raise PathTraversalError('../../unsafe')
        except ValidationError:
            pass  # Should catch it
        else:
            pytest.fail("Exception not caught by category")
    
    def test_exception_attributes_accessible(self):
        """Test exception attributes are accessible after catching."""
        try:
            raise ProfileParseError('plain_marker', 'test error', line_number=10)
        except ProfileParseError as e:
            assert e.profile_name == 'plain_marker'
            assert e.reason == 'test error'
            assert e.line_number == 10
    
    def test_exception_repr(self):
        """Test exception string representation is informative."""
        exc = FileSizeError('big.bin', 100.5, 10.0)
        
        exc_str = str(exc)
        
        # Should contain all key information
        assert 'big.bin' in exc_str
        assert '100' in exc_str  # Size
        assert '10' in exc_str   # Limit


class TestExceptionMessages:
    """Tests for exception message quality."""
    
    def test_messages_are_actionable(self):
        """Test exception messages provide actionable information."""
        exc = ProfileNotFoundError('wrong_profile', ['plain_marker', 'md_fence'])
        msg = str(exc)
        
        # Should tell user what's wrong
        assert 'wrong_profile' in msg
        # Should suggest alternatives
        assert 'plain_marker' in msg
        assert 'md_fence' in msg
    
    def test_messages_include_context(self):
        """Test messages include relevant context."""
        exc = ConfigMigrationError('1.1.5', '2.1', 'Missing required key')
        msg = str(exc)
        
        # Should include versions and reason
        assert '1.1.5' in msg
        assert '2.1' in msg
        assert 'Missing required key' in msg
    
    def test_messages_are_clear(self):
        """Test messages use clear, non-technical language."""
        exc = OverwriteError('file.txt')
        msg = str(exc)
        
        # Should be understandable
        assert 'file.txt' in msg
        assert 'exists' in msg.lower() or 'overwrite' in msg.lower()


# ============================================================================
# LIFECYCLE STATUS: Proposed
# COVERAGE: Complete exception hierarchy and message formatting
# NEXT STEPS: None - exceptions fully tested
# ============================================================================
