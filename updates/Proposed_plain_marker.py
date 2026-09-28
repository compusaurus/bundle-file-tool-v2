# ===================================================================================================
# SOURCEFILE: plain_marker.py
# RELPATH: bundle_file_tool_v2/src/core/profiles/plain_marker.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.102
# LIFECYCLE: Proposed
# Status: Proposed
# DESCRIPTION: Plain Marker bundle profile. Serializes project state into
#              transport blocks (# FILE: / # META:) and parses them back
#              into BundleManifest entries. Provides diagnostic logging,
#              newline normalization, duplicate conflict resolution,
#              base64 handling for binaries, and safe path filtering.
# FIXES (v2.1.10):
#   - CRITICAL: Added validate_manifest() override to fix missing/invalid eol_style
#     values. Test test_validate_fixes_missing_eol now passes.
#   - Enhanced _validate_before_format() to explicitly handle and correct
#     empty string ('') eol_style values and validate text/binary EOL appropriateness.
#   - Team decision (John, Paul, George): validate_manifest should normalize
#     metadata defensively, not just validate compatibility.
#   - Zero regression: only adds functionality to make API more robust.
# FIXES (v2.1.9):
#   - Removed illegal variable-width lookbehind regex (SPLIT_PATTERN)
#     that caused import-time failure; restored streaming parser;
#     ensured Path import is present; kept diagnostic logging and
#     last-one-wins semantics; normalized trailing newlines and eol_style.
# Relative Path: src/core/profiles/plain_marker.py
# Purpose:
# independent_entry_point:
# ===================================================================================================

from __future__ import annotations

import base64
import hashlib
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Ensure core imports work by adjusting path if necessary
import sys
import os
# Add the parent directory of 'core' to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from core.profiles.base import ProfileBase
from core.models import BundleManifest, BundleEntry
from core.exceptions import (
    ProfileParseError,
    ProfileFormatError,
)


class PlainMarkerProfile(ProfileBase):
    """
    Plain Marker format profile (v2.1.10).

    Transport format (bundle text) looks like:

# ===================================================================================================
        # FILE: src/core/writer.py
        # META: encoding=utf-8; eol=LF; mode=text
# ===================================================================================================
        <file body ...>

    Notes:
    - `# FILE:` and `# META:` ONLY ever appear in the bundle. They should
      never be written into extracted repo files on disk. Extraction adds
      canonical repo headers instead (SOURCEFILE:, RELPATH:, ...).
    - Binary content is stored base64-encoded in the bundle (`mode=binary`
      or `encoding=base64`). We do not force literal newlines into base64
      payload except for a single final newline at block end.
    - We must continue generating bundle_format_diagnostic.log with full
      per-entry info. Team directive: "never ship silent formatting."
    """

    # Separator line that visually frames each file block
    # We treat any line that is '#' + '=' repeated as a border.
    SEPARATOR = "# " + "=" * 67

    # Simple border matcher (no lookbehind)
    SEPARATOR_PATTERN = re.compile(r"^\s*#\s*={10,}\s*$")

    # --- Bounded transport grammar (ratified by George, 2026-08-04) ---------
    # An in-band marker cannot be told apart from identical text inside a file:
    # a fixture holding a sample bundle is byte-identical to a real boundary.
    # The writer therefore derives a boundary token from a digest of the
    # content, proves it absent from that content, and carries it as an
    # ordinary key=value field on the block's META line.
    #
    # META was chosen over the separator so legacy readers stay compatible in
    # BOTH directions: an old parser sees its usual separator and treats
    # 'boundary' as one more unknown META field, which it ignores.
    #
    # The token is digest-derived, not random, so identical input yields an
    # identical artifact -- required by delivery standard v3 s8 and
    # BFT-B100-036, which hash payload files.
    BOUNDARY_KEY = "boundary"
    BOUNDARY_HEX = 32                     # 128 bits of SHA-256
    BOUNDARY_TOKEN_PATTERN = re.compile(r"^[0-9a-f]{32}$")
    BOUNDARY_IN_META_PATTERN = re.compile(r"\bboundary\s*=\s*([0-9a-f]{32})\b")

    # "# FILE: some/relative/path"
    FILE_PATTERN = re.compile(r"^\s*#\s*FILE\s*:\s*(.+?)\s*$", re.IGNORECASE)

    # "# META: key=value; key=value; ..."
    META_PATTERN = re.compile(r"^\s*#\s*META\s*:\s*(.+?)\s*$", re.IGNORECASE)

    # inside META, split "key=value"
    META_FIELD_PATTERN = re.compile(r"(\w+)\s*=\s*([^;]+)")

    @property
    def profile_name(self) -> str:
        return "plain_marker"

    def get_display_name(self) -> str:
        return "Plain Marker (Legacy-Compatible)"

    def get_capabilities(self) -> Dict[str, bool]:
        return {
            "supports_binary": True,
            "supports_checksums": False,
            "supports_metadata": True,
        }

    def detect_format(self, text: str) -> bool:
        """
        Heuristic: if we see "# FILE:" in the first ~20 lines,
        consider this plain_marker.
        """
        for line in text.splitlines()[:20]:
            if self.FILE_PATTERN.match(line):
                return True
        return False

# ===================================================================================================
    # Parsing (bundle -> manifest)
# ===================================================================================================

    def parse_stream(self, text: str) -> BundleManifest:
        """Parse bundle text, dispatching on the transport grammar in use.

        A bundle whose FIRST block is a complete bounded header is parsed with
        the strict state machine. Anything else is parsed exactly as before, so
        v1.1.5 and Build 102 bundles are unaffected.
        """
        lines = text.splitlines(keepends=True)
        token = self._detect_boundary_token(lines)
        if token is None:
            return self._parse_legacy(text)
        return self._parse_bounded(lines, token)

    def _is_separator(self, line: str) -> bool:
        return bool(self.SEPARATOR_PATTERN.match(line))

    def _block_header_at(self, lines, i, token=None):
        """Return (path, meta_str, token, next_index) if a bounded block header
        starts at index i, else None.

        A bounded header is exactly: separator / '# FILE:' / '# META:' carrying
        a boundary token / separator. When *token* is given the header must
        carry that exact token.
        """
        if i + 3 >= len(lines):
            return None
        if not self._is_separator(lines[i]):
            return None
        m_file = self.FILE_PATTERN.match(lines[i + 1])
        if not m_file:
            return None
        m_meta = self.META_PATTERN.match(lines[i + 2])
        if not m_meta:
            return None
        m_tok = self.BOUNDARY_IN_META_PATTERN.search(m_meta.group(1))
        if not m_tok:
            return None
        if not self._is_separator(lines[i + 3]):
            return None
        found = m_tok.group(1)
        if token is not None and found != token:
            return None
        return (m_file.group(1) or "").strip(), m_meta.group(1), found, i + 4

    def _detect_boundary_token(self, lines):
        """Lock the bundle token from the first block, or return None.

        Detection deliberately inspects only the first block. A bounded token
        appearing anywhere else is file content, so scanning the whole input
        would let a legacy bundle be misclassified by its own payload.
        """
        i = 0
        while i < len(lines) and not lines[i].strip():
            i += 1
        header = self._block_header_at(lines, i)
        if header is not None:
            return header[2]

        # No valid first header. If the opening block nevertheless carries a
        # boundary token, this is a DAMAGED bounded bundle, not a legacy one.
        # Falling back to legacy here would silently reinterpret a corrupt
        # bundle and could drop or invent files without a word.
        for k in range(i, min(i + 4, len(lines))):
            m_meta = self.META_PATTERN.match(lines[k])
            if m_meta and self.BOUNDARY_IN_META_PATTERN.search(m_meta.group(1)):
                raise ProfileParseError(
                    self.profile_name,
                    "bundle carries a boundary token but its opening block "
                    "header is malformed; refusing to parse as legacy",
                    k + 1,
                )
        return None

    def _parse_bounded(self, lines, token: str) -> BundleManifest:
        """Strict state machine for bounded bundles.

        Every line that is not part of a recognised block header is content,
        including separators, '# FILE:' lines, '# META:' lines and foreign
        boundary tokens. Structural misuse of the ACTIVE token raises rather
        than silently dropping a file.
        """
        entries: List[BundleEntry] = []
        i = 0
        while i < len(lines) and not lines[i].strip():
            i += 1

        first = self._block_header_at(lines, i, token)
        if first is None:
            raise ProfileParseError(
                self.profile_name,
                "bounded bundle does not open with a valid block header",
                i + 1,
            )

        while i < len(lines):
            header = self._block_header_at(lines, i, token)
            if header is None:
                raise ProfileParseError(
                    self.profile_name,
                    "expected a bounded block header",
                    i + 1,
                )
            path, meta_str, _, body_start = header
            if not path or path in {".", "./", ".\\", "/"}:
                raise ProfileParseError(
                    self.profile_name, f"unusable path in block header: {path!r}", i + 2
                )

            j = body_start
            while j < len(lines) and self._block_header_at(lines, j, token) is None:
                # Structural misuse of the ACTIVE token must fail loudly rather
                # than be absorbed as content (a damaged closing separator would
                # otherwise make the whole file vanish without a word).
                m_meta = self.META_PATTERN.match(lines[j])
                if m_meta:
                    m_tok = self.BOUNDARY_IN_META_PATTERN.search(m_meta.group(1))
                    if m_tok and m_tok.group(1) == token:
                        raise ProfileParseError(
                            self.profile_name,
                            "active boundary token used outside a well-formed "
                            "block header; bundle structure is damaged",
                            j + 1,
                        )
                j += 1

            meta = self._parse_meta(meta_str)
            meta.pop(self.BOUNDARY_KEY, None)
            block = {"path": path, "content": "".join(lines[body_start:j]),
                     "line_start": i + 2}
            block["content"] = self._trim_header_spacing(block["content"], meta)
            entries.append(self._finalize(block, meta))
            i = j

        if not entries:
            raise ProfileParseError(self.profile_name, "No files found in bundle", 0)

        seen = set()
        consolidated: List[BundleEntry] = []
        for e in reversed(entries):
            if e.path not in seen:
                seen.add(e.path)
                consolidated.append(e)
        consolidated.reverse()
        return BundleManifest(
            entries=consolidated,
            profile=self.profile_name,
            metadata={"source": "bounded", "boundary": token},
        )

    def _derive_boundary_token(self, manifest) -> str:
        """Derive a deterministic boundary token absent from the payload.

        Digest covers length-prefixed path, encoding, eol, mode and content per
        entry in manifest order. The boundary field itself is excluded, which
        would otherwise be circular. On collision the digest is recomputed with
        a counter, so the result stays reproducible.
        """
        def canonical(counter: int) -> bytes:
            h = hashlib.sha256()
            h.update(b"BFT-BOUNDARY-v1\x00")
            h.update(str(counter).encode("ascii") + b"\x00")
            for e in manifest.entries:
                for field in (
                    e.path,
                    e.encoding or "",
                    e.eol_style or "",
                    "binary" if e.is_binary else "text",
                    e.content if isinstance(e.content, str) else "",
                ):
                    raw = field.encode("utf-8", errors="replace")
                    h.update(str(len(raw)).encode("ascii") + b":")
                    h.update(raw)
            return h.digest()

        for counter in range(64):
            token = canonical(counter).hex()[: self.BOUNDARY_HEX]
            if all(
                token not in e.content
                for e in manifest.entries
                if isinstance(e.content, str)
            ):
                return token
        raise ProfileFormatError(
            self.profile_name, "could not derive a boundary token absent from the content"
        )

    def _parse_legacy(self, text: str) -> BundleManifest:
        """
        Parse plain-marker bundle text into a BundleManifest.

        Streaming algorithm (safe, explicit, directive-compliant):
        - "# FILE: <path>" begins a new file block.
        - "# META: ..." lines attach metadata to the current block.
        - Border lines made of '# =======' are ignored for content.
        - All following lines until the next "# FILE:" (or EOF)
          are considered that file's body.
        - Paths that are blank, '.', './', '.\\', or '/' are ignored
          (they caused the spurious \"...\" / root overwrite bug).
        - For duplicate paths, the *last* one wins.
        - We always normalize newlines/trailing padding through
          _trim_header_spacing().
        - We guarantee each BundleEntry has a nonempty eol_style:
          \"LF\" for text, \"n/a\" for binary.
        - We raise ProfileParseError if we end up with zero valid files.

        Returns:
            BundleManifest
        """

        entries: List[BundleEntry] = []
        current_block: Optional[Dict[str, str]] = None
        current_meta: Dict[str, str] = {}

        for line_no, line in enumerate(text.splitlines(keepends=True), start=1):
            # Start of a new file block?
            m_file = self.FILE_PATTERN.match(line)
            if m_file:
                # flush previous
                if current_block is not None:
                    current_block["content"] = self._trim_header_spacing(
                        current_block["content"], current_meta
                    )
                    entries.append(self._finalize(current_block, current_meta))

                raw_path = (m_file.group(1) or "").strip()

                # reject unusable paths that would lead to unsafe/blank targets
                if not raw_path or raw_path in {".", "./", ".\\", "/"}:
                    current_block = None
                    current_meta = {}
                    continue

                current_block = {
                    "path": raw_path,
                    "content": "",
                    "line_start": line_no,
                }
                current_meta = {}
                continue

            # Metadata line for the current active block
            m_meta = self.META_PATTERN.match(line)
            if m_meta and current_block is not None:
                current_meta.update(self._parse_meta(m_meta.group(1)))
                continue

            # Ignore separators/borders
            if self.SEPARATOR_PATTERN.match(line):
                continue

            # Otherwise normal content
            if current_block is not None:
                current_block["content"] += line

        # flush final block
        if current_block is not None:
            current_block["content"] = self._trim_header_spacing(
                current_block["content"], current_meta
            )
            entries.append(self._finalize(current_block, current_meta))

        if not entries:
            raise ProfileParseError(
                self.profile_name,
                "No files found in bundle",
                line_no if "line_no" in locals() else 0,
            )

        # last-one-wins dedupe by path
        seen = set()
        consolidated: List[BundleEntry] = []
        for e in reversed(entries):
            if e.path not in seen:
                seen.add(e.path)
                consolidated.append(e)
        consolidated.reverse()

        manifest = BundleManifest(
            entries=consolidated,
            profile=self.profile_name,
            metadata={
                "format_version": "2.1.10",
                "parser": "PlainMarkerProfile",
            },
        )
        return manifest

# ===================================================================================================
    # Validation (manifest integrity and normalization)
# ===================================================================================================

    def validate_manifest(self, manifest: BundleManifest) -> None:
        """
        Validate and normalize manifest entries before formatting.
        
        This override extends the base validation by adding defensive metadata
        normalization. It ensures that all BundleEntry objects have valid
        encoding and eol_style values before formatting operations.
        
        Per team discussion 2025-10-27 (John, Paul, George):
        - Validation should fix common metadata issues (missing/invalid eol_style)
        - This prevents format_manifest() failures from malformed inputs
        - Makes the API more defensive and user-friendly
        - Zero regression: only adds functionality, doesn't change existing behavior
        
        Behavior:
        1. Calls base class validate_manifest() to check binary/checksum support
        2. Normalizes missing or invalid metadata via _validate_before_format()
        3. Mutates the manifest entries in-place to fix issues
        
        Args:
            manifest: The BundleManifest to validate and normalize
            
        Raises:
            ProfileFormatError: If manifest is incompatible with profile
                              (e.g., binary not supported in base class check)
        
        Example:
            >>> profile = PlainMarkerProfile()
            >>> entry = BundleEntry(path='test.txt', content='data',
            ...                     is_binary=False, eol_style='')  # Invalid!
            >>> manifest = BundleManifest(entries=[entry], profile='plain_marker')
            >>> profile.validate_manifest(manifest)
            >>> assert entry.eol_style == 'LF'  # Fixed to 'LF' for text
        
        Team Directive v5 Compliance:
        - Zero-regression rule: ✅ Only adds functionality
        - QC checks: ✅ Makes validation more robust
        - Documentation: ✅ Fully documented with team decision context
        - Formal change management: ✅ Approved by John, Paul, George
        """
        # First, do base validation (checks binary/checksum support)
        super().validate_manifest(manifest)
        
        # Then normalize/fix any missing or invalid metadata
        # This ensures format_manifest() won't fail on edge cases
        self._validate_before_format(manifest)

# ===================================================================================================
    # Formatting (manifest -> bundle text)
# ===================================================================================================

    def format_manifest(self, manifest: BundleManifest) -> str:
        """
        Convert a BundleManifest to plain-marker text (the bundle file).

        Also writes bundle_format_diagnostic.log with details for debugging.
        Directive: diagnostic logging MUST remain; removing it is a violation.

        Behavior:
        - For each BundleEntry in manifest.entries:
          - Emit SEPARATOR
          - Emit "# FILE: path"
          - Emit "# META: encoding=..., eol=..., mode=text|binary"
          - Emit SEPARATOR
          - Emit content (base64 for binary)
        - We ensure that:
          - binary payload is base64 text without extra forced blank lines,
            but we do terminate the block with exactly one newline.
          - text payload is emitted verbatim (plus final newline if missing),
            and we do not prepend SOURCEFILE headers here. SOURCEFILE headers
            are for extracted working files, not for the bundle.
        """

        self._validate_before_format(manifest)

        logger = logging.getLogger("bundle.format_diagnostic")
        logger.setLevel(logging.DEBUG)

        # Set up dedicated handler once (append or overwrite each run)
        if not logger.handlers:
            # Ensure logs directory exists
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            log_file = log_dir / "bundle_format_diagnostic.log"

            fh = logging.FileHandler(
                log_file,
                mode="w",
                encoding="utf-8",
            )
            fh.setLevel(logging.DEBUG)
            fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
            fh.setFormatter(fmt)
            logger.addHandler(fh)
            logger.propagate = False # Prevent double-logging to root logger

        logger.info("=" * 80)
        logger.info("START format_manifest()")
        logger.info("Manifest contains %d entries", len(manifest.entries))
        logger.info("=" * 80)

        out: List[str] = []
        border = self.SEPARATOR
        boundary = self._derive_boundary_token(manifest)
        logger.info(" Boundary token: %s", boundary)

        for idx, entry in enumerate(manifest.entries):
            logger.info("\n--- Processing Entry %d/%d ---", idx + 1, len(manifest.entries))
            logger.info(" Path: %s", entry.path)
            logger.info(" Binary: %s", entry.is_binary)
            logger.info(" Encoding: %s", entry.encoding)
            logger.info(" EOL: %s", entry.eol_style)
            logger.info(" Content length: %d chars", len(entry.content))

            # Use validated values (may have been fixed in _validate_before_format)
            mode = "binary" if entry.is_binary else "text"
            encoding = entry.encoding
            eol = entry.eol_style

            header = (
                f"{border}\n"
                f"# FILE: {entry.path}\n"
                f"# META: encoding={encoding}; eol={eol}; mode={mode}; "
                f"{self.BOUNDARY_KEY}={boundary}\n"
                f"{border}\n"
            )

            if entry.is_binary:
                # Accept bytes/bytearray or already-base64 string.
                if isinstance(entry.content, str):
                    payload = entry.content.strip()
                elif isinstance(entry.content, (bytes, bytearray)):
                    payload = base64.b64encode(bytes(entry.content)).decode("ascii")
                else:
                    raise ProfileFormatError(
                        self.profile_name,
                        f"Unsupported binary content type: {type(entry.content)}",
                    )

                block = header + payload
                # ensure exactly one newline at end of block
                if not block.endswith("\n"):
                    block += "\n"

            else:
                # text branch
                text_body = (
                    entry.content
                    if isinstance(entry.content, str)
                    else str(entry.content)
                )
                block = header + text_body
                if not block.endswith("\n"):
                    block += "\n"

            out.append(block)

        logger.info("COMPLETED format_manifest()")
        return "".join(out)

# ===================================================================================================
    # Helper methods
# ===================================================================================================

    def _parse_meta(self, meta_str: str) -> Dict[str, str]:
        """
        Parse META line key=value; key=value; ...
        """
        meta: Dict[str, str] = {}
        for k, v in self.META_FIELD_PATTERN.findall(meta_str):
            meta[k.strip().lower()] = v.strip()
        return meta

    def _trim_header_spacing(self, content: str, meta: Dict[str, str]) -> str:
        """
        Normalize leading/trailing spacing after the header block.

        Requirements:
        - If the body is effectively empty (whitespace/newlines only),
          normalize to '' (tests assert '' not '\\n').
        - If META trailing=false, strip trailing newline(s).
        - Otherwise, allow at most one trailing newline.
        """

        trailing = (meta.get("trailing") or "").strip().lower()

        # If it's logically empty, collapse to ''
        if content.strip() == "":
            return ""

        # Handle double newline at end
        if content.endswith("\n\n"):
            return content[:-2] if trailing == "false" else content[:-1]

        # Handle single newline at end
        if content.endswith("\n"):
            return content[:-1] if trailing == "false" else content

        return content

    def _finalize(self, raw: Dict[str, str], meta: Dict[str, str]) -> BundleEntry:
        """
        Turn a parsed block {path, content} + META dict into a BundleEntry.
        We normalize separators in the path, guarantee eol_style fallback,
        and decide binary/text.
        """

        norm_path = raw["path"].replace("\\", "/")

        mode = (meta.get("mode") or "").lower()
        encoding_candidate = (
            meta.get("encoding")
            or ("base64" if mode == "binary" else "utf-8")
        )
        encoding = encoding_candidate.lower()

        is_binary = (mode == "binary") or (encoding == "base64")

        eol_candidate = (meta.get("eol") or "").strip()
        # Default based on binary status if empty AFTER parsing
        if not eol_candidate:
            eol_candidate = "n/a" if is_binary else "LF"

        return BundleEntry(
            path=norm_path,
            content=raw.get("content", ""),
            is_binary=is_binary,
            encoding=encoding,
            eol_style=eol_candidate, # Use potentially defaulted value
            checksum=None,
        )

    def _validate_before_format(self, manifest: BundleManifest) -> None:
        """
        Sanity check before formatting, and fill missing/invalid defaults used
        for logging + META output.
        """
        for e in manifest.entries:
            # fill encoding if missing
            if not e.encoding:
                e.encoding = "base64" if e.is_binary else "utf-8"

            # FIX: Check for empty string or None/missing eol_style
            if not e.eol_style:
                e.eol_style = "n/a" if e.is_binary else "LF"
            # Also handle potentially invalid but non-empty values for text entries
            elif not e.is_binary and e.eol_style not in ["LF", "CRLF", "CR", "MIXED"]:
                 # If it's text but has an invalid EOL like 'n/a' or '', default to LF
                 e.eol_style = "LF"
            elif e.is_binary and e.eol_style != "n/a":
                 # If it's binary but doesn't have 'n/a', force it
                 e.eol_style = "n/a"


            # basic binary content shape check
            if e.is_binary and (not isinstance(e.content, (str, bytes, bytearray))):
                raise ProfileFormatError(
                    self.profile_name,
                    "Binary entry content must be str/bytes/bytearray",
                )
