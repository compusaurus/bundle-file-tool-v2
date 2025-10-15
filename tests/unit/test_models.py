# ============================================================================
# FILE: test_models.py
# RELPATH: bundle_file_tool_v2/tests/unit/test_models.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.0
# LIFECYCLE: Proposed
# DESCRIPTION: Unit tests for BundleEntry and BundleManifest data models
# ============================================================================

"""
Unit tests for core data models.

Tests BundleEntry and BundleManifest dataclasses including validation,
helper methods, and checksum functionality.
"""

import pytest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from core.models import BundleEntry, BundleManifest


# ============================================================================
# BundleEntry Tests
# ============================================================================

class TestBundleEntry:
    """Tests for BundleEntry dataclass."""
    
    def test_create_text_entry(self):
        """Test creating a basic text file entry."""
        entry = BundleEntry(
            path="src/main.py",
            content="print('hello')\n",
            is_binary=False,
            encoding="utf-8",
            eol_style="LF"
        )
        
        assert entry.path == "src/main.py"
        assert entry.content == "print('hello')\n"
        assert entry.is_binary is False
        assert entry.encoding == "utf-8"
        assert entry.eol_style == "LF"
        assert entry.checksum is None
    
    def test_create_binary_entry(self):
        """Test creating a binary file entry."""
        entry = BundleEntry(
            path="assets/logo.png",
            content="iVBORw0KGgoAAAANSUhEUgAAAAEAAAAB...",
            is_binary=True,
            encoding="base64",
            eol_style="n/a"
        )
        
        assert entry.is_binary is True
        assert entry.encoding == "base64"
        assert entry.eol_style == "n/a"
    
    def test_path_normalization(self):
        """Test that backslashes are normalized to forward slashes."""
        entry = BundleEntry(
            path="src\\windows\\path.py",
            content="",
            is_binary=False,
            encoding="utf-8",
            eol_style="LF"
        )
        
        assert entry.path == "src/windows/path.py"
    
    def test_empty_path_raises_error(self):
        """Test that empty path raises ValueError."""
        with pytest.raises(ValueError, match="path cannot be empty"):
            BundleEntry(
                path="",
                content="test",
                is_binary=False,
                encoding="utf-8",
                eol_style="LF"
            )
    
    def test_invalid_eol_style_raises_error(self):
        """Test that invalid EOL style raises ValueError."""
        with pytest.raises(ValueError, match="Invalid eol_style"):
            BundleEntry(
                path="test.txt",
                content="test",
                is_binary=False,
                encoding="utf-8",
                eol_style="INVALID"
            )
    
    def test_valid_eol_styles(self):
        """Test all valid EOL styles."""
        valid_styles = ["LF", "CRLF", "CR", "MIXED", "n/a"]
        
        for style in valid_styles:
            entry = BundleEntry(
                path="test.txt",
                content="test",
                is_binary=False,
                encoding="utf-8",
                eol_style=style
            )
            assert entry.eol_style == style
    
    def test_blank_eol_coerced_to_lf_for_text(self):
        """Test that blank EOL is coerced to LF for text files."""
        entry = BundleEntry(
            path="test.txt",
            content="test",
            is_binary=False,
            encoding="utf-8",
            eol_style=""
        )
        assert entry.eol_style == "LF"
    
    def test_blank_eol_coerced_to_na_for_binary(self):
        """Test that blank EOL is coerced to n/a for binary files."""
        entry = BundleEntry(
            path="test.bin",
            content="dGVzdA==",
            is_binary=True,
            encoding="base64",
            eol_style=""
        )
        assert entry.eol_style == "n/a"
    
    def test_calculate_checksum(self):
        """Test checksum calculation."""
        entry = BundleEntry(
            path="test.txt",
            content="hello world",
            is_binary=False,
            encoding="utf-8",
            eol_style="LF"
        )
        
        checksum = entry.calculate_checksum()
        
        assert isinstance(checksum, str)
        assert len(checksum) == 64  # SHA-256 hex length
        assert all(c in '0123456789abcdef' for c in checksum)
    
    def test_verify_checksum_match(self):
        """Test checksum verification when checksums match."""
        content = "test content"
        entry = BundleEntry(
            path="test.txt",
            content=content,
            is_binary=False,
            encoding="utf-8",
            eol_style="LF",
            checksum=None
        )
        
        # Calculate and set checksum
        entry.checksum = entry.calculate_checksum()
        
        # Verify
        assert entry.verify_checksum() is True
    
    def test_verify_checksum_mismatch(self):
        """Test checksum verification when checksums don't match."""
        entry = BundleEntry(
            path="test.txt",
            content="current content",
            is_binary=False,
            encoding="utf-8",
            eol_style="LF",
            checksum="0" * 64  # Wrong checksum
        )
        
        assert entry.verify_checksum() is False
    
    def test_verify_checksum_none(self):
        """Test that verification returns True when no checksum set."""
        entry = BundleEntry(
            path="test.txt",
            content="test",
            is_binary=False,
            encoding="utf-8",
            eol_style="LF",
            checksum=None
        )
        
        assert entry.verify_checksum() is True
    
    def test_invalid_checksum_format(self):
        """Test that invalid checksum format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid checksum format"):
            BundleEntry(
                path="test.txt",
                content="test",
                is_binary=False,
                encoding="utf-8",
                eol_style="LF",
                checksum="invalid"  # Too short, not hex
            )
    
    def test_file_size_bytes_field(self):
        """Test that file_size_bytes field is properly handled."""
        entry = BundleEntry(
            path="test.txt",
            content="test",
            is_binary=False,
            encoding="utf-8",
            eol_style="LF",
            file_size_bytes=1024
        )
        
        assert entry.file_size_bytes == 1024
    
    def test_invalid_file_size_bytes(self):
        """Test that invalid file_size_bytes raises ValueError."""
        with pytest.raises(ValueError, match="Invalid file_size_bytes"):
            BundleEntry(
                path="test.txt",
                content="test",
                is_binary=False,
                encoding="utf-8",
                eol_style="LF",
                file_size_bytes=-1  # Negative not allowed
            )


# ============================================================================
# BundleManifest Tests
# ============================================================================

class TestBundleManifest:
    """Tests for BundleManifest dataclass."""
    
    def test_create_manifest(self, sample_text_entry):
        """Test creating a basic manifest."""
        manifest = BundleManifest(
            entries=[sample_text_entry],
            profile="plain_marker"
        )
        
        assert len(manifest.entries) == 1
        assert manifest.profile == "plain_marker"
        assert manifest.version == "2.1"
        assert isinstance(manifest.metadata, dict)
    
    def test_empty_manifest(self):
        """Test creating an empty manifest."""
        manifest = BundleManifest(
            entries=[],
            profile="plain_marker"
        )
        
        assert len(manifest.entries) == 0
        assert manifest.get_file_count() == 0
    
    def test_manifest_with_metadata(self):
        """Test manifest with custom metadata."""
        manifest = BundleManifest(
            entries=[],
            profile="md_fence",
            metadata={"source": "test", "created": "2025-10-02"}
        )
        
        assert manifest.metadata["source"] == "test"
        assert manifest.metadata["created"] == "2025-10-02"
    
    def test_empty_profile_raises_error(self):
        """Test that empty profile raises ValueError."""
        with pytest.raises(ValueError, match="profile cannot be empty"):
            BundleManifest(
                entries=[],
                profile=""
            )
    
    def test_duplicate_paths_raises_error(self, sample_text_entry):
        """Test that duplicate file paths raise ValueError."""
        duplicate = BundleEntry(
            path=sample_text_entry.path,  # Same path
            content="different content",
            is_binary=False,
            encoding="utf-8",
            eol_style="LF"
        )
        
        with pytest.raises(ValueError, match="Duplicate file paths"):
            BundleManifest(
                entries=[sample_text_entry, duplicate],
                profile="plain_marker"
            )
    
    def test_get_file_count(self, sample_text_entry, sample_binary_entry):
        """Test get_file_count method."""
        manifest = BundleManifest(
            entries=[sample_text_entry, sample_binary_entry],
            profile="plain_marker"
        )
        
        assert manifest.get_file_count() == 2
    
    def test_get_binary_count(self, sample_text_entry, sample_binary_entry):
        """Test get_binary_count method."""
        manifest = BundleManifest(
            entries=[sample_text_entry, sample_binary_entry],
            profile="plain_marker"
        )
        
        assert manifest.get_binary_count() == 1
    
    def test_get_text_count(self, sample_text_entry, sample_binary_entry, sample_html_entry):
        """Test get_text_count method."""
        manifest = BundleManifest(
            entries=[sample_text_entry, sample_binary_entry, sample_html_entry],
            profile="plain_marker"
        )
        
        assert manifest.get_text_count() == 2
    
    def test_get_entry_found(self, sample_text_entry):
        """Test get_entry when entry exists."""
        manifest = BundleManifest(
            entries=[sample_text_entry],
            profile="plain_marker"
        )
        
        entry = manifest.get_entry(sample_text_entry.path)
        
        assert entry is not None
        assert entry.path == sample_text_entry.path
    
    def test_get_entry_not_found(self, sample_text_entry):
        """Test get_entry when entry doesn't exist."""
        manifest = BundleManifest(
            entries=[sample_text_entry],
            profile="plain_marker"
        )
        
        entry = manifest.get_entry("nonexistent.txt")
        
        assert entry is None
    
    def test_get_entry_path_normalization(self, sample_text_entry):
        """Test get_entry with backslashes."""
        manifest = BundleManifest(
            entries=[sample_text_entry],
            profile="plain_marker"
        )
        
        # Use backslashes - should still find it
        entry = manifest.get_entry(sample_text_entry.path.replace('/', '\\'))
        
        assert entry is not None
    
    def test_verify_all_checksums_success(self):
        """Test verify_all_checksums when all match."""
        entry1 = BundleEntry(
            path="file1.txt",
            content="content1",
            is_binary=False,
            encoding="utf-8",
            eol_style="LF"
        )
        entry1.checksum = entry1.calculate_checksum()
        
        entry2 = BundleEntry(
            path="file2.txt",
            content="content2",
            is_binary=False,
            encoding="utf-8",
            eol_style="LF"
        )
        entry2.checksum = entry2.calculate_checksum()
        
        manifest = BundleManifest(
            entries=[entry1, entry2],
            profile="plain_marker"
        )
        
        results = manifest.verify_all_checksums()
        
        assert len(results) == 2
        assert all(results.values())
    
    def test_verify_all_checksums_failure(self):
        """Test verify_all_checksums when checksums don't match."""
        entry = BundleEntry(
            path="file.txt",
            content="content",
            is_binary=False,
            encoding="utf-8",
            eol_style="LF",
            checksum="0" * 64  # Wrong checksum
        )
        
        manifest = BundleManifest(
            entries=[entry],
            profile="plain_marker"
        )
        
        results = manifest.verify_all_checksums()
        
        assert results["file.txt"] is False
    
    def test_add_entry_success(self):
        """Test adding entry to manifest."""
        manifest = BundleManifest(
            entries=[],
            profile="plain_marker"
        )
        
        entry = BundleEntry(
            path="new.txt",
            content="test",
            is_binary=False,
            encoding="utf-8",
            eol_style="LF"
        )
        
        manifest.add_entry(entry)
        
        assert manifest.get_file_count() == 1
        assert manifest.get_entry("new.txt") is not None
    
    def test_add_entry_duplicate_raises_error(self, sample_text_entry):
        """Test adding duplicate entry raises error."""
        manifest = BundleManifest(
            entries=[sample_text_entry],
            profile="plain_marker"
        )
        
        duplicate = BundleEntry(
            path=sample_text_entry.path,
            content="different",
            is_binary=False,
            encoding="utf-8",
            eol_style="LF"
        )
        
        with pytest.raises(ValueError, match="already exists"):
            manifest.add_entry(duplicate)
    
    def test_remove_entry_success(self, sample_text_entry):
        """Test removing entry from manifest."""
        manifest = BundleManifest(
            entries=[sample_text_entry],
            profile="plain_marker"
        )
        
        result = manifest.remove_entry(sample_text_entry.path)
        
        assert result is True
        assert manifest.get_file_count() == 0
    
    def test_remove_entry_not_found(self, sample_text_entry):
        """Test removing nonexistent entry returns False."""
        manifest = BundleManifest(
            entries=[sample_text_entry],
            profile="plain_marker"
        )
        
        result = manifest.remove_entry("nonexistent.txt")
        
        assert result is False
        assert manifest.get_file_count() == 1
    
    def test_get_total_size_bytes(self):
        """Test get_total_size_bytes method."""
        entry1 = BundleEntry(
            path="file1.txt",
            content="content1",
            is_binary=False,
            encoding="utf-8",
            eol_style="LF",
            file_size_bytes=100
        )
        
        entry2 = BundleEntry(
            path="file2.txt",
            content="content2",
            is_binary=False,
            encoding="utf-8",
            eol_style="LF",
            file_size_bytes=200
        )
        
        manifest = BundleManifest(
            entries=[entry1, entry2],
            profile="plain_marker"
        )
        
        assert manifest.get_total_size_bytes() == 300
    
    def test_get_total_size_bytes_missing_sizes(self):
        """Test get_total_size_bytes when some entries lack size info."""
        entry1 = BundleEntry(
            path="file1.txt",
            content="content1",
            is_binary=False,
            encoding="utf-8",
            eol_style="LF",
            file_size_bytes=100
        )
        
        entry2 = BundleEntry(
            path="file2.txt",
            content="content2",
            is_binary=False,
            encoding="utf-8",
            eol_style="LF",
            file_size_bytes=None  # No size info
        )
        
        manifest = BundleManifest(
            entries=[entry1, entry2],
            profile="plain_marker"
        )
        
        assert manifest.get_total_size_bytes() == 100


# ============================================================================
# LIFECYCLE STATUS: Proposed
# COVERAGE: 100% of BundleEntry and BundleManifest public methods
# NEXT STEPS: Add integration tests, parametrized encoding tests
# ============================================================================
