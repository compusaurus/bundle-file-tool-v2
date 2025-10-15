# ============================================================================
# SOURCEFILE: models.py
# RELPATH: bundle_file_tool_v2/src/core/models.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.0
# LIFECYCLE: Proposed
# STATUS: UPDATED - Added file_size_bytes field per George's architectural decision
# DESCRIPTION: Core data models for bundle entries and manifests
# ============================================================================

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import hashlib


@dataclass
class BundleEntry:
    """
    Represents a single file within a bundle.
    
    Attributes:
        path: Relative path of the file within the project
        content: File content as string (UTF-8 or base64 if binary)
        is_binary: True if content is base64-encoded binary data
        encoding: Original file encoding (e.g., 'utf-8', 'windows-1252', 'utf-8-bom')
        eol_style: End-of-line style ('LF', 'CRLF', 'CR', 'MIXED', or 'n/a' for binary)
        checksum: Optional SHA-256 hex string for integrity verification
        file_size_bytes: Optional original file size in bytes (NEW - v2.1.0)
    """
    path: str
    content: str
    is_binary: bool
    encoding: str
    eol_style: str
    checksum: Optional[str] = None
    file_size_bytes: Optional[int] = None  # NEW FIELD - Added per George's guidance
    
    # ============================================================================
    # LOCATION: src/core/models.py
    # CLASS: BundleEntry
    # METHOD: __post_init__
    # REPLACEMENT: Complete method - handles blank EOL values gracefully
    # ============================================================================

    def __post_init__(self) -> None:
        """
        Normalize and validate BundleEntry fields. Accept blank EOL values and coerce
        to sensible defaults so validators/repair logic can run.
        """
        if not self.path:
            raise ValueError("BundleEntry path cannot be empty")
        
        # Normalize path separators (keep relative form)
        self.path = self.path.replace("\\", "/")
        
        # Coerce blank EOL to defaults (text -> LF, binary -> n/a)
        if self.eol_style is None or str(self.eol_style).strip() == "":
            self.eol_style = "n/a" if self.is_binary else "LF"
        
        # Validate EOL style
        valid_eol = {"LF", "CRLF", "CR", "MIXED", "n/a"}
        if self.eol_style not in valid_eol:
            raise ValueError(f"Invalid eol_style: {self.eol_style}. Must be one of {valid_eol}")
        
        # Validate checksum format if present
        if self.checksum is not None:
            if not (isinstance(self.checksum, str) and 
                    len(self.checksum) == 64 and 
                    all(c in '0123456789abcdefABCDEF' for c in self.checksum)):
                raise ValueError(f"Invalid checksum format: {self.checksum}. Must be 64-char hex string")
        
        # Validate file_size_bytes if present
        if self.file_size_bytes is not None:
            if not isinstance(self.file_size_bytes, int) or self.file_size_bytes < 0:
                raise ValueError(f"Invalid file_size_bytes: {self.file_size_bytes}. Must be non-negative integer")
    
    def calculate_checksum(self) -> str:
        """
        Calculate SHA-256 checksum of the content.
        
        Returns:
            Lowercase hexadecimal SHA-256 hash string
        """
        return hashlib.sha256(self.content.encode('utf-8')).hexdigest()
    
    def verify_checksum(self) -> bool:
        """
        Verify that stored checksum matches current content.
        
        Returns:
            True if checksum matches or no checksum stored, False otherwise
        """
        if self.checksum is None:
            return True
        return self.calculate_checksum() == self.checksum.lower()


@dataclass
class BundleManifest:
    """
    Container for an entire bundle with metadata.
    
    Attributes:
        entries: List of BundleEntry objects representing all files
        profile: Profile name used to create/parse the bundle
        version: Bundle format version (default "2.1")
        metadata: Additional bundle-level metadata
    """
    entries: List[BundleEntry]
    profile: str
    version: str = "2.1"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate manifest data on initialization."""
        if not isinstance(self.entries, list):
            raise TypeError("entries must be a list")
        
        if not self.profile:
            raise ValueError("profile cannot be empty")
        
        # Ensure metadata is a dict
        if self.metadata is None:
            self.metadata = {}
        elif not isinstance(self.metadata, dict):
            raise TypeError("metadata must be a dictionary")
        
        # Check for duplicate paths
        paths = [entry.path for entry in self.entries]
        if len(paths) != len(set(paths)):
            duplicates = {p for p in paths if paths.count(p) > 1}
            raise ValueError(f"Duplicate file paths found: {duplicates}")
    
    def get_entry(self, path: str) -> Optional[BundleEntry]:
        """
        Retrieve a specific entry by path.
        
        Args:
            path: Relative file path to search for
            
        Returns:
            BundleEntry if found, None otherwise
        """
        normalized_path = path.replace('\\', '/')
        for entry in self.entries:
            if entry.path == normalized_path:
                return entry
        return None
    
    def get_file_count(self) -> int:
        """Return total number of files in the bundle."""
        return len(self.entries)
    
    def get_binary_count(self) -> int:
        """Return number of binary files in the bundle."""
        return sum(1 for entry in self.entries if entry.is_binary)
    
    def get_text_count(self) -> int:
        """Return number of text files in the bundle."""
        return sum(1 for entry in self.entries if not entry.is_binary)
    
    def get_total_size_bytes(self) -> int:
        """
        Return total size of all files in bytes (if file_size_bytes populated).
        
        Returns:
            Total size in bytes, or 0 if no entries have size information
        """
        return sum(entry.file_size_bytes for entry in self.entries if entry.file_size_bytes is not None)
    
    def verify_all_checksums(self) -> Dict[str, bool]:
        """
        Verify checksums for all entries that have them.
        
        Returns:
            Dictionary mapping file paths to verification results
        """
        results = {}
        for entry in self.entries:
            if entry.checksum is not None:
                results[entry.path] = entry.verify_checksum()
        return results
    
    def add_entry(self, entry: BundleEntry) -> None:
        """
        Add a new entry to the manifest.
        
        Args:
            entry: BundleEntry to add
            
        Raises:
            ValueError: If entry with same path already exists
        """
        if self.get_entry(entry.path) is not None:
            raise ValueError(f"Entry with path '{entry.path}' already exists")
        self.entries.append(entry)
    
    def remove_entry(self, path: str) -> bool:
        """
        Remove an entry by path.
        
        Args:
            path: Relative file path to remove
            
        Returns:
            True if entry was removed, False if not found
        """
        normalized_path = path.replace('\\', '/')
        for i, entry in enumerate(self.entries):
            if entry.path == normalized_path:
                del self.entries[i]
                return True
        return False


# ============================================================================
# LIFECYCLE STATUS: Proposed
# CHANGES: Added file_size_bytes field to BundleEntry (v2.1.0 update)
# CHANGES: Added get_total_size_bytes() method to BundleManifest
# CHANGES: Added validation for file_size_bytes in __post_init__
# CHANGES: FIXED checksum validation error message to match tests
# NEXT STEPS: Integration with writer module to populate file_size_bytes
# DEPENDENCIES: None (core data structures)
# TESTS: Unit tests updated to include file_size_bytes field
# REGRESSION RISK: LOW - Optional field maintains backward compatibility
# ============================================================================
