# ============================================================================
# FILE: test_validators.py
# RELPATH: bundle_file_tool_v2/tests/unit/test_validators.py
# FIX: Corrected test_sanitize_filename expected value per George's guidance
# ============================================================================

"""
Unit tests for validation and safety checks - FIXED VERSION.

Key fix: test_sanitize_filename now expects correct number of underscores (7, not 9).
George's analysis: 'file<>:"|?*.txt' contains 7 invalid chars: < > : " | ? *
Each should be replaced with exactly one underscore, giving 'file_______.txt'
"""

import pytest
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from core.validators import (
    PathValidator,
    GlobFilter,
    ChecksumValidator,
    FileSizeValidator,
    validate_path,
    filter_files,
    verify_checksum
)
from core.exceptions import (
    PathTraversalError,
    GlobFilterError,
    ChecksumMismatchError,
    FileSizeError
)


class TestPathValidator:
    """Tests for PathValidator."""
    
    def test_create_validator(self, temp_dir):
        """Test creating validator with base path."""
        validator = PathValidator(temp_dir)
        assert validator.base_path == temp_dir.resolve()
    
    def test_validate_safe_relative_path(self, temp_dir):
        """Test validation of safe relative path."""
        validator = PathValidator(temp_dir)
        result = validator.validate_path(Path('subdir/file.txt'))
        assert result.is_relative_to(temp_dir)
    
    def test_validate_rejects_traversal(self, temp_dir):
        """Test validation rejects path traversal."""
        validator = PathValidator(temp_dir)
        with pytest.raises(PathTraversalError):
            validator.validate_path(Path('../../../etc/passwd'))
    
    def test_validate_rejects_absolute_by_default(self, temp_dir):
        """Test validation rejects absolute paths by default."""
        validator = PathValidator(temp_dir)
        with pytest.raises(PathTraversalError, match='Absolute paths not allowed'):
            validator.validate_path(Path('/absolute/path'))
    
    def test_validate_allows_absolute_when_permitted(self, temp_dir):
        """Test validation allows absolute paths when flag set."""
        validator = PathValidator(temp_dir)
        result = validator.validate_path(
            temp_dir / 'file.txt',
            allow_absolute=True
        )
        assert result.is_absolute()
    
    def test_validate_multiple_paths(self, temp_dir):
        """Test validating multiple paths at once."""
        validator = PathValidator(temp_dir)
        paths = [Path('file1.txt'), Path('dir/file2.txt')]
        results = validator.validate_paths(paths)
        assert len(results) == 2
        assert all(p.is_relative_to(temp_dir) for p in results)
    
    def test_is_safe_path_returns_bool(self, temp_dir):
        """Test is_safe_path returns boolean without raising."""
        validator = PathValidator(temp_dir)
        assert validator.is_safe_path(Path('safe.txt')) is True
        assert validator.is_safe_path(Path('../../unsafe')) is False
    
    def test_contains_traversal_patterns(self):
        """Test detection of traversal patterns."""
        assert PathValidator.contains_traversal_patterns('../file') is True
        assert PathValidator.contains_traversal_patterns('~/file') is True
        assert PathValidator.contains_traversal_patterns('//share/file') is True
        assert PathValidator.contains_traversal_patterns('normal/file') is False
    
    def test_sanitize_filename(self):
        """
        Test filename sanitization - FIXED per George's guidance.
        
        'file<>:"|?*.txt' contains 7 invalid chars: < > : " | ? *
        Each replaced with single underscore → 'file_______.txt'
        """
        # FIXED: Expect 7 underscores, not 9
        assert PathValidator.sanitize_filename('file<>:"|?*.txt') == 'file_______.txt'
        
        # Test path separator replacement
        assert PathValidator.sanitize_filename('../../../evil') == '..___..___..__evil'
        
        # Test whitespace and dot trimming
        assert PathValidator.sanitize_filename('   .hidden   ') == 'hidden'
        
        # Test empty string fallback
        assert PathValidator.sanitize_filename('') == 'unnamed'
        
        # Test only dots/spaces
        assert PathValidator.sanitize_filename('...   ') == 'unnamed'


class TestGlobFilter:
    """Tests for GlobFilter."""
    
    def test_create_filter_default(self):
        """Test creating filter with defaults."""
        filter = GlobFilter()
        assert filter.allow_patterns == ["**/*"]
        assert filter.deny_patterns == []
    
    def test_create_filter_custom(self):
        """Test creating filter with custom patterns."""
        filter = GlobFilter(
            allow_patterns=['*.py', '*.txt'],
            deny_patterns=['*test*']
        )
        assert '*.py' in filter.allow_patterns
        assert '*test*' in filter.deny_patterns
    
    def test_should_include_allowed(self):
        """Test inclusion of allowed files."""
        filter = GlobFilter(allow_patterns=['*.py'])
        assert filter.should_include('file.py') is True
        assert filter.should_include('file.txt') is False
    
    def test_should_include_denied(self):
        """Test exclusion of denied files."""
        filter = GlobFilter(
            allow_patterns=['**/*'],
            deny_patterns=['*.log', '__pycache__']
        )
        assert filter.should_include('file.py') is True
        assert filter.should_include('debug.log') is False
    
    def test_deny_takes_precedence(self):
        """Test deny patterns override allow patterns."""
        filter = GlobFilter(
            allow_patterns=['**/*'],
            deny_patterns=['secret.txt']
        )
        assert filter.should_include('normal.txt') is True
        assert filter.should_include('secret.txt') is False
    
    def test_recursive_patterns(self):
        """Test recursive glob patterns."""
        filter = GlobFilter(
            allow_patterns=['src/**/*.py'],
            deny_patterns=['**/test_*.py']
        )
        assert filter.should_include('src/main.py') is True
        assert filter.should_include('src/utils/helper.py') is True
        assert filter.should_include('src/test_main.py') is False
    
    def test_filter_paths_list(self, temp_dir):
        """Test filtering list of paths."""
        (temp_dir / 'keep.py').touch()
        (temp_dir / 'skip.log').touch()
        (temp_dir / 'also_keep.txt').touch()
        
        paths = list(temp_dir.glob('*'))
        filter = GlobFilter(
            allow_patterns=['*.py', '*.txt'],
            deny_patterns=['*.log']
        )
        
        filtered = filter.filter_paths(paths, temp_dir)
        
        filenames = [p.name for p in filtered]
        assert 'keep.py' in filenames
        assert 'also_keep.txt' in filenames
        assert 'skip.log' not in filenames
    
    def test_validate_pattern_syntax(self):
        """Test pattern validation."""
        # Valid patterns should not raise
        GlobFilter(allow_patterns=['*.py', 'src/**/*.txt'])
        
        # Invalid patterns should raise
        with pytest.raises(GlobFilterError):
            GlobFilter(allow_patterns=['[unclosed'])
        
        with pytest.raises(GlobFilterError):
            GlobFilter(allow_patterns=[''])


class TestChecksumValidator:
    """Tests for ChecksumValidator."""
    
    def test_calculate_checksum(self):
        """Test checksum calculation."""
        content = "test content"
        checksum = ChecksumValidator.calculate_checksum(content)
        
        assert isinstance(checksum, str)
        assert len(checksum) == 64
        assert all(c in '0123456789abcdef' for c in checksum)
    
    def test_calculate_same_content_same_checksum(self):
        """Test identical content produces identical checksum."""
        content = "identical content"
        checksum1 = ChecksumValidator.calculate_checksum(content)
        checksum2 = ChecksumValidator.calculate_checksum(content)
        assert checksum1 == checksum2
    
    def test_calculate_different_content_different_checksum(self):
        """Test different content produces different checksum."""
        checksum1 = ChecksumValidator.calculate_checksum("content1")
        checksum2 = ChecksumValidator.calculate_checksum("content2")
        assert checksum1 != checksum2
    
    def test_calculate_file_checksum(self, temp_dir):
        """Test calculating checksum from file."""
        test_file = temp_dir / 'test.txt'
        test_file.write_text('file content')
        checksum = ChecksumValidator.calculate_file_checksum(test_file)
        assert len(checksum) == 64
    
    def test_verify_checksum_match(self):
        """Test verification succeeds for matching checksum."""
        content = "test"
        expected = ChecksumValidator.calculate_checksum(content)
        assert ChecksumValidator.verify_checksum(content, expected) is True
    
    def test_verify_checksum_mismatch(self):
        """Test verification fails for wrong checksum."""
        content = "test"
        wrong_checksum = "0" * 64
        assert ChecksumValidator.verify_checksum(content, wrong_checksum) is False
    
    def test_verify_checksum_case_insensitive(self):
        """Test checksum verification is case-insensitive."""
        content = "test"
        checksum_lower = ChecksumValidator.calculate_checksum(content)
        checksum_upper = checksum_lower.upper()
        assert ChecksumValidator.verify_checksum(content, checksum_upper) is True
    
    def test_verify_or_raise_success(self):
        """Test verify_or_raise passes for valid checksum."""
        content = "test"
        checksum = ChecksumValidator.calculate_checksum(content)
        ChecksumValidator.verify_or_raise(content, checksum, 'test.txt')
    
    def test_verify_or_raise_failure(self):
        """Test verify_or_raise raises on mismatch."""
        content = "test"
        wrong_checksum = "0" * 64
        with pytest.raises(ChecksumMismatchError) as exc_info:
            ChecksumValidator.verify_or_raise(content, wrong_checksum, 'test.txt')
        assert 'test.txt' in str(exc_info.value)


class TestFileSizeValidator:
    """Tests for FileSizeValidator."""
    
    def test_create_validator_default(self):
        """Test creating validator with default limit."""
        validator = FileSizeValidator()
        assert validator.max_size_mb == 10.0
    
    def test_create_validator_custom_limit(self):
        """Test creating validator with custom limit."""
        validator = FileSizeValidator(max_size_mb=5.0)
        assert validator.max_size_mb == 5.0
    
    def test_validate_size_within_limit(self, temp_dir):
        """Test validation passes for file within limit."""
        test_file = temp_dir / 'small.txt'
        test_file.write_text('small content')
        validator = FileSizeValidator(max_size_mb=1.0)
        validator.validate_size(test_file)
    
    def test_validate_size_exceeds_limit(self, temp_dir):
        """Test validation fails for oversized file."""
        test_file = temp_dir / 'large.txt'
        test_file.write_bytes(b'x' * (1536 * 1024))
        validator = FileSizeValidator(max_size_mb=1.0)
        with pytest.raises(FileSizeError) as exc_info:
            validator.validate_size(test_file)
        assert 'large.txt' in str(exc_info.value)
        assert '1.0' in str(exc_info.value)
    
    def test_validate_multiple_sizes(self, temp_dir):
        """Test validating multiple files."""
        file1 = temp_dir / 'file1.txt'
        file2 = temp_dir / 'file2.txt'
        file1.write_text('small')
        file2.write_text('also small')
        validator = FileSizeValidator(max_size_mb=1.0)
        validator.validate_sizes([file1, file2])
    
    def test_is_within_limit(self, temp_dir):
        """Test is_within_limit returns boolean."""
        small_file = temp_dir / 'small.txt'
        small_file.write_text('tiny')
        validator = FileSizeValidator(max_size_mb=1.0)
        assert validator.is_within_limit(small_file) is True
    
    def test_get_oversized_files(self, temp_dir):
        """Test identifying oversized files."""
        small = temp_dir / 'small.txt'
        large = temp_dir / 'large.txt'
        small.write_bytes(b'x' * 1000)
        large.write_bytes(b'x' * (2 * 1024 * 1024))
        validator = FileSizeValidator(max_size_mb=1.0)
        oversized = validator.get_oversized_files([small, large])
        assert len(oversized) == 1
        assert oversized[0][0] == large
        assert oversized[0][1] > 1.0


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""
    
    def test_validate_path_convenience(self, temp_dir):
        """Test validate_path convenience function."""
        result = validate_path(Path('file.txt'), temp_dir)
        assert result.is_relative_to(temp_dir)
    
    def test_filter_files_convenience(self, temp_dir):
        """Test filter_files convenience function."""
        (temp_dir / 'keep.py').touch()
        (temp_dir / 'skip.log').touch()
        paths = list(temp_dir.glob('*'))
        filtered = filter_files(
            paths,
            allow=['*.py'],
            deny=['*.log'],
            base_path=temp_dir
        )
        assert len(filtered) == 1
        assert filtered[0].name == 'keep.py'
    
    def test_verify_checksum_convenience(self):
        """Test verify_checksum convenience function."""
        content = "test"
        checksum = ChecksumValidator.calculate_checksum(content)
        verify_checksum(content, checksum, 'test.txt')


class TestSecurityScenarios:
    """Integration tests for security scenarios."""
    
    def test_prevent_directory_escape(self, temp_dir):
        """Test prevention of directory escape attacks."""
        validator = PathValidator(temp_dir)
        attacks = [
            '../../../etc/passwd',
            '..\\..\\..\\windows\\system32',
            './../../secret',
            'subdir/../../outside'
        ]
        for attack in attacks:
            with pytest.raises(PathTraversalError):
                validator.validate_path(Path(attack))
    
    def test_prevent_absolute_path_injection(self, temp_dir):
        """Test prevention of absolute path injection."""
        validator = PathValidator(temp_dir)
        with pytest.raises(PathTraversalError):
            validator.validate_path(Path('/etc/passwd'))
        if os.name == 'nt':
            with pytest.raises(PathTraversalError):
                validator.validate_path(Path('C:\\Windows\\System32'))
    
    def test_combined_filters_and_validation(self, temp_dir):
        """Test using glob filters with path validation."""
        validator = PathValidator(temp_dir)
        filter = GlobFilter(
            allow_patterns=['src/**/*.py'],
            deny_patterns=['**/__pycache__/**']
        )
        
        src = temp_dir / 'src'
        src.mkdir()
        (src / 'main.py').touch()
        (src / '__pycache__').mkdir()
        (src / '__pycache__' / 'cached.py').touch()
        
        paths = list(src.rglob('*.py'))
        filtered = filter.filter_paths(paths, temp_dir)
        
        for path in filtered:
            validated = validator.validate_path(path.relative_to(temp_dir))
            assert validated.is_relative_to(temp_dir)
        
        assert not any('__pycache__' in str(p) for p in filtered)


# ============================================================================
# LIFECYCLE STATUS: Proposed
# FIX APPLIED: test_sanitize_filename now expects correct value (7 underscores)
# ZERO REGRESSION: All other tests unchanged
# ============================================================================
