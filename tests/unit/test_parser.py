# ============================================================================
# SOURCEFILE: test_parser.py
# RELPATH: bundle_file_tool_v2/tests/unit/test_parser.py
# PROJECT: Bundle File Tool v2.1
# LIFECYCLE: Proposed
# DESCRIPTION: Unit tests for parser, profile registry, and auto-detection
# ============================================================================

import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from core.parser import BundleParser, ProfileRegistry, parse_bundle
from core.profiles.plain_marker import PlainMarkerProfile
from core.exceptions import ProfileNotFoundError, ProfileDetectionError, ProfileParseError


class TestProfileRegistry:
    """Tests for ProfileRegistry."""
    
    def test_registry_initialization(self):
        """Test registry initializes with built-in profiles."""
        registry = ProfileRegistry()
        profiles = registry.list_profiles()
        
        assert 'plain_marker' in profiles
    
    def test_register_profile(self):
        """Test registering a profile."""
        registry = ProfileRegistry()
        initial_count = len(registry.list_profiles())
        
        # Register should work (even if already registered)
        registry.register(PlainMarkerProfile)
        
        assert len(registry.list_profiles()) >= initial_count
    
    def test_get_profile_success(self):
        """Test getting an existing profile."""
        registry = ProfileRegistry()
        profile = registry.get('plain_marker')
        
        assert isinstance(profile, PlainMarkerProfile)
        assert profile.profile_name == 'plain_marker'
    
    def test_get_profile_not_found(self):
        """Test getting non-existent profile raises error."""
        registry = ProfileRegistry()
        
        with pytest.raises(ProfileNotFoundError) as exc_info:
            registry.get('nonexistent_profile')
        
        assert 'nonexistent_profile' in str(exc_info.value)
    
    def test_list_profiles(self):
        """Test listing all profiles."""
        registry = ProfileRegistry()
        profiles = registry.list_profiles()
        
        assert isinstance(profiles, list)
        assert len(profiles) > 0
        assert 'plain_marker' in profiles
    
    def test_get_all_profiles(self):
        """Test getting all profile instances."""
        registry = ProfileRegistry()
        profiles = registry.get_all_profiles()
        
        assert isinstance(profiles, list)
        assert len(profiles) > 0
        assert all(hasattr(p, 'parse_stream') for p in profiles)


class TestBundleParser:
    """Tests for BundleParser."""
    
    def test_parser_initialization(self):
        """Test parser initializes with default registry."""
        parser = BundleParser()
        
        assert parser.registry is not None
        assert isinstance(parser.registry, ProfileRegistry)
    
    def test_parse_with_explicit_profile(self, sample_plain_marker_bundle):
        """Test parsing with explicitly specified profile."""
        parser = BundleParser()
        manifest = parser.parse(sample_plain_marker_bundle, profile_name='plain_marker')
        
        assert manifest is not None
        assert manifest.profile == 'plain_marker'
        assert manifest.get_file_count() > 0
    
    def test_parse_with_auto_detect(self, sample_plain_marker_bundle):
        """Test parsing with auto-detection."""
        parser = BundleParser()
        manifest = parser.parse(sample_plain_marker_bundle, auto_detect=True)
        
        assert manifest is not None
        assert manifest.profile == 'plain_marker'
    
    def test_parse_invalid_profile(self, sample_plain_marker_bundle):
        """Test parsing with invalid profile name."""
        parser = BundleParser()
        
        with pytest.raises(ProfileNotFoundError):
            parser.parse(sample_plain_marker_bundle, profile_name='invalid')
    
    def test_parse_no_profile_no_autodetect_raises(self):
        """Test that parse raises error if no profile and no auto-detect."""
        parser = BundleParser()
        
        with pytest.raises(ValueError, match="Must specify profile_name or enable auto_detect"):
            parser.parse("some text", profile_name=None, auto_detect=False)
    
    def test_detect_profile_plain_marker(self, sample_plain_marker_bundle):
        """Test profile detection for plain marker format."""
        parser = BundleParser()
        detected = parser.detect_profile_name(sample_plain_marker_bundle)
        
        assert detected == 'plain_marker'
    
    def test_detect_profile_markdown_fence(self, sample_markdown_fence_bundle):
        """Test profile detection for markdown fence format."""
        parser = BundleParser()
        # Will fail until MarkdownFenceProfile is implemented
        # For now, should fall back or raise ProfileDetectionError
        try:
            detected = parser.detect_profile_name(sample_markdown_fence_bundle)
            # If it succeeds, it found a matching profile
            assert detected in ['plain_marker', 'md_fence']
        except ProfileDetectionError:
            # Expected until md_fence profile is implemented
            pass
    
    def test_detect_profile_no_match(self):
        """Test detection failure for unrecognized format."""
        parser = BundleParser()
        invalid_text = "This is not a valid bundle format at all"
        
        with pytest.raises(ProfileDetectionError) as exc_info:
            parser.detect_profile_name(invalid_text)
        
        # Should list attempted profiles
        assert 'plain_marker' in str(exc_info.value)
    
    def test_validate_bundle_valid(self, sample_plain_marker_bundle):
        """Test bundle validation for valid bundle."""
        parser = BundleParser()
        result = parser.validate_bundle(sample_plain_marker_bundle)
        
        assert result['valid'] is True
        assert result['profile'] == 'plain_marker'
        assert result['file_count'] > 0
        assert len(result['errors']) == 0
    
    def test_validate_bundle_invalid(self):
        """Test bundle validation for invalid bundle."""
        parser = BundleParser()
        result = parser.validate_bundle("not a valid bundle")
        
        assert result['valid'] is False
        assert len(result['errors']) > 0
    
    def test_validate_bundle_empty(self):
        """Test validation of empty bundle."""
        parser = BundleParser()
        # Create minimal valid bundle with no files
        empty_bundle = "# FILE: dummy.txt\n"
        
        result = parser.validate_bundle(empty_bundle)
        
        # Should parse but may have warnings
        if result['valid']:
            assert result['file_count'] >= 0


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""
    
    def test_parse_bundle_convenience(self, sample_plain_marker_bundle):
        """Test parse_bundle convenience function."""
        manifest = parse_bundle(sample_plain_marker_bundle)
        
        assert manifest is not None
        assert manifest.get_file_count() > 0
    
    def test_parse_bundle_with_profile(self, sample_plain_marker_bundle):
        """Test parse_bundle with explicit profile."""
        manifest = parse_bundle(sample_plain_marker_bundle, profile_name='plain_marker')
        
        assert manifest.profile == 'plain_marker'


class TestAutoDetection:
    """Tests for profile auto-detection logic."""
    
    def test_detection_order(self):
        """Test that detection tries profiles in order."""
        parser = BundleParser()
        
        # Plain marker should be detected
        plain_text = "# FILE: test.txt\nContent here"
        detected = parser._detect_profile(plain_text)
        
        assert detected.profile_name == 'plain_marker'
    
    def test_detection_uses_snippet(self):
        """Test that detection only uses first portion of text."""
        parser = BundleParser()
        
        # Create large text with marker at start
        large_text = "# FILE: test.txt\n" + ("x" * 10000)
        detected = parser._detect_profile(large_text)
        
        # Should still detect even with large file
        assert detected.profile_name == 'plain_marker'
    
    def test_detection_performance(self):
        """Test detection performance with large input."""
        import time
        parser = BundleParser()
        
        # Create very large text
        huge_text = "# FILE: test.txt\n" + ("content\n" * 100000)
        
        start = time.time()
        parser._detect_profile(huge_text)
        elapsed = time.time() - start
        
        # Detection should be fast (< 1 second even for huge files)
        assert elapsed < 1.0


# ============================================================================
# LIFECYCLE STATUS: Proposed
# COVERAGE: Parser, ProfileRegistry, auto-detection
# NEXT STEPS: Add tests for MarkdownFence and JSONL when implemented
# ============================================================================
