# ===================================================================================================
# SOURCEFILE: plain_marker.py
# RELPATH: bundle_file_tool_v2/src/core/profiles/plain_marker.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.103
# LIFECYCLE: Testing
# Status: Build 103 - bounded transport grammar (BFT_B103_BOUNDED_TRANSPORT_GRAMMAR)
# DESCRIPTION: Plain Marker bundle profile. Serializes project state into
#              transport blocks (# FILE: / # META:) and parses them back
#              into BundleManifest entries. Provides diagnostic logging,
#              newline normalization, duplicate conflict resolution,
#              base64 handling for binaries, and safe path filtering.
# FIXES (2.1.103 - ratified by George 2026-08-04, Paul s5.1-s5.6, s8 step 2):
#   - Bounded transport grammar: the writer derives a deterministic boundary
#     token from the payload, proves it absent from that payload, and carries
#     it as boundary=<token> on each block's # META: line. Only a frame
#     carrying the ACTIVE token is a boundary; everything else is content.
#   - Two-way legacy compatibility: the separator line is unchanged, so a
#     Build 102 reader frames blocks exactly as before and ignores the extra
#     META field. A bundle with no boundary token still parses by the legacy
#     path, so old bundles are unaffected.
#   - Deterministic output: the token is SHA-256 derived over length-prefixed
#     canonical fields with a collision counter, so identical input yields a
#     byte-identical artifact (delivery standard v3 s8 / BFT-B100-036).
#   - Fail loud: structural misuse of the ACTIVE token raises ProfileParseError
#     instead of silently dropping a file.
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
from typing import Callable, Dict, Iterable, List, Optional, Tuple

# Ensure core imports work by adjusting path if necessary
import sys
import os
# Add the parent directory of 'core' to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from core.profiles.base import ProfileBase
from core.models import BundleManifest, BundleEntry
from core.progress import OP_EXTRACT, PHASE_PARSE, ThrottledReporter
from core.version import __version__
from core.exceptions import (
    ProfileParseError,
    ProfileFormatError,
)


class PlainMarkerProfile(ProfileBase):
    """
    Plain Marker format profile.

    Transport format (bundle text) looks like:

# ===================================================================================================
        # FILE: src/core/writer.py
        # META: encoding=utf-8; eol=LF; mode=text; boundary=<32 hex>
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

    Boundary authority (Build 103):
    - An in-band marker cannot be told apart from identical text inside a
      file: a fixture holding a sample bundle is byte-identical to a real
      boundary. The ONLY authority is the per-bundle boundary token, which is
      proven absent from every payload before the artifact is written.
    - A frame carrying the ACTIVE token is a block boundary. Any other
      marker-looking text - including a complete frame carrying a FOREIGN
      token, which is exactly what this project's own test fixtures contain -
      is ordinary content and is preserved byte for byte.
    """

    # Separator line that visually frames each file block
    # We treat any line that is '#' + '=' repeated as a border.
    SEPARATOR = "# " + "=" * 67

    # Simple border matcher (no lookbehind)
    SEPARATOR_PATTERN = re.compile(r"^\s*#\s*={10,}\s*$")

    # --- Bounded transport grammar (ratified by George, 2026-08-04) ---------
    # META was chosen over the separator so legacy readers stay compatible in
    # BOTH directions: an old parser sees its usual separator and treats
    # 'boundary' as one more unknown META field, which it ignores.
    BOUNDARY_KEY = "boundary"
    BOUNDARY_HEX = 32                     # 128 bits of SHA-256
    BOUNDARY_MAX_COLLISION_RETRIES = 64
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

    def parse_stream(self, text: str, *,
                     progress: Optional[Callable] = None) -> BundleManifest:
        """Parse bundle text, dispatching on the transport grammar in use.

        A bundle whose FIRST block is a complete bounded header is parsed with
        the strict state machine. Anything else is parsed exactly as before, so
        v1.1.5 and Build 102 bundles are unaffected.

        Build 111: `progress` is reported against the line count, which is known
        before either path begins, so the parse phase is determinate rather than
        a bare spinner.
        """
        lines = text.splitlines(keepends=True)
        token = self._detect_boundary_token(lines)
        if token is None:
            return self._parse_legacy(text, progress=progress)
        return self._parse_bounded(lines, token, progress=progress)

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

    def _parse_bounded(self, lines, token: str, *,
                       progress: Optional[Callable] = None) -> BundleManifest:
        """Strict state machine for bounded bundles.

        Every line that is not part of a recognised ACTIVE-token block header is
        content, including separators, '# FILE:' lines, '# META:' lines and
        foreign boundary tokens. Structural misuse of the ACTIVE token raises
        rather than silently dropping a file.
        """
        entries: List[BundleEntry] = []
        producer_versions = set()
        reporter = ThrottledReporter(
            progress, OP_EXTRACT, PHASE_PARSE, "lines", total=len(lines))
        i = 0
        while i < len(lines) and not lines[i].strip():
            i += 1

        if self._block_header_at(lines, i, token) is None:
            raise ProfileParseError(
                self.profile_name,
                "bounded bundle does not open with a valid block header",
                i + 1,
            )

        while i < len(lines):
            # Build 111: report on the clock, against the known line count. The
            # entry tally is carried in the message because "412 files
            # recovered" is what the reader cares about, while the line count is
            # what the bar can honestly measure.
            reporter.tick(i, message=f"{len(entries):,} files recovered")
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
                # otherwise make the whole file vanish without a word). A FOREIGN
                # token is content: that is how a fixture holding a sample bundle
                # survives byte for byte.
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
            producer_version = meta.get("bft_version", "")
            if re.fullmatch(r"\d+\.\d+\.\d+", producer_version):
                producer_versions.add(producer_version)
            block = {"path": path, "content": "".join(lines[body_start:j]),
                     "line_start": i + 2}
            try:
                block["content"] = self._recover_bounded_payload(
                    block["content"], meta, i + 2)
            except ProfileParseError as error:
                producer = (f"BFT {producer_version}" if producer_version in producer_versions
                            else "producer build not recorded")
                raise ProfileParseError(
                    self.profile_name,
                    f"{path!r}: {error.reason} ({producer})",
                    error.line_number,
                ) from error
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
        reporter.close(len(lines),
                       message=f"Parsed {len(consolidated):,} files")
        return BundleManifest(
            entries=consolidated,
            profile=self.profile_name,
            metadata={
                "format_version": "2.1.103",
                "parser": "PlainMarkerProfile",
                "transport": "bounded",
                "boundary": token,
                "bft_versions": sorted(producer_versions),
            },
        )

    def _emitted_payload(self, entry: BundleEntry) -> str:
        """Return exactly the body text format_manifest() will write for *entry*.

        Both the boundary derivation and the writer use this one function, so
        the token can never be proven absent from a payload that differs from
        the payload actually emitted.
        """
        if entry.is_binary:
            if isinstance(entry.content, str):
                return entry.content.strip()
            if isinstance(entry.content, (bytes, bytearray)):
                return base64.b64encode(bytes(entry.content)).decode("ascii")
            raise ProfileFormatError(
                self.profile_name,
                f"Unsupported binary content type: {type(entry.content)}",
            )
        return entry.content if isinstance(entry.content, str) else str(entry.content)

    def _boundary_candidate(self, manifest, payloads: Iterable[str], counter: int) -> str:
        """Return the candidate boundary token for *counter*.

        This is the single deterministic seam of the derivation: the digest
        covers a length-prefixed canonical encoding of every field that can
        change the artifact, so no two distinguishable manifests share a token
        and the same manifest always yields the same one. Isolated as its own
        method so tests can force the collision-counter path without patching
        hashlib (Paul s7 item 22).
        """
        h = hashlib.sha256()
        h.update(b"BFT-BOUNDARY-v1\x00")
        h.update(__version__.encode("ascii") + b"\x00")
        h.update(str(counter).encode("ascii") + b"\x00")
        for entry, payload in zip(manifest.entries, payloads):
            for field in (
                entry.path,
                entry.encoding or "",
                entry.eol_style or "",
                "binary" if entry.is_binary else "text",
                payload,
            ):
                raw = field.encode("utf-8", errors="replace")
                h.update(str(len(raw)).encode("ascii") + b":")
                h.update(raw)
        return h.hexdigest()[: self.BOUNDARY_HEX]

    def _derive_boundary_token(self, manifest) -> str:
        """Derive a deterministic boundary token absent from the payload.

        The digest covers length-prefixed path, encoding, eol, mode and the
        EMITTED payload of every entry in manifest order, so any change to any
        of those changes the token. The boundary field itself is excluded,
        which would otherwise be circular. On collision the digest is recomputed
        with a counter, so the result stays reproducible.
        """
        for counter in range(self.BOUNDARY_MAX_COLLISION_RETRIES):
            # Recompute lazily instead of retaining a second complete list of
            # payload strings. On a large self-bundle that list alone was
            # hundreds of MiB; the manifest already owns the canonical content.
            payloads = (self._emitted_payload(entry)
                        for entry in manifest.entries)
            token = self._boundary_candidate(manifest, payloads, counter)
            if all(token not in self._emitted_payload(entry)
                   for entry in manifest.entries) and all(
                token not in (entry.path or "") for entry in manifest.entries
            ):
                return token
        raise ProfileFormatError(
            self.profile_name,
            "could not derive a boundary token absent from the content",
        )

    def _parse_legacy(self, text: str, *,
                      progress: Optional[Callable] = None) -> BundleManifest:
        """
        Parse legacy (unbounded) plain-marker bundle text into a BundleManifest.

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

        all_lines = text.splitlines(keepends=True)
        reporter = ThrottledReporter(
            progress, OP_EXTRACT, PHASE_PARSE, "lines", total=len(all_lines))

        for line_no, line in enumerate(all_lines, start=1):
            reporter.tick(line_no, message=f"{len(entries):,} files recovered")
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

        reporter.close(len(all_lines),
                       message=f"Parsed {len(consolidated):,} files")

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
        - Zero-regression rule: only adds functionality
        - QC checks: makes validation more robust
        - Documentation: fully documented with team decision context
        - Formal change management: approved by John, Paul, George
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
        - Derive one deterministic boundary token for the whole manifest and
          prove it absent from every emitted payload.
        - For each BundleEntry in manifest.entries:
          - Emit SEPARATOR
          - Emit "# FILE: path"
          - Emit "# META: encoding=..., eol=..., mode=text|binary, boundary=..."
          - Emit SEPARATOR
          - Emit content (base64 for binary)
        - We ensure that:
          - binary payload is base64 text without extra forced blank lines,
            but we do terminate the block with exactly one newline.
          - text payload is emitted verbatim (plus final newline if missing),
            and we do not prepend SOURCEFILE headers here. SOURCEFILE headers
            are for extracted working files, not for the bundle.
        """

        return "".join(self.iter_format_manifest(manifest))

    def iter_format_manifest(self, manifest: BundleManifest):
        """Yield one complete transport block at a time."""
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

        border = self.SEPARATOR
        boundary = self._derive_boundary_token(manifest)
        logger.info("Boundary token: %s", boundary)

        for idx, entry in enumerate(manifest.entries):
            logger.info(
                "Entry %d/%d path=%s binary=%s encoding=%s eol=%s chars=%d",
                idx + 1, len(manifest.entries), entry.path, entry.is_binary,
                entry.encoding, entry.eol_style, len(entry.content))

            # Use validated values (may have been fixed in _validate_before_format)
            mode = "binary" if entry.is_binary else "text"
            encoding = entry.encoding
            eol = entry.eol_style

            header = (
                f"{border}\n"
                f"# FILE: {entry.path}\n"
                f"# META: encoding={encoding}; eol={eol}; mode={mode}; "
                f"{self.BOUNDARY_KEY}={boundary}; bft_version={__version__}"
                + (f"; size={entry.file_size_bytes}"
                   if entry.file_size_bytes is not None else "")
                + "\n"
                f"{border}\n"
            )

            block = header + self._emitted_payload(entry)
            # ensure exactly one newline at end of block
            if not block.endswith("\n"):
                block += "\n"

            yield block

        logger.info("COMPLETED format_manifest()")

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

    def _recover_bounded_payload(self,
                                 content: str,
                                 meta: Dict[str, str],
                                 line_number: int) -> str:
        """Remove only bounded-format padding, preserving source text bytes.

        New bounded blocks carry the source byte size.  Formatting adds one LF
        only when the payload does not already end in LF.  Recovering exactly
        ``size`` bytes therefore preserves CRLF, CR, mixed endings, empty files,
        and files without a final newline.  Older blocks without a usable size
        retain the legacy spacing behavior.
        """
        mode = (meta.get("mode") or "").strip().lower()
        encoding = (meta.get("encoding") or "utf-8").strip()
        size_text = (meta.get("size") or "").strip()
        if mode == "binary" or not size_text:
            return self._trim_header_spacing(content, meta)

        try:
            expected_size = int(size_text)
        except ValueError:
            return self._trim_header_spacing(content, meta)
        if expected_size < 0:
            return self._trim_header_spacing(content, meta)

        try:
            raw = content.encode(encoding, errors="strict")
        except (LookupError, UnicodeEncodeError) as error:
            raise ProfileParseError(
                self.profile_name,
                f"cannot recover text payload using encoding {encoding!r}: {error}",
                line_number,
            ) from error

        if len(raw) < expected_size:
            raise ProfileParseError(
                self.profile_name,
                "text payload is shorter than its declared byte size "
                f"(declared {expected_size}, available {len(raw)} bytes)",
                line_number,
            )

        padding = raw[expected_size:]
        if padding not in {b"", b"\n"}:
            raise ProfileParseError(
                self.profile_name,
                "text payload exceeds its declared byte size "
                f"(declared {expected_size}, available {len(raw)} bytes)",
                line_number,
            )

        try:
            return raw[:expected_size].decode(encoding, errors="strict")
        except UnicodeDecodeError as error:
            raise ProfileParseError(
                self.profile_name,
                "declared byte size splits an encoded text character",
                line_number,
            ) from error

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

        file_size = None
        size_candidate = (meta.get("size") or "").strip()
        if size_candidate:
            try:
                parsed_size = int(size_candidate)
                if parsed_size >= 0:
                    file_size = parsed_size
            except ValueError:
                pass

        return BundleEntry(
            path=norm_path,
            content=raw.get("content", ""),
            is_binary=is_binary,
            encoding=encoding,
            eol_style=eol_candidate, # Use potentially defaulted value
            checksum=None,
            file_size_bytes=file_size,
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
