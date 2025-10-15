# ============================================================================
# FILE: exceptions.py
# RELPATH: bundle_file_tool_v2/src/core/exceptions.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.0
# LIFECYCLE: Proposed
# DESCRIPTION: Exception hierarchy for Bundle File Tool v2.1
# ============================================================================

"""
Exception classes for Bundle File Tool v2.1.

This module defines a hierarchical exception structure for all error conditions
in the application, enabling precise error handling and meaningful user feedback.
"""


class BundleFileToolError(Exception):
    """Base exception for all Bundle File Tool errors."""
    pass


# ============================================================================
# Profile-Related Exceptions
# ============================================================================

class ProfileError(BundleFileToolError):
    """Base exception for profile-related errors."""
    pass


class ProfileParseError(ProfileError):
    """
    Raised when a profile cannot parse bundle text.
    
    Attributes:
        profile_name: Name of the profile that failed to parse
        reason: Human-readable explanation of the failure
        line_number: Optional line number where parsing failed
    """
    def __init__(self, profile_name: str, reason: str, line_number: int = None):
        self.profile_name = profile_name
        self.reason = reason
        self.line_number = line_number
        
        msg = f"Profile '{profile_name}' parse failed: {reason}"
        if line_number is not None:
            msg += f" (line {line_number})"
        super().__init__(msg)


class ProfileFormatError(ProfileError):
    """
    Raised when a profile cannot format a manifest.
    
    Attributes:
        profile_name: Name of the profile that failed to format
        reason: Human-readable explanation of the failure
    """
    def __init__(self, profile_name: str, reason: str):
        self.profile_name = profile_name
        self.reason = reason
        super().__init__(f"Profile '{profile_name}' format failed: {reason}")


class ProfileNotFoundError(ProfileError):
    """
    Raised when a requested profile does not exist.
    
    Attributes:
        profile_name: Name of the profile that was not found
        available_profiles: List of available profile names
    """
    def __init__(self, profile_name: str, available_profiles: list = None):
        self.profile_name = profile_name
        self.available_profiles = available_profiles or []
        
        msg = f"Profile '{profile_name}' not found"
        if self.available_profiles:
            msg += f". Available profiles: {', '.join(self.available_profiles)}"
        super().__init__(msg)


class ProfileDetectionError(ProfileError):
    """
    Raised when auto-detection cannot identify any suitable profile.
    
    Attributes:
        attempted_profiles: List of profile names that were attempted
    """
    def __init__(self, attempted_profiles: list = None):
        self.attempted_profiles = attempted_profiles or []
        msg = "Could not auto-detect bundle format"
        if self.attempted_profiles:
            msg += f". Attempted: {', '.join(self.attempted_profiles)}"
        super().__init__(msg)


# ============================================================================
# Validation-Related Exceptions
# ============================================================================

class ValidationError(BundleFileToolError):
    """Base exception for validation errors."""
    pass


class PathTraversalError(ValidationError):
    """
    Raised when an unsafe path is detected (e.g., path traversal attempt).
    
    Attributes:
        path: The unsafe path that was detected
        reason: Explanation of why the path is unsafe
    """
    def __init__(self, path: str, reason: str = "Path traversal detected"):
        self.path = path
        self.reason = reason
        super().__init__(f"Unsafe path '{path}': {reason}")


class FileSizeError(ValidationError):
    """
    Raised when a file exceeds the maximum allowed size.
    
    Attributes:
        path: Path of the oversized file
        size_mb: Actual file size in megabytes
        max_mb: Maximum allowed size in megabytes
    """
    def __init__(self, path: str, size_mb: float, max_mb: float):
        self.path = path
        self.size_mb = size_mb
        self.max_mb = max_mb
        super().__init__(
            f"File '{path}' size ({size_mb:.2f} MB) exceeds limit ({max_mb:.2f} MB)"
        )


class ChecksumMismatchError(ValidationError):
    """
    Raised when checksum verification fails.
    
    Attributes:
        path: Path of the file with mismatched checksum
        expected: Expected checksum value
        actual: Actual calculated checksum value
    """
    def __init__(self, path: str, expected: str, actual: str):
        self.path = path
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"Checksum mismatch for '{path}': expected {expected[:16]}..., "
            f"got {actual[:16]}..."
        )


class GlobFilterError(ValidationError):
    """
    Raised when a glob pattern is invalid or causes errors.
    
    Attributes:
        pattern: The problematic glob pattern
        reason: Explanation of the error
    """
    def __init__(self, pattern: str, reason: str):
        self.pattern = pattern
        self.reason = reason
        super().__init__(f"Invalid glob pattern '{pattern}': {reason}")


# ============================================================================
# Configuration-Related Exceptions
# ============================================================================

class ConfigError(BundleFileToolError):
    """Base exception for configuration-related errors."""
    pass


class ConfigLoadError(ConfigError):
    """
    Raised when configuration file cannot be loaded.
    
    Attributes:
        config_file: Path to the configuration file
        reason: Explanation of the failure
    """
    def __init__(self, config_file: str, reason: str):
        self.config_file = config_file
        self.reason = reason
        super().__init__(f"Failed to load config '{config_file}': {reason}")


class ConfigMigrationError(ConfigError):
    """
    Raised when configuration migration from old version fails.
    
    Attributes:
        old_version: Version being migrated from
        new_version: Version being migrated to
        reason: Explanation of the failure
    """
    def __init__(self, old_version: str, new_version: str, reason: str):
        self.old_version = old_version
        self.new_version = new_version
        self.reason = reason
        super().__init__(
            f"Config migration from {old_version} to {new_version} failed: {reason}"
        )


class ConfigValidationError(ConfigError):
    """
    Raised when configuration data fails validation.
    
    Attributes:
        key: Configuration key that failed validation
        value: The invalid value
        reason: Explanation of why validation failed
    """
    def __init__(self, key: str, value: any, reason: str):
        self.key = key
        self.value = value
        self.reason = reason
        super().__init__(f"Invalid config value for '{key}': {reason}")


# ============================================================================
# I/O-Related Exceptions
# ============================================================================

class BundleIOError(BundleFileToolError):
    """Base exception for I/O errors."""
    pass


class BundleReadError(BundleIOError):
    """
    Raised when a bundle file cannot be read.
    
    Attributes:
        path: Path to the bundle file
        reason: Explanation of the failure
    """
    def __init__(self, path: str, reason: str):
        self.path = path
        self.reason = reason
        super().__init__(f"Failed to read bundle '{path}': {reason}")


class BundleWriteError(BundleIOError):
    """
    Raised when a bundle or extracted file cannot be written.
    
    Attributes:
        path: Path where writing failed
        reason: Explanation of the failure
    """
    def __init__(self, path: str, reason: str):
        self.path = path
        self.reason = reason
        super().__init__(f"Failed to write '{path}': {reason}")


class EncodingError(BundleIOError):
    """
    Raised when file encoding issues are encountered.
    
    Attributes:
        path: Path to the file with encoding issues
        encoding: The encoding that failed
        reason: Explanation of the failure
    """
    def __init__(self, path: str, encoding: str, reason: str):
        self.path = path
        self.encoding = encoding
        self.reason = reason
        super().__init__(
            f"Encoding error for '{path}' (encoding: {encoding}): {reason}"
        )


# ============================================================================
# Operation-Related Exceptions
# ============================================================================

class OperationError(BundleFileToolError):
    """Base exception for operation errors."""
    pass


class OverwriteError(OperationError):
    """
    Raised when attempting to overwrite an existing file without permission.
    
    Attributes:
        path: Path to the file that would be overwritten
    """
    def __init__(self, path: str):
        self.path = path
        super().__init__(f"File '{path}' already exists and overwrite not permitted")


class DryRunError(OperationError):
    """
    Raised when a write operation is attempted during dry-run mode.
    
    Attributes:
        operation: Description of the attempted operation
    """
    def __init__(self, operation: str):
        self.operation = operation
        super().__init__(f"Cannot perform '{operation}' in dry-run mode")


# ============================================================================
# LIFECYCLE STATUS: Proposed
# NEXT STEPS: Integration with all core modules for error handling
# DEPENDENCIES: None (base exception definitions)
# TESTS: Unit tests for exception instantiation and message formatting
# ============================================================================
