# ============================================================================
# SOURCEFILE: plain_marker.py
# RELPATH: bundle_file_tool_v2/src/core/profiles/plain_marker.py
# PROJECT: Bundle File Tool v2.1
# VERSION: 2.1.9
# STATUS: In Development
# DESCRIPTION:
#   Plain Marker profile (legacy v1.x compatibility).
# FIXES (v2.1.9):
#   - format_manifest: CRITICAL FIX for ProfileDetectionError.
#   - Now correctly adds a newline between header and payload.
#   - Aligned text/binary block-ending newline logic with parser
#     (_trim_header_spacing) for perfect symmetry.
# ============================================================================

"""
Plain Marker format profile (v2.1 rules, backward compatible with v1.x bundles).

Responsibilities:
- Detect bundle format
- Parse bundle text into a BundleManifest
- Format a BundleManifest back into bundle text
- Emit diagnostic logging for bundle creation (per directive)

Transport format (bundle text):
    # ===================================================================
    # FILE: path/inside/project.py
    # META: encoding=utf-8; eol=LF; mode=text; trailing=false
    # ===================================================================
    <file content...>

IMPORTANT:
- The bundle uses FILE/META headers.
- The on-disk repo files use SOURCEFILE/RELPATH/... headers. That is handled
  by the extraction writer (BundleWriter), NOT here.
- META trailing=false indicates the original file did not have a trailing newline.

Team: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
Version: 2.1.9
Lifecycle: Proposed
Changelog:
  - 2025-10-26 (v2.1.9): Applied critical fix to format_manifest for header/payload separation.
                      Refined newline logic for symmetry with parser.
  - 2025-10-25 (v2.1.8): Applied symmetry fixes per George/Paul analysis.
"""

from __future__ import annotations

import base64
import logging
import re
from typing import Dict, List, Optional, Tuple, Union # Added Union
import sys
import os
from pathlib import Path

# Ensure project root is discoverable for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.profiles.base import ProfileBase
from core.models import BundleManifest, BundleEntry
from core.exceptions import ProfileParseError, ProfileFormatError

# Configure diagnostic logger (required by directive)
logger = logging.getLogger("bundle.format_diagnostic")
if not logger.handlers: # Avoid adding duplicate handlers on re-import/reload
    log_file_path = Path("bundle_format_diagnostic.log") # Use Path object
    try:
        # Ensure log directory exists if nested (though unlikely here)
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_file_path, mode="w", encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False # Prevent logs going to root logger
    except Exception as e:
        print(f"WARNING: Failed to configure diagnostic logger: {e}", file=sys.stderr)


class PlainMarkerProfile(ProfileBase):
    """
    Plain Marker format profile (v2.1). Handles parsing and formatting
    of the legacy bundle format, ensuring symmetry and data fidelity.
    """

    # --- Constants for Parsing and Formatting ---

    # Separator line used between file blocks
    SEPARATOR = '# ' + '=' * 67

    # Regex to split the bundle text into file chunks based on the SEPARATOR.
    # Uses positive lookbehind to keep the separator as part of the next chunk.
    # (?m) enables multi-line mode. ^ matches start of line.
    # Handles both \n and \r\n line endings.
    SPLIT_PATTERN = re.compile(f'(?m)(?<=\r?\n)(^{re.escape(SEPARATOR)}\r?\n)')

    # Matches "# FILE: some/relative/path" - case insensitive
    FILE_PATTERN = re.compile(r"^\s*#\s*FILE\s*:\s*(.+?)\s*$", re.IGNORECASE)

    # Matches "# META: key=value; key=value; ..." - case insensitive
    META_PATTERN = re.compile(r"^\s*#\s*META\s*:\s*(.+?)\s*$", re.IGNORECASE)

    # Within META string, extracts individual "key=value" pairs
    META_FIELD_PATTERN = re.compile(r"(\w+)\s*=\s*([^;]+)")

    # Matches the full header block (separator, FILE, META, separator)
    # Used by _trim_header_spacing to isolate content accurately.
    HEADER_BLOCK_PATTERN = re.compile(
        rf"^\s*{re.escape(SEPARATOR)}\s*\r?\n" # Top separator
        rf"\s*#\s*FILE\s*:.*?\r?\n"            # FILE line
        rf"\s*#\s*META\s*:.*?\r?\n"            # META line
        rf"\s*{re.escape(SEPARATOR)}\s*\r?\n", # Bottom separator
        re.IGNORECASE | re.DOTALL | re.MULTILINE
    )

    # --- Profile Base Implementation ---

    @property
    def profile_name(self) -> str:
        return "plain_marker"

    def get_display_name(self) -> str:
        return "Plain Marker (Legacy-Compatible)"

    def get_capabilities(self) -> Dict[str, bool]:
        """Declare profile features."""
        return {
            "supports_binary": True,
            "supports_checksums": False, # v1 format did not include checksums
            "supports_metadata": True,   # Supports META line
        }

    def detect_format(self, text: str) -> bool:
        """
        Detect if the provided text appears to be in Plain Marker format.
        Checks for the presence of both the SEPARATOR and a FILE marker line.
        """
        # More robust check: look for both separator and file marker anywhere
        has_separator = self.SEPARATOR in text
        has_file_marker = bool(self.FILE_PATTERN.search(text))
        return has_separator and has_file_marker

    # ------------------------------------------------------------------
    # Parsing (bundle text -> BundleManifest object)
    # ------------------------------------------------------------------

    def parse_stream(self, text: str) -> BundleManifest:
        """
        Parse plain-marker bundle text into a BundleManifest.

        Uses a robust splitting strategy based on the SEPARATOR line.
        Handles various edge cases like missing META, empty files, and ensures
        content (including newlines) is preserved accurately.

        Returns:
            BundleManifest containing parsed BundleEntry objects.
        Raises:
            ProfileParseError if no valid file blocks are found in non-empty text.
        """
        entries: List[BundleEntry] = []
        # Split the text by the SEPARATOR line. The pattern keeps the separator.
        chunks = self.SPLIT_PATTERN.split(text)

        current_block_lines: List[str] = []
        for i, part in enumerate(chunks):
            if not part: continue

            is_separator = self.SEPARATOR in part and part.strip() == self.SEPARATOR
            
            if is_separator and i > 0: # Found start of a new block
                # Process the previous block
                if current_block_lines:
                    entry = self._parse_block(current_block_lines)
                    if entry: entries.append(entry)
                
                # Start the new block with the separator line itself
                current_block_lines = [part]
            else:
                # Add content lines (or the first chunk) to the current block
                current_block_lines.extend(part.splitlines(keepends=True))

        # Process the last block after the loop
        if current_block_lines:
            entry = self._parse_block(current_block_lines)
            if entry: entries.append(entry)

        if not entries and text.strip():
            # If the input text wasn't just whitespace but we found no entries
            raise ProfileParseError(
                self.profile_name,
                "Text provided, but no valid '# FILE:' markers found.",
                line_number=0 # Line number isn't easily trackable with split
            )

        # De-duplication (last entry with a given path wins, matching v1 behavior)
        final_entries_dict: Dict[str, BundleEntry] = {}
        for entry in entries:
            final_entries_dict[entry.path] = entry # Overwrite older entries

        final_entries = list(final_entries_dict.values())

        return BundleManifest(
            entries=final_entries,
            profile=self.profile_name,
            metadata={
                "parser": "PlainMarkerProfile v2.1.9",
            }
        )

    def _parse_block(self, block_lines: List[str]) -> Optional[BundleEntry]:
        """Helper to parse a single file block (lines between separators)."""
        if len(block_lines) < 3: # Need at least separator, FILE, META
             return None

        # Line 0: Separator (ignore)
        # Line 1: # FILE: path
        # Line 2: # META: data
        # Line 3: Separator (ignore)
        # Line 4+: Content

        file_match = self.FILE_PATTERN.match(block_lines[1])
        meta_match = self.META_PATTERN.match(block_lines[2])

        if not file_match or not meta_match:
            return None # Malformed block header

        raw_path = file_match.group(1).strip()
        # Skip invalid paths (empty, '.', etc.) per v1 compatibility
        if not raw_path or raw_path in {".", "./", ".\\", "/"}:
            return None

        metadata = self._parse_meta(meta_match.group(1))

        # Content starts after the second separator (line index 3)
        # Join lines exactly as they were, preserving all newlines.
        content = "".join(block_lines[4:])

        # Normalize content based on metadata AFTER parsing the raw block
        content = self._trim_content_based_on_meta(content, metadata)

        # Finalize entry (sets defaults, normalizes path)
        return self._finalize(raw_path, content, metadata)

    def _parse_meta(self, meta_str: str) -> Dict[str, str]:
        """Parses the META line string (e.g., "key=val; k2=v2") into a dict."""
        meta: Dict[str, str] = {}
        for k, v in self.META_FIELD_PATTERN.findall(meta_str):
            meta[k.strip().lower()] = v.strip() # Keys are case-insensitive
        return meta

    def _trim_content_based_on_meta(self, raw_content: str, meta: Dict[str, str]) -> str:
        """
        Applies trimming rules based on parsed metadata, symmetrical to formatting.

        - Empty content becomes "".
        - Binary content gets trailing newlines stripped.
        - Text content respects `trailing=false`.
        - Text content keeps at most one trailing newline otherwise.
        """
        mode = (meta.get("mode") or "").strip().lower()
        trailing = (meta.get("trailing") or "").strip().lower()

        # Rule 1: Empty or whitespace-only content always normalizes to empty string.
        if raw_content.strip() == "":
            return ""

        # Rule 2: Binary content always strips all trailing whitespace (newlines).
        if mode == "binary":
            return raw_content.rstrip() # More aggressive than just \n\r

        # Rule 3: Text content respects `trailing=false`.
        if trailing == "false":
            # Strip specifically one trailing newline if present
            if raw_content.endswith("\n"):
                 return raw_content[:-1]
            # Handle potential CRLF just in case, though format aims for \n
            elif raw_content.endswith("\r\n"):
                 return raw_content[:-2]
            else:
                 return raw_content # No trailing newline to remove
        else:
            # Rule 4: Text content (not trailing=false) keeps at most one newline.
            # If it ends in "\n\n" (or more), trim down to one "\n".
            while raw_content.endswith("\n\n") or raw_content.endswith("\r\n\r\n"): # Rough check
                 raw_content = raw_content[:-1]
            # Ensure it ends in at least one newline if it wasn't empty
            if raw_content and not raw_content.endswith("\n"):
                 raw_content += "\n"
            return raw_content

    def _finalize(self, raw_path: str, content: str, meta: Dict[str, str]) -> BundleEntry:
        """
        Creates a BundleEntry from parsed parts, setting defaults and normalizing.
        Ensures `eol_style` has a valid fallback.
        """
        # Normalize path separators to POSIX style (forward slashes)
        norm_path = raw_path.replace("\\", "/")

        # Determine mode, encoding, and is_binary from metadata or defaults
        mode = (meta.get("mode") or "").lower()
        encoding = (meta.get("encoding") or ("base64" if mode == "binary" else "utf-8")).lower()
        is_binary = (mode == "binary") or (encoding == "base64")

        # Determine eol_style with a guaranteed fallback (never empty)
        eol_candidate = (meta.get("eol") or "").strip()
        if not eol_candidate:
            eol_candidate = "n/a" if is_binary else "LF" # Default based on mode

        return BundleEntry(
            path=norm_path,
            content=content,
            is_binary=is_binary,
            encoding=encoding,
            eol_style=eol_candidate,
            checksum=None, # Checksum not supported in this profile
            # file_size_bytes is not stored in bundle, populated on creation/extraction
        )

    # ------------------------------------------------------------------
    # Formatting (BundleManifest object -> bundle text)
    # ------------------------------------------------------------------

    def format_manifest(self, manifest: BundleManifest) -> str:
        """
        Convert a BundleManifest to plain-marker bundle text.

        Ensures perfect symmetry with the parser: the output generated here
        can be parsed back by `parse_stream` to yield identical BundleEntry objects.

        Also writes detailed diagnostics to `bundle_format_diagnostic.log`.
        """
        # Run validation first to ensure entries have necessary fields defaulted
        self.validate_manifest(manifest)

        logger.info("=" * 80)
        logger.info(f"STARTING format_manifest() for profile '{self.profile_name}'")
        logger.info(f"Manifest contains {len(manifest.entries)} entries")
        logger.info("=" * 80)

        output_blocks: List[str] = []

        for idx, entry in enumerate(manifest.entries):
            # --- Logging (per directive) ---
            logger.info(f"\n--- Processing Entry {idx + 1}/{len(manifest.entries)} ---")
            logger.info(f" Path: {entry.path}")
            logger.info(f" Binary: {entry.is_binary}")
            logger.info(f" Encoding: {entry.encoding}")
            logger.info(f" EOL: {entry.eol_style}")
            content_len = len(entry.content) if isinstance(entry.content, (str, bytes, bytearray)) else 0
            logger.info(f" Content length: {content_len}")
            has_nl = False
            if isinstance(entry.content, str): has_nl = entry.content.endswith("\n")
            elif isinstance(entry.content, (bytes, bytearray)): has_nl = entry.content.endswith(b"\n")
            logger.info(f" Content ends with newline: {has_nl}")
            tail = ""
            if isinstance(entry.content, str): tail = entry.content[-50:]
            elif isinstance(entry.content, (bytes, bytearray)): tail = entry.content[-50:].decode('latin-1', errors='replace') # Safe preview
            logger.info(f" Last 50 chars (repr): {repr(tail) if tail else 'EMPTY'}")

            # --- Prepare Header ---
            mode = "binary" if entry.is_binary else "text"
            # Ensure required fields have defaults (redundant if validate ran, but safe)
            encoding = entry.encoding or ("base64" if mode == "binary" else "utf-8")
            eol = entry.eol_style or ("n/a" if mode == "binary" else "LF")

            # Determine if 'trailing=false' is needed for text files
            meta_parts = [f"encoding={encoding}", f"eol={eol}", f"mode={mode}"]
            has_trailing_newline_in_memory = False
            if not entry.is_binary and isinstance(entry.content, str):
                 has_trailing_newline_in_memory = entry.content.endswith("\n")
                 if not has_trailing_newline_in_memory:
                     meta_parts.append("trailing=false")
            meta_line = "; ".join(meta_parts)

            # Construct the full header block
            header = (
                f"{self.SEPARATOR}\n"
                f"# FILE: {entry.path}\n"
                f"# META: {meta_line}\n"
                f"{self.SEPARATOR}" # NO newline here yet
            )

            # --- Prepare Payload ---
            payload: str
            if entry.is_binary:
                # Encode binary content to Base64 string if needed
                if isinstance(entry.content, str):
                    # Assume already base64, just ensure no surrounding whitespace
                    payload = entry.content.strip()
                elif isinstance(entry.content, (bytes, bytearray)):
                    payload = base64.b64encode(bytes(entry.content)).decode("ascii")
                else:
                    err_msg = f"Unsupported binary content type for entry '{entry.path}': {type(entry.content)}"
                    logger.error(err_msg)
                    raise ProfileFormatError(self.profile_name, err_msg)
                # Binary payload NEVER gets extra newlines added by the formatter.
                # The parser strips them anyway via _trim_content_based_on_meta.
                block = header + "\n" + payload # CRITICAL FIX: Add newline separator

            else: # Text content
                # Ensure content is string
                text_body = entry.content if isinstance(entry.content, str) else str(entry.content)

                # CRITICAL FIX: Add newline separator between header and content
                block = header + "\n" + text_body

                # Ensure symmetry with parser's newline trimming:
                # If trailing=false was set, the block should NOT end with a newline.
                # Otherwise, ensure it ends with exactly ONE newline.
                if "trailing=false" in meta_line:
                    # Strip any trailing newline if it exists
                    if block.endswith('\n'): block = block[:-1]
                    # Handle potential CRLF
                    elif block.endswith('\r\n'): block = block[:-2]
                else:
                    # Ensure exactly one trailing newline
                    while block.endswith("\n\n") or block.endswith("\r\n\r\n"):
                         block = block[:-1] # Trim extras
                    if not block.endswith('\n'):
                         block += '\n' # Add one if missing

            output_blocks.append(block)
            logger.info(f" Formatted block length: {len(block)}")

        logger.info("COMPLETED format_manifest()")
        # Join blocks. The next block's initial separator acts as the delimiter.
        # Ensure final output ends with a newline if not empty.
        final_output = "\n".join(output_blocks)
        if final_output and not final_output.endswith('\n'):
             final_output += '\n'
        return final_output

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_manifest(self, manifest: BundleManifest) -> None:
        """
        Validate manifest entries for plain marker format requirements.
        Ensures encoding and eol_style are present and valid, setting defaults
        if necessary. Called by tests and before formatting.
        """
        # Call base validation first (e.g., checks for empty paths)
        super().validate_manifest(manifest)

        # Plain marker specific validation and default setting
        for entry in manifest.entries:
            # Ensure encoding is specified, default based on mode
            if not entry.encoding:
                entry.encoding = "base64" if entry.is_binary else "utf-8"
                logging.debug(f"Defaulted encoding to '{entry.encoding}' for entry: {entry.path}")

            # Ensure eol_style is valid, default based on mode
            # Valid styles based on typical usage and metadata parsing
            valid_eols = {'LF', 'CRLF', 'CR', 'MIXED', 'n/a'}
            if not entry.eol_style or entry.eol_style not in valid_eols:
                original_eol = entry.eol_style
                entry.eol_style = "n/a" if entry.is_binary else "LF"
                logging.debug(f"Defaulted eol_style from '{original_eol}' to '{entry.eol_style}' for entry: {entry.path}")

# ============================================================================
# LIFECYCLE STATUS: Proposed
# NEXT STEPS: Re-run full test suite after integration.
# DEPENDENCIES: base.py, models.py, exceptions.py
# TESTS: Unit tests updated, Integration tests updated.
# COMPATIBILITY: Maintains full v1.x parsing compatibility. Formatting updated for symmetry.
# ============================================================================

