# ============================================================================
# SOURCEILE: base.py
# RELPATH: bundle_file_tool_v2/src/core/profiles/base.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.0
# LIFECYCLE: Proposed
# DESCRIPTION: Abstract base class defining the profile interface contract
# ARCHITECT: George (specification in Response to v2.1k3 Assessment)
# ============================================================================

"""
Profile Base Interface for Bundle File Tool v2.1.

This module defines the abstract base class that all bundle format profiles
must implement, ensuring a consistent interface for the parser and writer.
"""

from abc import ABC, abstractmethod
from typing import Dict
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.models import BundleManifest
from core.exceptions import ProfileParseError, ProfileFormatError, EncodingError


class ProfileBase(ABC):
    """
    Abstract base class for all bundle format profiles.
    
    This class defines the contract that all profile implementations (e.g., PlainMarker,
    MarkdownFence) must adhere to, ensuring a consistent interface for the parser and writer.
    
    All concrete profile classes must:
    1. Inherit from ProfileBase
    2. Implement all abstract methods
    3. Override get_capabilities() if supporting advanced features
    """

    @property
    @abstractmethod
    def profile_name(self) -> str:
        """
        Return the unique, machine-readable identifier for the profile.
        
        The profile name is used for:
        - Configuration file references (e.g., bundle_profile: "plain_marker")
        - Profile selection in the UI
        - Logging and diagnostics
        
        Returns:
            Lowercase string identifier (e.g., 'plain_marker', 'md_fence', 'jsonl')
            
        Example:
            >>> profile = PlainMarkerProfile()
            >>> profile.profile_name
            'plain_marker'
        """
        pass

    @abstractmethod
    def detect_format(self, text: str) -> bool:
        """
        Quickly and efficiently detect if the given text appears to match this profile's format.
        
        This method should operate on a small snippet of text (e.g., the first 1-2KB)
        to avoid performance issues during auto-detection. It should use heuristics
        to identify format markers specific to the profile.
        
        Design Notes:
        - Must be fast - will be called sequentially during auto-detection
        - Should be conservative - false positives are worse than false negatives
        - Look for format-specific markers (e.g., "# FILE:" for plain_marker)
        - Consider checking first 10-20 lines only
        
        Args:
            text: A snippet of the bundle text (typically first 1-2KB or 20 lines)
            
        Returns:
            True if the text is likely in this profile's format, False otherwise
            
        Example:
            >>> profile = PlainMarkerProfile()
            >>> text = "# FILE: src/example.py\\ndef main(): pass"
            >>> profile.detect_format(text)
            True
        """
        pass

    @abstractmethod
    def parse_stream(self, text: str) -> BundleManifest:
        """
        Parse the raw bundle text into a BundleManifest object according to the profile's grammar.
        
        This is the core parsing method. It must:
        1. Identify file boundaries using profile-specific markers
        2. Extract file paths, content, and metadata
        3. Handle encoding declarations
        4. Decode base64 content for binary files
        5. Create BundleEntry objects with proper attributes
        6. Return a complete BundleManifest
        
        Error Handling:
        - Raise ProfileParseError for malformed bundle structure
        - Raise EncodingError for encoding issues
        - Include line numbers in error messages when possible
        - Provide clear, actionable error messages for users
        
        Args:
            text: The raw bundle file content as a string
            
        Returns:
            A BundleManifest object containing all extracted entries
            
        Raises:
            ProfileParseError: If the text is malformed and cannot be parsed
            EncodingError: If the content within the bundle has an invalid or unexpected encoding
            
        Example:
            >>> profile = PlainMarkerProfile()
            >>> text = "# FILE: test.py\\nprint('hello')"
            >>> manifest = profile.parse_stream(text)
            >>> manifest.get_file_count()
            1
        """
        pass

    @abstractmethod
    def format_manifest(self, manifest: BundleManifest) -> str:
        """
        Format a BundleManifest object into the profile's specific text representation.
        
        This is the core formatting method. It must:
        1. Iterate through all entries in the manifest
        2. Format each entry according to profile syntax
        3. Include metadata (encoding, EOL, checksums if supported)
        4. Ensure proper line endings
        5. Return a complete, parseable bundle string
        
        Round-Trip Guarantee:
        - The output of this method should be parseable by parse_stream()
        - parse_stream(format_manifest(manifest)) should produce equivalent manifest
        
        Error Handling:
        - Raise ProfileFormatError if manifest contains incompatible data
        - Example: Binary files in a profile that doesn't support them
        
        Args:
            manifest: The BundleManifest object to format
            
        Returns:
            The formatted bundle text as a string
            
        Raises:
            ProfileFormatError: If the manifest contains data that is incompatible with the
                                profile's capabilities (e.g., trying to format a binary file
                                in a profile that does not support it)
                                
        Example:
            >>> profile = PlainMarkerProfile()
            >>> manifest = BundleManifest(entries=[...], profile='plain_marker')
            >>> text = profile.format_manifest(manifest)
            >>> '# FILE:' in text
            True
        """
        pass

    def get_capabilities(self) -> Dict[str, bool]:
        """
        Declare the capabilities of this profile.
        
        This allows the application to make intelligent decisions, such as:
        - Warning users if they try to bundle binary files with an unsupported profile
        - Disabling checksum verification for profiles that don't support it
        - Filtering profile options based on bundle content
        
        Base Implementation:
        - Default assumes minimal capabilities (text-only, no checksums)
        - Subclasses should override to declare their actual capabilities
        
        Returns:
            A dictionary of supported features:
            - 'supports_binary': Can handle base64-encoded binary files
            - 'supports_checksums': Can store/verify SHA-256 checksums
            - 'supports_metadata': Can store encoding/EOL metadata
            - 'supports_compression': Can compress content (future)
            
        Example:
            >>> profile = MarkdownFenceProfile()
            >>> caps = profile.get_capabilities()
            >>> caps['supports_binary']
            True
            >>> caps['supports_checksums']
            True
        """
        return {
            'supports_binary': False,
            'supports_checksums': False,
            'supports_metadata': False,
        }
    
    def get_display_name(self) -> str:
        """
        Return a human-readable display name for the profile.
        
        This is used in the UI for profile selection dropdowns and labels.
        Base implementation converts profile_name to title case.
        Subclasses can override for custom display names.
        
        Returns:
            Human-readable profile name
            
        Example:
            >>> profile = PlainMarkerProfile()
            >>> profile.get_display_name()
            'Plain Marker'
        """
        return self.profile_name.replace('_', ' ').title()
    
    def validate_manifest(self, manifest: BundleManifest) -> None:
        """
        Validate that a manifest is compatible with this profile.
        
        This is called before format_manifest() to catch issues early.
        Base implementation checks basic compatibility.
        Subclasses can override for profile-specific validation.
        
        Args:
            manifest: The manifest to validate
            
        Raises:
            ProfileFormatError: If manifest is incompatible with profile
            
        Example:
            >>> profile = PlainMarkerProfile()
            >>> manifest = BundleManifest(entries=[binary_entry], profile='plain_marker')
            >>> profile.validate_manifest(manifest)  # May raise ProfileFormatError
        """
        capabilities = self.get_capabilities()
        
        # Check for binary files if not supported
        if not capabilities['supports_binary']:
            binary_files = [e.path for e in manifest.entries if e.is_binary]
            if binary_files:
                raise ProfileFormatError(
                    self.profile_name,
                    f"Profile does not support binary files. Found: {', '.join(binary_files[:3])}"
                )
        
        # Check for checksums if not supported
        if not capabilities['supports_checksums']:
            checksum_files = [e.path for e in manifest.entries if e.checksum is not None]
            if checksum_files:
                # This is just a warning - we can format without checksums
                pass


# ============================================================================
# LIFECYCLE STATUS: Proposed
# NEXT STEPS: Implement concrete profile classes (PlainMarker, MarkdownFence, JSONL)
# DEPENDENCIES: models.py, exceptions.py
# TESTS: Abstract class tests, concrete implementations will have full test suites
# SPECIFICATION: Defined by George in "Response to v2.1k3 Assessment" document
# ============================================================================
