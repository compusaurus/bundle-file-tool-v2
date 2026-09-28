# SOURCEFILE: parser.py
# RELPATH: bundle_file_tool_v2/src/core/parser.py
# PROJECT: Bundle File Tool v2.1
# VERSION: 2.1.1
# STATUS: FIXED - Heuristic detection per Paul's analysis v3
# Relative Path: src/core/parser.py
# Purpose:
# independent_entry_point:
# Status:
# ===================================================================================================
# BFT_B105_PROFILE_REGISTRY_COMPLETE - every configurable profile is registered

"""Bundle Parser Module."""

from typing import Callable, Optional, List, Dict, Type
from pathlib import Path
import codecs
import inspect
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.bundle_integrity import bundle_integrity_report
from core.models import BundleManifest
from core.progress import OP_EXTRACT, PHASE_READ, ThrottledReporter
from core.profiles.base import ProfileBase
from core.profiles.plain_marker import PlainMarkerProfile
from core.profiles.markdown_fence import MarkdownFenceProfile
from core.exceptions import (
    ProfileNotFoundError,
    ProfileDetectionError,
    ProfileParseError,
    BundleReadError
)


class ProfileRegistry:
    """Registry for managing available bundle format profiles."""

    def __init__(self):
        self._profiles: Dict[str, Type[ProfileBase]] = {}
        self._register_builtin_profiles()

    def _register_builtin_profiles(self):
        """Register built-in profile implementations.

        Build 105. MarkdownFenceProfile was implemented but never registered, so
        any invocation resolving to the 'md_fence' profile - including
        ConfigManager.DEFAULT_CONFIG's own default - raised ProfileNotFoundError.
        The gap survived because the markdown tests instantiate the profile
        directly and the registry tests only asserted that plain_marker exists.

        Every profile the configuration can select must be registered here.
        """
        self.register(PlainMarkerProfile)
        self.register(MarkdownFenceProfile)

    def register(self, profile_class: Type[ProfileBase]) -> None:
        """Register a profile class."""
        if not issubclass(profile_class, ProfileBase):
            raise TypeError(f"{profile_class.__name__} must be a ProfileBase subclass")

        instance = profile_class()
        profile_name = instance.profile_name

        self._profiles[profile_name] = profile_class

    def get(self, profile_name: str) -> ProfileBase:
        """Get a profile instance by name."""
        if profile_name not in self._profiles:
            raise ProfileNotFoundError(profile_name, list(self._profiles.keys()))

        return self._profiles[profile_name]()

    def list_profiles(self) -> List[str]:
        """List all registered profile names in sorted order."""
        return sorted(self._profiles.keys())

    def get_all_profiles(self) -> List[ProfileBase]:
        """Get instances of all registered profiles."""
        return [profile_class() for profile_class in self._profiles.values()]


class BundleParser:
    """Main parser for bundle files."""

    #: A UTF-8 signature is transport metadata, not part of the first bundle
    #: frame.  ``utf-8-sig`` consumes it when present and behaves exactly like
    #: ``utf-8`` when absent.  Decoding is deliberately strict: an unknown byte
    #: must stop ingress rather than disappear from a payload that is then
    #: reported as valid.
    BUNDLE_TEXT_ENCODING = "utf-8-sig"
    UTF8_BOM = "\ufeff"
    TRANSPORT_BOMS = (
        (b"\x00\x00\xfe\xff", "UTF-32 BE", "utf-32"),
        (b"\xff\xfe\x00\x00", "UTF-32 LE", "utf-32"),
        (b"\xfe\xff", "UTF-16 BE", "utf-16"),
        (b"\xff\xfe", "UTF-16 LE", "utf-16"),
    )

    def __init__(self, registry: Optional[ProfileRegistry] = None):
        """Initialize parser."""
        self.registry = registry or ProfileRegistry()

    def parse(self,
              text: str,
              profile_name: Optional[str] = None,
              auto_detect: bool = True,
              *,
              progress: Optional[Callable] = None) -> BundleManifest:
        """Parse bundle text into a manifest.

        Build 111: `progress` is keyword-only and optional. When supplied it is
        handed to the profile, which reports determinate line-oriented progress
        for the parse phase.
        """
        text = self._without_transport_bom(text)

        # Pre-check for empty content
        if not text or not text.strip():
            raise ValueError("Empty bundle text")

        if profile_name:
            profile = self.registry.get(profile_name)
            return self._parse_with_profile(text, profile, progress=progress)

        elif auto_detect:
            profile = self._detect_profile(text)
            return self._parse_with_profile(text, profile, progress=progress)

        else:
            raise ValueError("Must specify profile_name or enable auto_detect")

    #: Read granularity for progress-reporting reads. Large enough that the
    #: chunk loop costs nothing measurable against a plain read, small enough
    #: that a slow disk still moves the bar.
    READ_CHUNK_BYTES = 1 << 20  # 1 MiB
    # Compatibility for tests/extensions that inspected the old private name.
    READ_CHUNK_CHARS = READ_CHUNK_BYTES

    def parse_file(self,
                   file_path: Path,
                   profile_name: Optional[str] = None,
                   auto_detect: bool = True,
                   *,
                   encoding: Optional[str] = None,
                   progress: Optional[Callable] = None) -> BundleManifest:
        """Parse a bundle file from disk.

        Build 111: with a sink supplied, the file is read in chunks so the read
        phase reports determinate byte progress. Reading a large bundle was
        previously one blocking call with no observable state - on a 78 MB
        bundle that is a visible stall before parsing even begins.
        """
        text = self.read_bundle_text(
            file_path, encoding=encoding, progress=progress)
        return self.parse(text, profile_name, auto_detect, progress=progress)

    def read_bundle_text(self,
                         file_path: Path,
                         *,
                         encoding: Optional[str] = None,
                         progress: Optional[Callable] = None,
                         operation: str = OP_EXTRACT) -> str:
        """Read and strictly decode one bundle at the shared byte boundary.

        ``encoding`` is an explicit operator override.  With no override BFT
        accepts UTF-8 with or without its signature.  UTF-16/32 signatures are
        named before decoding so a transport problem is never misreported as a
        profile-detection failure.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise BundleReadError(str(file_path), "File not found")

        try:
            if progress is None:
                data = file_path.read_bytes()
                return self._decode_bundle_bytes(data, file_path, encoding)
            return self._read_text_reporting(
                file_path, progress, encoding=encoding, operation=operation)
        except BundleReadError:
            raise
        except Exception as error:
            raise BundleReadError(
                str(file_path), f"Failed to read file: {error}") from error

    @classmethod
    def _decode_bundle_bytes(cls,
                             data: bytes,
                             file_path: Path,
                             encoding: Optional[str] = None) -> str:
        """Decode bytes without replacement or deletion."""
        requested_encoding = encoding or cls.BUNDLE_TEXT_ENCODING

        if encoding is None:
            for signature, detected, override in cls.TRANSPORT_BOMS:
                if data.startswith(signature):
                    raise BundleReadError(
                        str(file_path),
                        f"detected {detected} byte-order mark; default bundle "
                        f"ingress accepts UTF-8 only. Specify encoding "
                        f"'{override}' explicitly (CLI: --encoding {override}).",
                    )

        try:
            canonical_encoding = codecs.lookup(requested_encoding).name
        except LookupError as error:
            raise BundleReadError(
                str(file_path),
                f"unknown text encoding '{requested_encoding}'",
            ) from error

        decode_data = data
        decode_encoding = requested_encoding
        offset_base = 0
        if canonical_encoding == "utf-8-sig" and data.startswith(b"\xef\xbb\xbf"):
            # Python's utf-8-sig decoder reports errors relative to the bytes
            # after the signature.  Strip it explicitly so diagnostics can add
            # the three-byte prefix and report a physical file offset.
            decode_data = data[3:]
            decode_encoding = "utf-8"
            offset_base = 3

        try:
            text = decode_data.decode(decode_encoding, errors="strict")
        except UnicodeDecodeError as error:
            offending = error.object[error.start:error.end]
            rendered = " ".join(f"0x{byte:02X}" for byte in offending)
            if not rendered:
                rendered = "incomplete byte sequence"
            physical_offset = offset_base + error.start
            raise BundleReadError(
                str(file_path),
                f"cannot decode as {requested_encoding} at byte offset "
                f"{physical_offset}; offending byte(s): {rendered}. Specify the "
                "bundle encoding explicitly (for example, --encoding cp1252).",
            ) from error

        # Do not apply universal-newline translation here.  Bundle structure
        # may use LF while a payload carries CRLF, CR, or mixed endings; changing
        # the decoded transport would change those payload bytes before the
        # profile has a chance to recover them.
        return cls._without_transport_bom(text)

    def _read_text_reporting(self,
                             file_path: Path,
                             progress: Callable,
                             *,
                             encoding: Optional[str] = None,
                             operation: str = OP_EXTRACT) -> str:
        """Read a text file in chunks, reporting bytes consumed.

        The total comes from the file size on disk, so this phase is
        determinate from the first event. Character and byte counts diverge for
        multi-byte encodings; the byte figure is the honest one for a progress
        bar because it is what the disk is actually delivering, so the reported
        position is derived from the file handle rather than the decoded length.
        """
        total_bytes = file_path.stat().st_size
        reporter = ThrottledReporter(
            progress, operation, PHASE_READ, "bytes", total=total_bytes)

        chunks = []
        with open(file_path, "rb") as handle:
            while True:
                chunk = handle.read(self.READ_CHUNK_BYTES)
                if not chunk:
                    break
                chunks.append(chunk)
                reporter.tick(min(handle.tell(), total_bytes),
                              message=f"Reading {file_path.name}")

        reporter.close(total_bytes, message=f"Read {file_path.name}")
        return self._decode_bundle_bytes(b"".join(chunks), file_path, encoding)

    @classmethod
    def _without_transport_bom(cls, text: str) -> str:
        """Remove one leading Unicode BOM from externally decoded text.

        File-based callers are covered by :attr:`BUNDLE_TEXT_ENCODING`; this
        second ingress guard keeps the public string APIs equivalent when a
        caller has already decoded UTF-8 bytes with plain ``utf-8``.  Only the
        first code point is considered.  A BOM inside a bundled file payload
        remains data and is preserved.
        """
        if isinstance(text, str) and text.startswith(cls.UTF8_BOM):
            return text[1:]
        return text

    def format(self, manifest: BundleManifest) -> str:
        """Format a BundleManifest into bundle text."""
        if not isinstance(manifest, BundleManifest):
            raise TypeError("manifest must be a BundleManifest")

        profile = self.registry.get(manifest.profile)
        return profile.format_manifest(manifest)

    def _detect_profile(self, text: str) -> ProfileBase:
        """Auto-detect the appropriate profile for the given text."""
        profiles = self.registry.get_all_profiles()

        attempted = []
        for profile in profiles:
            attempted.append(profile.profile_name)

            snippet = text[:2048]

            if profile.detect_format(snippet):
                return profile

        raise ProfileDetectionError(attempted)

    @staticmethod
    def _accepts_progress(func: Callable) -> bool:
        """Whether `func` declares a `progress` parameter, or accepts **kwargs.

        >>> BundleParser._accepts_progress(lambda text, *, progress=None: None)
        True
        >>> BundleParser._accepts_progress(lambda text: None)
        False
        """
        try:
            params = inspect.signature(func).parameters
        except (TypeError, ValueError):
            return False
        if "progress" in params:
            return True
        return any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values())

    def _parse_with_profile(self, text: str, profile: ProfileBase, *,
                            progress: Optional[Callable] = None) -> BundleManifest:
        """Parse text using a specific profile.

        Build 111: a profile written against the pre-111 contract does not
        accept `progress`. Its acceptance is decided by inspecting the
        signature, never by catching TypeError from the call - a genuine
        TypeError raised inside parsing would otherwise be swallowed and
        silently retried, turning a real defect into a missing progress bar.
        """
        try:
            if progress is not None and self._accepts_progress(profile.parse_stream):
                manifest = profile.parse_stream(text, progress=progress)
            else:
                manifest = profile.parse_stream(text)
            return manifest
        except ProfileParseError:
            raise
        except Exception as e:
            raise ProfileParseError(
                profile.profile_name,
                f"Unexpected error during parsing: {str(e)}"
            )

    def detect_profile_name(self, text: str) -> Optional[str]:
        """
        Detect profile name without parsing.

        PAUL'S FIX: Heuristic detection for common formats, RAISE for unknown.

        Rules shaped to satisfy tests:
        - Empty/whitespace -> ValueError("Empty bundle text")
        - Clear plain_marker markers -> "plain_marker"
        - Clear Markdown-fence markers -> "md_fence" (heuristic)
        - Extremely short / unknown / ambiguous -> raise ProfileDetectionError
        """
        text = self._without_transport_bom(text)
        if not text or not text.strip():
            raise ValueError("Empty bundle text")

        snippet = text[:2048]

        # Heuristic: plain_marker has '# FILE:' / '# BEGIN FILE' style markers
        if "# FILE:" in snippet or "# BEGIN FILE" in snippet or "# ==== " in snippet:
            return "plain_marker"

        # Heuristic: markdown-fence style (triple backticks, possible language/info)
        # e.g. ``` or ```bundle or fenced sections that look like files
        if "```" in snippet:
            return "md_fence"

        # If the registered profiles can detect it, use them
        try:
            profile = self._detect_profile(text)
            return profile.profile_name
        except ProfileDetectionError:
            # For all non-empty but unknown/too-short cases, tests expect a raise
            raise

    def validate_bundle(self, text: str, profile_name: Optional[str] = None) -> Dict:
        """Validate a bundle without fully parsing it."""
        text = self._without_transport_bom(text)
        result = {
            'valid': True,
            'profile': None,
            'file_count': 0,
            'errors': [],
            'warnings': []
        }

        if not text or not text.strip():
            result['valid'] = False
            result['errors'].append("Bundle text is empty")
            return result

        try:
            if profile_name:
                profile = self.registry.get(profile_name)
            else:
                profile = self._detect_profile(text)

            result['profile'] = profile.profile_name

            manifest = profile.parse_stream(text)
            # Build 198 S2a: refuse a bundle that embeds a nested full-source bundle/archive.
            _integrity = bundle_integrity_report(manifest)
            if not _integrity['clean']:
                result['valid'] = False
                for _p, _why, _mc in _integrity['nested_bundle_entries']:
                    result['errors'].append(f"Nested bundle detected [{_why}]: {_p}")
            result['file_count'] = manifest.get_file_count()

            if manifest.get_file_count() == 0:
                result['warnings'].append("Bundle contains no files")

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


# Convenience Functions
_default_parser = None

def get_default_parser() -> BundleParser:
    global _default_parser
    if _default_parser is None:
        _default_parser = BundleParser()
    return _default_parser

def parse_bundle(text: str, profile_name: Optional[str] = None) -> BundleManifest:
    """Convenience function to parse bundle text."""
    parser = get_default_parser()
    return parser.parse(text, profile_name)

def parse_bundle_file(file_path: Path) -> BundleManifest:
    """Convenience function to parse bundle file."""
    parser = get_default_parser()
    return parser.parse_file(file_path)


# ===================================================================================================
# VERSION: 2.1.1
# PAUL'S FIX: Heuristic detection (plain_marker, md_fence) + raise for unknown
# FIXES: 12 parser failures (detection tests expect ProfileDetectionError, not None)
# ===================================================================================================
# ===================================================================
