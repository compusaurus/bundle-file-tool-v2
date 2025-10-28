# ============================================================================
# SOURCEFILE: parser.py
# RELPATH: bundle_file_tool_v2/src/core/parser.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.0
# LIFECYCLE: Proposed
# DESCRIPTION: Main parser with profile registry and auto-detection
# ============================================================================

"""
Bundle Parser Module.

This module provides the main parsing interface for Bundle File Tool v2.1,
including profile registry, auto-detection, and unified parsing API.
"""

from typing import Optional, List, Dict, Type
from pathlib import Path
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.models import BundleManifest
from core.profiles.base import ProfileBase
from core.profiles.plain_marker import PlainMarkerProfile
from core.exceptions import (
    ProfileNotFoundError,
    ProfileDetectionError,
    ProfileParseError,
    BundleReadError
)


class ProfileRegistry:
    """
    Registry for managing available bundle format profiles.
    
    Provides profile registration, lookup, and enumeration capabilities.
    """
    
    def __init__(self):
        """Initialize registry with built-in profiles."""
        self._profiles: Dict[str, Type[ProfileBase]] = {}
        self._register_builtin_profiles()
    
    def _register_builtin_profiles(self):
        """Register built-in profile implementations."""
        # Register Plain Marker (v1.x compatibility)
        self.register(PlainMarkerProfile)
        
        # Future profiles will be registered here:
        # self.register(MarkdownFenceProfile)
        # self.register(JSONLProfile)
    
    def register(self, profile_class: Type[ProfileBase]) -> None:
        """
        Register a profile class.
        
        Args:
            profile_class: Profile class (not instance) to register
            
        Raises:
            TypeError: If profile_class is not a ProfileBase subclass
        """
        if not issubclass(profile_class, ProfileBase):
            raise TypeError(f"{profile_class.__name__} must be a ProfileBase subclass")
        
        # Instantiate to get profile name
        instance = profile_class()
        profile_name = instance.profile_name
        
        if profile_name in self._profiles:
            # Allow re-registration (useful for testing/reloading)
            pass
        
        self._profiles[profile_name] = profile_class
    
    def get(self, profile_name: str) -> ProfileBase:
        """
        Get a profile instance by name.
        
        Args:
            profile_name: Name of the profile to retrieve
            
        Returns:
            Profile instance
            
        Raises:
            ProfileNotFoundError: If profile not found
        """
        if profile_name not in self._profiles:
            raise ProfileNotFoundError(profile_name, list(self._profiles.keys()))
        
        return self._profiles[profile_name]()
    
    def list_profiles(self) -> List[str]:
        """
        List all registered profile names.
        
        Returns:
            List of profile name strings
        """
        return list(self._profiles.keys())
    
    def get_all_profiles(self) -> List[ProfileBase]:
        """
        Get instances of all registered profiles.
        
        Returns:
            List of profile instances
        """
        return [profile_class() for profile_class in self._profiles.values()]

    def _register_builtin_profiles(self):
        """Register built-in profile implementations."""
        # Register Plain Marker (v1.x compatibility)
        self.register(PlainMarkerProfile)
        
        # Register Markdown Fence (v2.1 default, AI-friendly)
        from core.profiles.markdown_fence import MarkdownFenceProfile
        self.register(MarkdownFenceProfile)
        
        # Future profiles will be registered here:
        # self.register(JSONLProfile)

class BundleParser:
    """
    Main parser for bundle files.
    
    Provides high-level parsing interface with profile selection and
    auto-detection capabilities.
    """
    
    def __init__(self, registry: Optional[ProfileRegistry] = None):
        """
        Initialize parser.
        
        Args:
            registry: Optional profile registry. If None, uses default registry.
        """
        self.registry = registry or ProfileRegistry()
    
    def parse(self, 
              text: str, 
              profile_name: Optional[str] = None,
              auto_detect: bool = True) -> BundleManifest:
        """
        Parse bundle text into a manifest.
        
        Args:
            text: Raw bundle file content as string
            profile_name: Specific profile to use. If None and auto_detect=True,
                         will attempt auto-detection
            auto_detect: If True and profile_name is None, attempt auto-detection
            
        Returns:
            Parsed BundleManifest
            
        Raises:
            ProfileNotFoundError: If specified profile doesn't exist
            ProfileDetectionError: If auto-detection fails
            ProfileParseError: If parsing fails
            
        Example:
            >>> parser = BundleParser()
            >>> manifest = parser.parse(bundle_text)  # Auto-detect
            >>> manifest = parser.parse(bundle_text, profile_name='plain_marker')
        """
        if profile_name:
            # Use specified profile
            profile = self.registry.get(profile_name)
            return self._parse_with_profile(text, profile)
        
        elif auto_detect:
            # Auto-detect profile
            profile = self._detect_profile(text)
            return self._parse_with_profile(text, profile)
        
        else:
            raise ValueError("Must specify profile_name or enable auto_detect")
    
    def parse_file(self,
                   file_path: Path,
                   profile_name: Optional[str] = None,
                   auto_detect: bool = True) -> BundleManifest:
        """
        Parse a bundle file from disk.
        
        Args:
            file_path: Path to bundle file
            profile_name: Specific profile to use
            auto_detect: If True and profile_name is None, attempt auto-detection
            
        Returns:
            Parsed BundleManifest
            
        Raises:
            BundleReadError: If file cannot be read
            ProfileNotFoundError: If specified profile doesn't exist
            ProfileDetectionError: If auto-detection fails
            ProfileParseError: If parsing fails
        """
        try:
            text = Path(file_path).read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            raise BundleReadError(str(file_path), str(e))
        
        return self.parse(text, profile_name, auto_detect)
    
    def _detect_profile(self, text: str) -> ProfileBase:
        """
        Auto-detect the appropriate profile for the given text.
        
        Strategy:
        1. Try each registered profile's detect_format() method
        2. Use first profile that returns True
        3. If none match, raise ProfileDetectionError
        
        Args:
            text: Bundle text to analyze
            
        Returns:
            Profile instance that matched
            
        Raises:
            ProfileDetectionError: If no profile matches
        """
        # Get all profiles for detection
        profiles = self.registry.get_all_profiles()
        
        # Try each profile's detection method
        attempted = []
        for profile in profiles:
            attempted.append(profile.profile_name)
            
            # Use first 2KB for detection (performance optimization)
            snippet = text[:2048]
            
            if profile.detect_format(snippet):
                return profile
        
        # No profile matched
        raise ProfileDetectionError(attempted)
    
    def _parse_with_profile(self, text: str, profile: ProfileBase) -> BundleManifest:
        """
        Parse text using a specific profile.
        
        Args:
            text: Bundle text to parse
            profile: Profile instance to use
            
        Returns:
            Parsed BundleManifest
            
        Raises:
            ProfileParseError: If parsing fails
        """
        try:
            manifest = profile.parse_stream(text)
            return manifest
        except ProfileParseError:
            # Re-raise profile errors as-is
            raise
        except Exception as e:
            # Wrap unexpected errors
            raise ProfileParseError(
                profile.profile_name,
                f"Unexpected error during parsing: {str(e)}"
            )
    
    def detect_profile_name(self, text: str) -> str:
        """
        Detect profile name without parsing.
        
        Useful for showing detected format to users before parsing.
        
        Args:
            text: Bundle text to analyze
            
        Returns:
            Detected profile name
            
        Raises:
            ProfileDetectionError: If no profile matches
        """
        profile = self._detect_profile(text)
        return profile.profile_name
    
    def validate_bundle(self, text: str, profile_name: Optional[str] = None) -> Dict:
        """
        Validate a bundle without fully parsing it.
        
        Performs quick validation checks and returns a summary report.
        
        Args:
            text: Bundle text to validate
            profile_name: Specific profile to use, or None for auto-detect
            
        Returns:
            Dictionary with validation results:
            {
                'valid': bool,
                'profile': str,
                'file_count': int,
                'errors': List[str],
                'warnings': List[str]
            }
        """
        result = {
            'valid': True,
            'profile': None,
            'file_count': 0,
            'errors': [],
            'warnings': []
        }
        
        try:
            # Detect or get profile
            if profile_name:
                profile = self.registry.get(profile_name)
            else:
                profile = self._detect_profile(text)
            
            result['profile'] = profile.profile_name
            
            # Try parsing
            manifest = profile.parse_stream(text)
            result['file_count'] = manifest.get_file_count()
            
            # Check for issues
            if manifest.get_file_count() == 0:
                result['warnings'].append("Bundle contains no files")
            
            # Check checksums if present
            checksum_results = manifest.verify_all_checksums()
            failed_checksums = [path for path, valid in checksum_results.items() if not valid]
            if failed_checksums:
                result['errors'].append(f"Checksum verification failed for: {', '.join(failed_checksums)}")
                result['valid'] = False
            
        except ProfileDetectionError as e:
            result['valid'] = False
            result['errors'].append(f"Profile detection failed: {str(e)}")
        except ProfileParseError as e:
            result['valid'] = False
            result['profile'] = e.profile_name
            result['errors'].append(f"Parse error: {e.reason}")
        except Exception as e:
            result['valid'] = False
            result['errors'].append(f"Unexpected error: {str(e)}")
        
        return result


# ============================================================================
# Convenience Functions
# ============================================================================

# Global parser instance for convenience
_default_parser = None


def get_default_parser() -> BundleParser:
    """Get the default global parser instance."""
    global _default_parser
    if _default_parser is None:
        _default_parser = BundleParser()
    return _default_parser


def parse_bundle(text: str, profile_name: Optional[str] = None) -> BundleManifest:
    """
    Convenience function to parse bundle text.
    
    Args:
        text: Bundle text to parse
        profile_name: Optional specific profile name
        
    Returns:
        Parsed BundleManifest
    """
    parser = get_default_parser()
    return parser.parse(text, profile_name)


def parse_bundle_file(file_path: Path) -> BundleManifest:
    """
    Convenience function to parse bundle file.
    
    Args:
        file_path: Path to bundle file
        
    Returns:
        Parsed BundleManifest
    """
    parser = get_default_parser()
    return parser.parse_file(file_path)


# ============================================================================
# LIFECYCLE STATUS: Proposed
# NEXT STEPS: Integration with writer module, add more profiles as implemented
# DEPENDENCIES: models.py, exceptions.py, profiles/*
# TESTS: Unit tests for registry, parser, auto-detection logic
# ============================================================================