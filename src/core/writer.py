# ===================================================================================================
# SOURCEFILE: writer.py
# RELPATH: bundle_file_tool_v2/src/core/writer.py
# PROJECT: Bundle File Tool v2.1
# VERSION: 2.1.103
# STATUS: Build 103 - extract reconciliation (BFT_B103_EXTRACT_RECONCILIATION)
# DESCRIPTION:
#   Handles file I/O for bundling (BundleCreator) and extraction (BundleWriter).
# FIXES (2.1.103 - ratified by George 2026-08-04):
#   - extract_manifest() reconciles the manifest entry count against the
#     processed/skipped/errored outcomes and the write ledgers, and raises
#     ValidationError rather than reporting a partial extraction as complete.
# FIXES (v2.1.11):
#   - CRITICAL FIX: Aligned write_entry policy checks with __init__ logic.
#   - __init__ stores policy as string value (e.g., "prompt"), but
#     write_entry was comparing against Enum object (OverwritePolicy.PROMPT).
#   - All policy comparisons now use .value (e.g., OverwritePolicy.PROMPT.value).
# FIXES (v2.1.10):
#   - CRITICAL BUG FIX: Fixed OverwritePolicy Enum conversion in BundleWriter.__init__
#   - When OverwritePolicy.RENAME (or other Enum) was passed, str(Enum) incorrectly
#     converted it to "OverwritePolicy.RENAME" instead of "rename"
#   - Now properly extracts .value from Enum instances
#   - Validates against list of valid policy string values
# FIXES (v2.1.9):
#   - Aligned BundleCreator.__init__ glob defaults with test expectations
#   - DEFAULT_ALLOW_GLOBS set to ['**/*']
#   - __init__ now REPLACES deny_globs if provided, not merges.
#   - __init__ KEEPS default deny_globs if deny_globs is None (preserves safety)
# Relative Path: src/core/writer.py
# Purpose:
# independent_entry_point:
# Status:
# ===================================================================================================
# BFT_B106_DISCOVERY_PROGRESS_EVENTS - rising count during the walk

from __future__ import annotations
from pathlib import Path, PurePosixPath
from typing import Callable, Dict, List, Optional, Set, Tuple, Union
import base64
import sys
import os
import re
import time
from enum import Enum
from datetime import datetime
import logging # Added for potential future logging

# Ensure project root is discoverable for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.models import BundleManifest, BundleEntry
from core.exceptions import (
    BundleFileToolError,
    BundleWriteError,
    PathTraversalError,
    OverwriteError,
    FileSizeError,
    ValidationError
)
from core.version import __version__
from core.cancellation import (
    CancelCheck, OperationCancelled, is_cancelled, raise_if_cancelled,
)
from core.progress import (
    OP_BUNDLE, OP_EXTRACT, PHASE_COMPLETE, PHASE_DISCOVER, PHASE_READ,
    PHASE_WRITE, OperationProgress, emit,
)

# ===================================================================================================
# Team Directives v4 Compliance:
# - BundleWriter.add_headers defaults to True to enforce canonical headers.
# - BundleCreator.DEFAULT_DENY_GLOBS curated list is kept for safety.
# ===================================================================================================


# BFT_B110_DISCOVERY_PRUNING - PERF-BFT-001 / PERF-BFT-002 (ARCH-RULING-2026-08-24-01)
#
# Discovery reports at most this often. emit() delivers to the sink
# synchronously with no rate limiting of its own, so an unthrottled per-file
# emit would saturate the UI thread across tens of thousands of files. 100ms is
# well inside the interval at which a progress bar still reads as live, and
# costs one monotonic() call per file.
_DISCOVER_EMIT_INTERVAL_S = 0.10

#: Matches a deny pattern that excludes an entire directory subtree: ``**/NAME/**``
_DIR_DENY_PATTERN = re.compile(r"\*\*/([^*/]+)/\*\*")


def prunable_dir_names(deny_patterns: Optional[List[str]]) -> Set[str]:
    """Directory names that ``os.walk`` may skip without descending.

    Derived strictly from deny patterns that already exclude a whole subtree,
    so pruning can never change which files are discovered - it only avoids
    walking into trees whose contents would be filtered out anyway.

    Only ``**/NAME/**`` qualifies. ``**/*.log`` says nothing about directories,
    and ``**/build/*`` denies only immediate children rather than the subtree,
    so neither is safe to prune on. Being conservative here is precisely what
    guarantees the discovered file set is unchanged.

    Args:
        deny_patterns: The active deny globs, or None.

    Returns:
        Bare directory names that are safe to prune, possibly empty.

    Example:
        >>> sorted(prunable_dir_names(["**/.venv/**", "*.log", "**/archives/**"]))
        ['.venv', 'archives']
    """
    if not deny_patterns:
        return set()

    names: Set[str] = set()
    for pattern in deny_patterns:
        match = _DIR_DENY_PATTERN.fullmatch(str(pattern).strip())
        if match:
            names.add(match.group(1))
    return names


# BFT_B109_HEADER_ALLOWLIST - Option B+ (ARCH-RULING-2026-08-23-02, F-01)
#
# Provenance headers are `#` comment blocks, so they may only be injected into
# formats where `#` begins a comment. Before Build 109 they were prepended to
# every text entry with no type check, which left JSON, XML, HTML, CSS, JS and
# SQL unparseable after an ordinary default extraction.
#
# Both sets are stored lower-case; the lookup normalises the candidate. Adding a
# structured format here would reintroduce the defect, so a test guards it.
HASH_COMMENT_EXTENSIONS = frozenset({
    ".py", ".pyw", ".sh", ".bash", ".zsh", ".ksh", ".csh",
    ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
    ".r", ".rb", ".pl", ".pm", ".tcl", ".dockerfile",
    ".env", ".properties", ".ps1", ".psm1",
})

# Exact filenames, matched case-insensitively, for files that carry no suffix.
HASH_COMMENT_FILENAMES = frozenset({
    "dockerfile", "makefile", "gemfile", "vagrantfile", "inventory",
})


def accepts_hash_header(entry_path: str) -> bool:
    """Whether a `#` provenance block is valid syntax for this file.

    Args:
        entry_path: The entry's relative path. Only its final component matters;
            the decision is per file, never per directory.

    Returns:
        True when the name matches a governed exact filename or a governed
        extension, both case-normalised. False for everything else, which is
        then extracted byte-pure.
    """
    name = PurePosixPath(str(entry_path).replace("\\", "/")).name.lower()
    if not name:
        return False
    if name in HASH_COMMENT_FILENAMES:
        return True
    # A leading-dot name such as `.env` has no suffix as far as pathlib is
    # concerned, so it is matched as an extension in its own right. Without this
    # the ruling's `.env` entry would never fire.
    if name.startswith(".") and name.count(".") == 1:
        return name in HASH_COMMENT_EXTENSIONS
    suffix = PurePosixPath(name).suffix.lower()
    return bool(suffix) and suffix in HASH_COMMENT_EXTENSIONS


def insert_provenance_header(content: str, header: str) -> str:
    """Place the provenance block without displacing a shebang.

    BFT_B109_SHEBANG_PRESERVED. Option B+ decides *whether* a `#` header is
    valid for a format; this decides *where* it goes. A shebang is a comment, so
    the allow-list is satisfied either way - but `#!` is only honoured at byte 0.
    Prepending the block to a shell script leaves valid syntax and an
    unexecutable file, which is the same class of harm F-01 was raised for.

    Args:
        content: The entry's text payload.
        header: The provenance block, ending in a newline.

    Returns:
        The payload with the header at the top, or immediately after the
        shebang line when one is present.
    """
    if not content.startswith("#!"):
        return header + content

    break_at = content.find("\n")
    if break_at == -1:
        # A shebang and nothing else; keep it first and terminate the line.
        return content + "\n" + header
    return content[:break_at + 1] + header + content[break_at + 1:]


class OverwritePolicy(Enum):
    PROMPT = "prompt"
    SKIP = "skip"
    OVERWRITE = "overwrite"
    RENAME = "rename"

class BundleWriter:
    """Handles file writing operations during bundle extraction."""

    def __init__(self,
                 base_path: Optional[Path] = None,
                 output_dir: Optional[Path] = None,
                 overwrite_policy: Union[str, OverwritePolicy] = OverwritePolicy.PROMPT,
                 dry_run: bool = False,
                 add_headers: bool = True,
                 header_metadata: Optional[Dict[str, str]] = None):
        """
        Initialize BundleWriter.

        Args:
            base_path: Base path for relative path resolution (defaults to cwd).
            output_dir: Directory to write files to (defaults to base_path).
            overwrite_policy: Policy for handling existing files (prompt, skip,
                              rename, overwrite). Defaults to prompt.
            dry_run: If True, simulate writing without touching the filesystem.
            add_headers: If True, inject canonical repository headers into
                         extracted text files. (Default: True per Team Directive v4)
            header_metadata: Optional truthful project/team/lifecycle values for
                             injected headers. Missing values remain explicitly
                             unspecified rather than claiming BFT's ownership.
        """
        self.base_path = Path(base_path).resolve() if base_path else Path.cwd()
        self.output_dir = Path(output_dir).resolve() if output_dir else self.base_path
        
        # Normalize policy: extract .value from Enum or lowercase string
        policy: str
        if isinstance(overwrite_policy, OverwritePolicy):
            policy = overwrite_policy.value  # Get the string value from Enum
        elif isinstance(overwrite_policy, str):
            policy = overwrite_policy.lower()
        else:
            policy = str(overwrite_policy).lower()  # Fallback for unexpected types
        
        # Validate against known policy values
        valid_policies = [p.value for p in OverwritePolicy]
        if policy not in valid_policies:
            policy = OverwritePolicy.PROMPT.value  # Safe default
        
        self.overwrite_policy = policy
        self.dry_run = dry_run
        self.add_headers = add_headers
        self.header_metadata = dict(header_metadata or {})

        # State tracking for reporting and rename logic
        self.files_written: List[Path] = []
        self.files_skipped: List[Path] = []
        self.files_renamed: Dict[Path, Path] = {}
        self.pending_writes: Set[Path] = set() # Tracks files targeted in this run

    def extract_manifest(self,
                        manifest: BundleManifest,
                        output_dir: Optional[Path] = None,
                        progress: Optional[Callable] = None,
                        emit_complete: bool = True,
                        cancel: Optional[CancelCheck] = None) -> Dict[str, int]:
        """
        Extract all files from a BundleManifest to the specified output directory.

        Args:
            manifest: BundleManifest object containing file entries.
            output_dir: Optional directory to extract files into. Overrides the
                        instance's output_dir if provided.
            progress: Optional sink receiving OperationProgress events. Build 107.
                      Extraction knows its size up front, so unlike discovery
                      every event here is determinate.
            emit_complete: Whether to emit the terminal PHASE_COMPLETE event.
                      Build 109 (F-06). True for a direct caller such as the
                      CLI. False when a facade wraps this call and owns the
                      operation's completion, so the stream carries exactly one
                      terminal event rather than two.

        Returns:
            Dictionary summarizing results: {"processed": int, "skipped": int, "errors": int}

        Raises:
            OverwriteError: If overwrite_policy is 'prompt' and a file exists.
            PathTraversalError: If an entry's path attempts to escape the output dir.
            BundleWriteError: For filesystem errors or encoding/decoding issues.
        """
        # Reset state for this extraction operation
        self.files_written.clear()
        self.files_skipped.clear()
        self.files_renamed.clear()
        self.pending_writes.clear()

        # Determine the final output directory, resolving to absolute path
        final_output_dir = Path(output_dir).resolve() if output_dir else self.output_dir

        # Ensure base output directory exists (only if not dry run)
        if not self.dry_run:
            final_output_dir.mkdir(parents=True, exist_ok=True)

        stats = {"processed": 0, "skipped": 0, "errors": 0}

        if not manifest or not manifest.entries:
            # Handle empty manifest gracefully
            return stats

        # BFT_B107_EXTRACT_PROGRESS - the unbundle path reports too.
        total_entries = len(manifest.entries)

        for _write_index, entry in enumerate(manifest.entries, start=1):
            # BFT_B112_CANCEL_WRITE. Between entries, so every file already
            # written is complete. The partial paths travel with the exception
            # because the operator has to be told what is on their disk.
            if is_cancelled(cancel):
                raise OperationCancelled(
                    operation=OP_EXTRACT, phase=PHASE_WRITE,
                    completed=stats["processed"], total=total_entries,
                    partial_paths=list(self.files_written),
                )
            emit(progress, OperationProgress(
                operation=OP_EXTRACT, phase=PHASE_WRITE,
                current=_write_index, total=total_entries, unit="files",
                message=entry.path,
            ))
            try:
                # Resolve the target path and validate it's safe
                target_path = self._resolve_output_path(entry.path, final_output_dir)
                self._validate_path(target_path, final_output_dir)

                # Attempt to write the entry based on policies
                status, written_path_str = self.write_entry(
                    entry,
                    target_path,
                    apply_headers=self.add_headers # Use instance default
                )

                if status == "processed":
                    stats["processed"] += 1
                elif status == "skipped":
                    stats["skipped"] += 1

            except (OverwriteError, PathTraversalError, BundleWriteError) as e:
                # Log specific, expected errors and continue if possible
                logging.warning(f"Error processing entry '{entry.path}': {e}")
                stats["errors"] += 1
                # Re-raise OverwriteError if policy is PROMPT, as it's fatal
                if isinstance(e, OverwriteError) and self.overwrite_policy == OverwritePolicy.PROMPT.value:
                    raise
            except Exception as e:
                # Catch unexpected errors
                logging.error(f"Unexpected error processing entry '{entry.path}': {e}", exc_info=True)
                stats["errors"] += 1

        self._reconcile_extraction(manifest, stats)
        if not emit_complete:
            return stats
        emit(progress, OperationProgress(
            operation=OP_EXTRACT, phase=PHASE_COMPLETE,
            current=stats["processed"], total=total_entries, unit="files",
            message=f"Extracted {stats['processed']} of {total_entries} files",
        ))
        return stats

    def _reconcile_extraction(self, manifest: BundleManifest, stats: Dict[str, int]) -> None:
        """Halt if the extraction did not account for every manifest entry.

        BFT_B103_EXTRACT_RECONCILIATION - ratified by George on 2026-08-04
        ("implement John's requested entry-count reconciliation assertion
        directly in the extract path to halt processing at runtime upon a
        mismatch").

        Every entry must leave through exactly one outcome: processed, skipped
        or errored. An entry that leaves through none of them is a file the
        operator asked for, was not told about, and does not have. Reporting
        that as a successful extraction is the silent-loss failure class this
        build exists to remove, so it raises instead.

        The write ledgers are cross-checked against the counters as well, so a
        counter that advances without a corresponding write is caught too.
        """
        expected = len(manifest.entries)
        accounted = stats["processed"] + stats["skipped"] + stats["errors"]

        if accounted != expected:
            raise ValidationError(
                "Extraction reconciliation FAILED: the manifest declares {0} "
                "entries but {1} were accounted for "
                "(processed={2}, skipped={3}, errors={4}). "
                "Refusing to report a partial extraction as complete.".format(
                    expected,
                    accounted,
                    stats["processed"],
                    stats["skipped"],
                    stats["errors"],
                )
            )

        if stats["processed"] != len(self.files_written) or stats["skipped"] != len(self.files_skipped):
            raise ValidationError(
                "Extraction reconciliation FAILED: counters disagree with the "
                "write ledgers (processed={0} vs written={1}, "
                "skipped={2} vs skipped-ledger={3}).".format(
                    stats["processed"],
                    len(self.files_written),
                    stats["skipped"],
                    len(self.files_skipped),
                )
            )

    def write_entry(self,
                   entry: BundleEntry,
                   output_path: Optional[Path] = None,
                   *,
                   apply_headers: Optional[bool] = None) -> Tuple[str, str]:
        """
        Write a single BundleEntry to the filesystem.

        Handles path creation, overwrite policies, binary decoding, text encoding,
        and optional header injection.

        Args:
            entry: The BundleEntry object containing file data.
            output_path: Optional specific absolute path to write to. If None,
                         calculated from entry.path relative to self.output_dir.
            apply_headers: Override instance `add_headers` setting for this specific
                           write operation. (Used internally by tests).

        Returns:
            Tuple: (status, target_path_string) where status is one of
                   "processed", "skipped".

        Raises:
            OverwriteError: If policy is 'prompt' and file exists.
            BundleWriteError: On decoding, encoding, or write failures.
            TypeError: If binary content is an unsupported type.
        """
        # Determine target path
        target = Path(output_path).resolve() if output_path else self._resolve_output_path(entry.path, self.output_dir)

        # Determine if headers should be applied for this write
        header_enabled = self.add_headers if apply_headers is None else apply_headers

        # Ensure parent directory exists (only if not dry run)
        if not self.dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)

        # Check for existing file or pending write collision
        file_exists = target.exists() or target in self.pending_writes

        # Apply overwrite policy
        if file_exists:
            # FIX: Compare self.overwrite_policy (string) to Enum.value (string)
            if self.overwrite_policy == OverwritePolicy.PROMPT.value:
                raise OverwriteError(str(target))

            # FIX: Compare self.overwrite_policy (string) to Enum.value (string)
            elif self.overwrite_policy == OverwritePolicy.SKIP.value:
                self.files_skipped.append(target)
                return ("skipped", str(target))

            # FIX: Compare self.overwrite_policy (string) to Enum.value (string)
            elif self.overwrite_policy == OverwritePolicy.RENAME.value:
                original_target = target
                target = self._get_renamed_path(target)
                self.files_renamed[original_target] = target
                # Proceed to write to the new 'target' path

            # FIX: Compare self.overwrite_policy (string) to Enum.value (string)
            elif self.overwrite_policy == OverwritePolicy.OVERWRITE.value:
                # Proceed to write, overwriting the existing file
                pass

        # === Prepare content for writing ===
        final_content_to_write: Union[str, bytes]

        if entry.is_binary:
            # Handle binary content (expecting base64 string or bytes/bytearray)
            try:
                binary_data: bytes
                if isinstance(entry.content, str):
                    # Assume base64 string, decode it
                    binary_data = base64.b64decode(entry.content.strip(), validate=True)
                elif isinstance(entry.content, (bytes, bytearray)):
                    binary_data = bytes(entry.content)
                else:
                    raise TypeError(f"Unsupported binary content type: {type(entry.content)}")
                final_content_to_write = binary_data
            except (base64.binascii.Error, TypeError) as e:
                raise BundleWriteError(str(target), f"Binary decode failed: {e}")

        else:
            # Handle text content
            text_content = entry.content if isinstance(entry.content, str) else str(entry.content)

            # Inject header if enabled AND the format accepts a `#` comment.
            # BFT_B109_HEADER_ALLOWLIST: the second condition is Option B+. It is
            # what keeps `add_headers=True` safe as the shipped default.
            if header_enabled and accepts_hash_header(entry.path):
                repo_header = self._build_repo_header_block(entry)
                payload = insert_provenance_header(text_content, repo_header)
            else:
                payload = text_content

            final_content_to_write = payload

        # === Perform write operation (unless dry run) ===
        if not self.dry_run:
            try:
                if entry.is_binary:
                    # Write bytes directly
                    target.write_bytes(final_content_to_write) # type: ignore
                else:
                    # Write text with specified encoding and newline handling
                    # Determine encoding, default to utf-8
                    encoding = entry.encoding if entry.encoding and entry.encoding.lower() != "auto" else "utf-8"
                    # Handle BOM variants
                    if encoding.lower() in ("utf-8-bom", "utf8-bom", "utf-8_sig"):
                        encoding = "utf-8-sig"

                    # CRITICAL: Use newline='' to write exactly what's in memory.
                    # This prevents Python from translating \n to \r\n on Windows.
                    target.write_text(final_content_to_write, encoding=encoding, newline='', errors='replace') # type: ignore

            except LookupError:
                raise BundleWriteError(str(target), f"Unknown encoding: {entry.encoding}")
            except Exception as e:
                # Catch generic OS errors during write
                raise BundleWriteError(str(target), f"Filesystem write failed: {e}")

        # Track successful (or simulated) write
        self.files_written.append(target)
        self.pending_writes.add(target) # Mark this path as targeted

        return ("processed", str(target))

    def _get_renamed_path(self, original: Path) -> Path:
        """
        Generates a unique filename by appending '_N' before the suffix.
        Example: file.txt -> file_1.txt -> file_2.txt

        Checks both the filesystem and pending writes in the current operation
        to avoid collisions.
        """
        parent = original.parent
        stem = original.stem
        suffix = original.suffix

        counter = 1
        while True:
            # Construct candidate path: file_1.txt, file_2.txt, etc.
            candidate = parent / f"{stem}_{counter}{suffix}"

            # Check if this candidate path either exists on disk OR is already
            # targeted for writing in this same extraction operation.
            if not candidate.exists() and candidate not in self.pending_writes:
                return candidate # Found a unique name
            counter += 1

    def _resolve_output_path(self, relative_path_str: str, output_dir: Path) -> Path:
        """
        Resolves the bundle entry's relative path to an absolute path within
        the target output directory. Normalizes separators.
        """
        # Normalize to POSIX-style separators, remove leading slash if any
        normalized_rel_path = PurePosixPath(relative_path_str.replace('\\', '/').lstrip('/'))
        # Join with output directory and resolve to absolute path
        target_path = (output_dir / normalized_rel_path).resolve()
        return target_path

    def _validate_path(self, target_path: Path, base_dir: Path) -> None:
        """
        Ensures the resolved target path is safely contained within the base directory.
        Prevents path traversal attacks (e.g., writing outside the extraction folder).
        """
        resolved_target = target_path.resolve()
        resolved_base = base_dir.resolve()

        try:
            # Check if the target is relative to (inside) the base directory
            resolved_target.relative_to(resolved_base)
        except ValueError:
            # If relative_to fails, it means the path escapes the base directory
            raise PathTraversalError(
                str(target_path),
                f"Resolved path '{resolved_target}' would escape base directory '{resolved_base}'"
            )

    def _build_repo_header_block(self, entry: BundleEntry) -> str:
        """
        Constructs the canonical repository header block (per Team Directive v4).
        This header is injected into extracted TEXT files when add_headers=True.
        """
        # A bundle entry does not carry repository ownership metadata. Never
        # claim BFT's internal team/lifecycle for extracted third-party files.
        project_name = self.header_metadata.get("project", "Unspecified")
        version = __version__
        team = self.header_metadata.get("team", "Unspecified")
        lifecycle = self.header_metadata.get("lifecycle", "Unspecified")

        normalized_relpath = entry.path.replace("\\", "/")
        # Construct the header lines
        header_lines = [
            "# " + "=" * 76,
            f"# SOURCEFILE: {Path(entry.path).name}", # Just the filename
            f"# RELPATH: {Path(entry.path).as_posix()}", # Full relative path
            f"# PROJECT: {project_name}",
            f"# TEAM: {team}",
            f"# VERSION: {version}",
            f"# LIFECYCLE: {lifecycle}",
            "# DESCRIPTION:",
            "#   (Content extracted from bundle)",
            "# FIXES:",
            "#   (If applicable, list fixes related to this file)",
            "# " + "=" * 76,
            "" # Add a blank line after the header
        ]
        return "\n".join(header_lines)


class BundleCreator:
    """Creates bundles from source directories or files."""

    # FIX: Set default to ['**/*'] to align with test_create_creator_default
    DEFAULT_ALLOW_GLOBS: List[str] = ["**/*"]

    # Keep curated deny list per Team Directive v4 (safety)
    DEFAULT_DENY_GLOBS: List[str] = [
        # Version control
        "**/.git/**", "**/.svn/**", "**/.hg/**", "**/.bzr/**", "**/.DS_Store",
        # Python virtual environments and caches
        "**/.venv/**", "**/__pycache__/**", "**/*.pyc", "**/*.pyo", "**/*.pyd",
        # Build artifacts
        "**/build/**", "**/dist/**", "**/*.egg-info/**", "**/node_modules/**",
        # Common logs and temp files
        "*.log", "**/*.log", "*.tmp", "**/*.tmp", "*.bak", "**/*.bak",
        # Test caches
        "**/.pytest_cache/**", "**/.mypy_cache/**", "**/.coverage",
        # IDE/Editor specific
        "**/.vscode/**", "**/.idea/**", "*.sublime-project", "*.sublime-workspace",
        # OS specific
        "**/Thumbs.db",
        # Self-bundling protection
        "*.bundle", "*.bft" # Avoid bundling previous outputs
    ]

    def __init__(self,
                 allow_globs: Optional[List[str]] = None,
                 deny_globs: Optional[List[str]] = None,
                 max_file_mb: float = 10.0,
                 treat_binary_as_base64: bool = True):
        """
        Initialize BundleCreator.

        Args:
            allow_globs: Glob patterns for files to include. If None, defaults to
                         DEFAULT_ALLOW_GLOBS (['**/*']). If provided, replaces default.
            deny_globs: Glob patterns for files/directories to exclude. If None,
                        defaults to DEFAULT_DENY_GLOBS (curated list). If provided,
                        replaces default (does NOT merge).
            max_file_mb: Maximum individual file size in Megabytes.
            treat_binary_as_base64: If True, automatically detect binary files and
                                    encode their content as Base64. If False, raise
                                    an error if a binary file is encountered.
        """

        # FIX: Replace-on-provide, else use default.
        if allow_globs is None:
            self.allow_globs = self.DEFAULT_ALLOW_GLOBS.copy()
        else:
            # Take the provided list exactly
            self.allow_globs = allow_globs[:]

        # FIX: Replace-on-provide, else use default.
        # This satisfies test_create_creator_custom (which provides a list)
        # AND test_discover_excludes_common_directories (which uses default)
        if deny_globs is None:
            # Use the curated safety list
            self.deny_globs = self.DEFAULT_DENY_GLOBS.copy()
        else:
            # Take the provided list exactly
            self.deny_globs = deny_globs[:]

        # Validate max_file_mb
        if not isinstance(max_file_mb, (int, float)) or max_file_mb <= 0:
            raise ValueError("max_file_mb must be a positive number.")
        self.max_file_mb = max_file_mb
        self.treat_binary_as_base64 = treat_binary_as_base64

    def discover_files(self, source_path: Path, base_path: Optional[Path] = None,
                       progress: Optional[Callable] = None,
                       cancel: Optional[CancelCheck] = None) -> List[Path]:
        """
        Discover files using glob filtering, starting from source_path.

        Args:
            source_path: The directory or single file to start scanning from.
            base_path: Optional. The root directory relative to which bundle paths
                       should be calculated. Defaults to source_path if source_path
                       is a directory, or source_path.parent if source_path is a file.

        Returns:
            A sorted list of unique, absolute Path objects for files to be included.

        Raises:
            BundleWriteError: If source_path does not exist.
        """
        # Dynamically import GlobFilter here if it's in a separate module
        try:
            from core.validators import GlobFilter
        except ImportError:
            # Fallback or raise if validators module isn't available
            raise ImportError("Could not import GlobFilter from core.validators. Ensure it exists.")

        # Keep a file alias's selected name. Resolving it here silently changes
        # both the filtering path and the name that will be put in the bundle.
        source_path = Path(os.path.abspath(source_path))
        if not source_path.exists():
            raise BundleWriteError(str(source_path), "Source path does not exist")

        # Determine the base path for relative path calculations
        if base_path:
            base = Path(os.path.abspath(base_path))
        elif source_path.is_dir():
            base = source_path
        else: # source_path is a file
            base = source_path.parent

        # Handle the case where a single file is provided
        if source_path.is_file():
            glob_filter = GlobFilter(
                allow_patterns=self.allow_globs,
                deny_patterns=self.deny_globs
            )
            # Calculate relative path for filtering
            try:
                rel_path_for_filter = str(source_path.relative_to(base)).replace("\\", "/")
            except ValueError:
                # If file is outside base somehow, use filename
                rel_path_for_filter = source_path.name

            # Apply filter and return if included
            if glob_filter.should_include(rel_path_for_filter):
                return [source_path]
            else:
                return [] # Excluded by filters

        # Handle directory scanning
        glob_filter = GlobFilter(
            allow_patterns=self.allow_globs,
            deny_patterns=self.deny_globs
        )

        # Use a set to automatically handle potential duplicates from various sources
        discovered_files: Set[Path] = set()

        # Build 106: discovery has no total until it finishes, so it reports an
        # indeterminate rising count. This is the event stream therm needs to
        # show more than a bare spinner during a long walk.
        emit(progress, OperationProgress(
            operation=OP_BUNDLE, phase=PHASE_DISCOVER, current=0, total=None,
            unit="files", message=f"Scanning {source_path}",
        ))

        # Build 110 (PERF-BFT-001): walk with os.walk so denied directories can
        # be pruned before descent. rglob("*") offers no such hook, so every
        # node under a denied tree was visited and then discarded - 16,685 of
        # 19,164 nodes on a routine source tree, all inside .venv, which the
        # deny list already excluded. The prune set is derived from the deny
        # patterns themselves, so nothing is skipped that was not already being
        # filtered out and the resulting file set is unchanged.
        pruned_dirs = prunable_dir_names(self.deny_globs)
        scanned = 0
        # None means "nothing emitted yet", which forces the first file to
        # report immediately rather than after a silent 100ms, and guarantees a
        # scan event even on a tree small enough to finish inside one interval.
        # Priming this by subtracting the interval from monotonic() does not
        # work: monotonic() returns a large float, so t - (t - 0.10) evaluates
        # to 0.09999999998 and the first comparison silently fails.
        last_emit: Optional[float] = None
        base_str = str(base)

        for walk_root, walk_dirs, walk_files in os.walk(source_path):
            # In-place mutation is what tells os.walk not to descend.
            walk_dirs[:] = [d for d in walk_dirs if d not in pruned_dirs]

            # BFT_B112_CANCEL_DISCOVER. Polled per directory rather than per
            # file: os.walk yields a whole directory at a time, and a scan of a
            # large tree spends most of its time inside this loop.
            if is_cancelled(cancel):
                raise OperationCancelled(
                    operation=OP_BUNDLE, phase=PHASE_DISCOVER,
                    completed=len(discovered_files), total=None,
                )

            for filename in walk_files:
                scanned += 1
                full_path = os.path.join(walk_root, filename)

                # Build 110 (PERF-BFT-002): relpath is string work; resolve()
                # is a syscall that cost 44% of discovery when spent on files
                # about to be discarded. Keep selected names through discovery;
                # target resolution and containment belong to the read step.
                try:
                    rel_path_for_filter = os.path.relpath(full_path, base_str).replace("\\", "/")
                except ValueError:
                    # Different drive on Windows - outside the base context.
                    continue
                if rel_path_for_filter.startswith(".."):
                    # Outside the base directory context, skip it.
                    continue

                if glob_filter.should_include(rel_path_for_filter):
                    discovered_files.add(Path(os.path.abspath(full_path)))

                # Build 110 (PERF-BFT-002): emit on files *scanned*, not files
                # *matched*. Emitting only on a match meant a dense excluded
                # subtree produced no events at all - a measured 13.15s of
                # silence that read as a frozen UI. Throttled because emit()
                # calls the sink synchronously with no rate limit of its own.
                now = time.monotonic()
                if last_emit is None or now - last_emit >= _DISCOVER_EMIT_INTERVAL_S:
                    emit(progress, OperationProgress(
                        operation=OP_BUNDLE, phase=PHASE_DISCOVER,
                        current=len(discovered_files), total=None, unit="files",
                        message=(f"Scanning {os.path.relpath(walk_root, base_str)} - "
                                 f"{len(discovered_files):,} included / {scanned:,} scanned"),
                    ))
                    last_emit = now

        # Return a sorted list for deterministic output
        found = sorted(list(discovered_files))
        # The count is known only now, so the closing event is determinate.
        emit(progress, OperationProgress(
            operation=OP_BUNDLE, phase=PHASE_DISCOVER,
            current=len(found), total=len(found), unit="files",
            message=f"Discovered {len(found)} files",
        ))
        return found

    def create_manifest(self,
                       files: List[Path],
                       base_path: Path,
                       profile_name: str,
                       progress: Optional[Callable] = None,
                       cancel: Optional[CancelCheck] = None,
                       operation: str = OP_BUNDLE,
                       content_reader: Optional[
                           Callable[[str], bytes]] = None) -> BundleManifest:
        """
        Create a BundleManifest object from a list of discovered file paths.

        Reads each file, determines if it's binary or text, detects EOL style,
        and creates BundleEntry objects.

        Args:
            files: List of absolute Path objects for files to include.
            base_path: The absolute Path object representing the project root,
                       used to calculate relative paths for the bundle entries.
            profile_name: The name of the bundle profile being used (e.g., 'plain_marker').

        Returns:
            A BundleManifest object populated with BundleEntry objects.

        Raises:
            FileSizeError: If any file exceeds self.max_file_mb.
            BundleWriteError: If binary handling is disabled and a binary file is found,
                              or if there are file reading errors.
            BundleWriteError: If a file or its target is outside base_path.
        """
        entries: List[BundleEntry] = []
        skipped_entries: List[Dict[str, object]] = []
        absolute_base_path = Path(os.path.abspath(base_path))
        resolved_base_path = absolute_base_path.resolve()
        total_files = len(files)

        emit(progress, OperationProgress(
            operation=operation, phase=PHASE_READ,
            current=0, total=total_files, unit="files",
            message=f"Preparing to read {total_files} files",
        ))

        for _read_index, file_path in enumerate(files, start=1):
            # BFT_B112_CANCEL_READ. Before the read, so a cancel never leaves a
            # partially-read file in the manifest.
            raise_if_cancelled(
                cancel, operation=operation, phase=PHASE_READ,
                completed=len(entries), total=total_files,
            )
            selected_path = Path(os.path.abspath(file_path))
            # A framework alias and its target are distinct planned entries.
            # Store the selected name, but verify and read the resolved target.
            # Using the target for both made Mac framework aliases collide.
            try:
                try:
                    relative = selected_path.relative_to(absolute_base_path)
                except ValueError:
                    # Callers may already have canonicalized a symlinked root.
                    relative = selected_path.relative_to(resolved_base_path)
                abs_file_path = selected_path.resolve()
                abs_file_path.relative_to(resolved_base_path)
            except ValueError:
                raise BundleWriteError(
                    str(selected_path),
                    f"File or link target is outside the specified base path '{resolved_base_path}'",
                ) from None
            relative_path_str = relative.as_posix()

            # Check file size against the limit
            #
            # Build 110 (UX-BFT-001, ARCH-RULING-2026-08-24-01 §3.2): exceeding
            # max_file_mb is a soft exclusion, not a fatal error. Raising here
            # aborted the whole manifest, so a single oversized asset made
            # every other discovered file unbundlable and blanked the GUI
            # preview. The file is now recorded and skipped; the bundle
            # proceeds with everything that fits.
            try:
                size_bytes = abs_file_path.stat().st_size
                size_mb = size_bytes / (1024 * 1024)
                if size_mb > self.max_file_mb:
                    skipped_entries.append({
                        "path": relative_path_str,
                        "reason": "oversize",
                        "size_mb": round(size_mb, 2),
                        "limit_mb": float(self.max_file_mb),
                    })
                    logging.info(
                        "Skipping oversized file (%.2f MB > %.2f MB limit): %s",
                        size_mb, self.max_file_mb, relative_path_str,
                    )
                    continue
            except FileNotFoundError:
                 # File might have been deleted between discovery and processing
                 logging.warning(f"File not found during size check, skipping: {abs_file_path}")
                 continue
            except OSError as e:
                 logging.warning(f"Could not stat file, skipping: {abs_file_path} ({e})")
                 continue


            # Read file content and create BundleEntry. Repository mode passes
            # a plan-bound reader supplied by the VCS Tool adapter; ordinary
            # filesystem mode retains the historical direct read.
            try:
                if content_reader is None:
                    entry = self._read_file_to_entry(
                        abs_file_path, relative_path_str)
                else:
                    source_bytes = content_reader(relative_path_str)
                    if not isinstance(source_bytes, bytes):
                        raise BundleWriteError(
                            relative_path_str,
                            "Repository content reader returned a non-bytes payload.",
                        )
                    entry = self._bytes_to_entry(
                        source_bytes, relative_path_str)
                # The emitted size describes the bytes actually consumed, not
                # an earlier stat that may have raced with the read.
                entry.file_size_bytes = (
                    len(source_bytes) if content_reader is not None
                    else size_bytes
                )
                entries.append(entry)
                # Completion is reported only after the source bytes have been
                # read and classified. Build 123 emitted this before read_bytes,
                # which allowed the GUI to display 100% while the last read and
                # every later safety/publication phase were still outstanding.
                emit(progress, OperationProgress(
                    operation=operation, phase=PHASE_READ,
                    current=_read_index, total=total_files, unit="files",
                    message=relative_path_str,
                ))
            except BundleFileToolError as e:
                # Propagate errors related to binary handling policy
                raise e
            except Exception as e:
                # Catch other file reading errors (permissions, etc.)
                logging.error(f"Failed to read file '{abs_file_path}': {e}", exc_info=True)
                # Optionally, raise BundleWriteError or just skip the file
                # raise BundleWriteError(relative_path_str, f"File read failed: {e}")
                continue # Skip file on error

        # Create the final manifest object
        return BundleManifest(
            entries=entries,
            profile=profile_name,
            metadata={
                "created": datetime.now().isoformat(),
                "source_path": str(resolved_base_path),
                "file_count": len(entries),
                "skipped_count": len(skipped_entries),
            },
            skipped_entries=skipped_entries,
        )

    def _read_file_to_entry(self, file_path: Path, relative_path: str) -> BundleEntry:
        """
        Read a source file once, classify it losslessly, and preserve its EOLs.

        Classification uses the complete byte stream. Sampling can split a
        valid UTF-8 code point or miss invalid bytes beyond the sample window,
        and ``Path.read_text`` applies universal-newline translation before EOL
        metadata can be recorded. Both behaviours violate byte fidelity.
        """
        try:
            source_bytes = file_path.read_bytes()
        except OSError as e:
            raise BundleWriteError(
                str(relative_path),
                f"Failed to read source file: {e}",
            ) from e

        return self._bytes_to_entry(source_bytes, relative_path)

    def _bytes_to_entry(self, source_bytes: bytes,
                        relative_path: str) -> BundleEntry:
        """Classify already-read source bytes without reopening the path."""

        decoded: Optional[str] = None
        if b"\x00" not in source_bytes:
            try:
                decoded = source_bytes.decode("utf-8", errors="strict")
            except UnicodeDecodeError:
                decoded = None

        is_binary = decoded is None
        if is_binary:
            if not self.treat_binary_as_base64:
                raise BundleWriteError(
                    str(relative_path),
                    "Binary file or non-UTF-8 file found but binary handling is disabled.",
                )
            content = base64.b64encode(source_bytes).decode("ascii")
            encoding = "base64"
            eol_style = "n/a"
        else:
            content = decoded
            encoding = "utf-8"
            eol_style = self._detect_eol(content)

        # Create the BundleEntry object
        return BundleEntry(
            path=relative_path,
            content=content,
            is_binary=is_binary,
            encoding=encoding,
            eol_style=eol_style,
            # file_size_bytes is added in create_manifest after stat
        )

    @staticmethod
    def _detect_eol(text: str) -> str:
        """
        Detects the predominant end-of-line style from a string.
        Handles LF, CRLF, CR, and MIXED cases robustly.
        Defaults to LF if no line endings are found.
        """
        counts = {'LF': 0, 'CRLF': 0, 'CR': 0}
        # Use finditer for efficiency on large strings
        crlf_indices = {m.start() for m in re.finditer(r'\r\n', text)}
        lf_indices = {m.start() for m in re.finditer(r'\n', text)}
        cr_indices = {m.start() for m in re.finditer(r'\r', text)}

        counts['CRLF'] = len(crlf_indices)
        # Count LFs that are NOT part of a CRLF
        counts['LF'] = len(lf_indices - {i + 1 for i in crlf_indices if i + 1 in lf_indices})
        # Count CRs that are NOT part of a CRLF
        counts['CR'] = len(cr_indices - crlf_indices)

        # Determine predominant or mixed
        present_styles = [style for style, count in counts.items() if count > 0]

        if len(present_styles) > 1:
            return "MIXED"
        elif len(present_styles) == 1:
            return present_styles[0]
        else:
            # No line endings found, default to LF (common for single-line files)
            return "LF"
