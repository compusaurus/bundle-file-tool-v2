# BFT_B114_METADATA_SCAN - metadata-first discovery with detector pruning
# ===================================================================================================
# SOURCEFILE: metadata_scan.py
# RELPATH: bundle_file_tool_v2/src/core/metadata_scan.py
# PROJECT: Bundle File Tool v2.2
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.114
# LIFECYCLE: Testing
# STATUS: Build 114 - WP3 - BFT_B114_METADATA_SCAN
# DESCRIPTION: Walks a source tree collecting metadata only. Opens no file.
# Relative Path: src/core/metadata_scan.py
# Purpose:
# independent_entry_point:
# ===================================================================================================
"""Collect what a plan needs, and nothing more.

`BFT_SELECTION_WORKSPACE_DESIGN_SPEC` §10.1 separates planning from reading:

    Scan metadata: normalized relative path, directory identity, size, mtime_ns,
    file family, and detector evidence.

This module is that scan. It opens no file, and the plan built from its output
can be re-evaluated on a checkbox click without touching the disk. That is the
whole reason a 4,000-path plan re-decides in 0.1 ms.

Pruning happens **before descent**. A directory that classifies as an
environment is recorded as a pruned root and never entered, so the 300 files
under `.venv312/Lib/site-packages` are never even statted. Build 113's harness
measures that as ~89% of the scan cost on a real tree.

WP5 will put a cached index in front of this. The seam is deliberate: this
returns plain immutable data, so a cache can memoise it without either side
knowing about the other.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from core.cancellation import CancelCheck, OperationCancelled, is_cancelled
from core.detectors import (
    DetectorFinding,
    DetectorLedger,
    DetectorResult,
    classify_directory,
)
from core.progress import (
    OP_BUNDLE,
    PHASE_DISCOVER,
    OperationProgress,
    emit,
)
from core.selection import normalise


@dataclass(frozen=True)
class PathMetadata:
    """Everything the selection engine needs about one file. No content."""

    path: str                      # normalised, relative to base
    size: int = 0
    mtime_ns: int = 0
    absolute: str = ""

    def as_candidate(self) -> Tuple[str, int]:
        """The (path, size) pair `SelectionEngine.plan` consumes."""
        return (self.path, self.size)


@dataclass
class ScanResult:
    """One metadata scan: candidates, what was pruned, and what went wrong."""

    entries: List[PathMetadata] = field(default_factory=list)
    ledger: DetectorLedger = field(default_factory=DetectorLedger)
    warnings: List[str] = field(default_factory=list)
    unknown: Dict[str, str] = field(default_factory=dict)
    scanned: int = 0

    def candidates(self) -> List[Tuple[str, int]]:
        return [entry.as_candidate() for entry in self.entries]

    def by_path(self) -> Dict[str, PathMetadata]:
        return {entry.path: entry for entry in self.entries}

    def pruned_roots(self) -> List[str]:
        return self.ledger.pruned_roots()


def scan_metadata(source: Path,
                  base_path: Optional[Path] = None,
                  *,
                  progress: Optional[Callable] = None,
                  cancel: Optional[CancelCheck] = None,
                  unprune: Sequence[str] = (),
                  prune_dir_names: Sequence[str] = (),
                  throttle_ms: int = 100) -> ScanResult:
    """Walk `source`, collecting metadata and pruning classified directories.

    Args:
        source: Directory (or single file) to scan.
        base_path: Root that relative paths are expressed against. Defaults to
            `source` for a directory, or its parent for a file.
        progress: Optional `OperationProgress` sink. Reports files *scanned*,
            not files matched - Build 110's lesson: an excluded subtree still
            has to move the bar or the UI looks hung.
        cancel: Optional cancellation predicate, polled per directory.
        unprune: Relative roots the operator has explicitly asked to descend
            into anyway, via `--include-root`. This is the only way a pruned
            subtree is entered, and it is a visible, costed choice.
        prune_dir_names: Bare directory names derived only from active
            whole-subtree deny rules (``**/NAME/**``). These can be skipped
            before descent without changing the selection result.
        throttle_ms: Minimum interval between progress events.

    Returns:
        A `ScanResult`. Unreadable directories become warnings and `Unknown`
        entries rather than silently empty results.

    Raises:
        OperationCancelled: if `cancel` reports a request between directories.
    """
    import time

    source = Path(source)
    if source.is_file():
        base = Path(base_path) if base_path else source.parent
        size, mtime_ns, error = _safe_stat_with_error(str(source))
        entry = PathMetadata(
            path=normalise(os.path.relpath(source, base)),
            size=size, mtime_ns=mtime_ns, absolute=str(source))
        result = ScanResult(entries=[entry], scanned=1)
        if error:
            result.unknown[entry.path] = error
            result.warnings.append(f"{entry.path}: {error}")
        return result

    base = Path(base_path) if base_path else source
    unpruned_roots = {normalise(root) for root in unprune}
    rule_pruned_names = {str(name) for name in prune_dir_names}
    result = ScanResult()
    last_emit = 0.0

    def record_walk_error(error: OSError) -> None:
        """Turn an unreadable directory into serializable plan evidence."""
        target = Path(getattr(error, "filename", None) or source)
        relative = normalise(os.path.relpath(target, base))
        if relative in ("", "."):
            relative = source.name or "<root>"
        reason = f"{type(error).__name__}: {error.strerror or error}"
        result.warnings.append(f"{relative}: {reason}")
        result.unknown[relative] = reason
        if relative not in {entry.path for entry in result.entries}:
            result.entries.append(PathMetadata(
                path=relative, absolute=str(target)))
            result.scanned += 1

    emit(progress, OperationProgress(
        operation=OP_BUNDLE, phase=PHASE_DISCOVER, current=0, total=None,
        unit="files", message=f"Scanning {source}"))

    for walk_root, walk_dirs, walk_files in os.walk(
            source, onerror=record_walk_error):
        if is_cancelled(cancel):
            raise OperationCancelled(
                operation=OP_BUNDLE, phase=PHASE_DISCOVER,
                completed=len(result.entries), total=None)

        keep: List[str] = []
        for name in sorted(walk_dirs):
            absolute = os.path.join(walk_root, name)
            relative = normalise(os.path.relpath(absolute, base))

            if relative in unpruned_roots:
                keep.append(name)                 # explicitly un-pruned
                continue

            # Prefer structural detector evidence when it independently proves
            # the directory family. A whole-subtree rule is the fallback for
            # ordinary generated directories such as BFT's tmp/out trees.
            finding = classify_directory(absolute, name)
            if finding.prunable:
                result.ledger.record(relative, finding)
                continue                          # do not descend
            if name in rule_pruned_names:
                result.ledger.record(relative, DetectorFinding(
                    result=DetectorResult.DETECTED,
                    family="selection-rule",
                    evidence=(f"**/{name}/**",),
                    code="PRUNED_BY_WHOLE_SUBTREE_RULE",
                ))
                continue
            result.ledger.record(relative, finding)
            keep.append(name)
        walk_dirs[:] = keep

        for name in sorted(walk_files):
            absolute = os.path.join(walk_root, name)
            relative = normalise(os.path.relpath(absolute, base))
            size, mtime_ns, error = _safe_stat_with_error(absolute)
            if error:
                result.unknown[relative] = error
                result.warnings.append(f"{relative}: {error}")
            result.entries.append(PathMetadata(path=relative, size=size,
                                               mtime_ns=mtime_ns,
                                               absolute=absolute))
            result.scanned += 1

            now = time.monotonic() * 1000
            if now - last_emit >= throttle_ms:
                last_emit = now
                emit(progress, OperationProgress(
                    operation=OP_BUNDLE, phase=PHASE_DISCOVER,
                    current=result.scanned, total=None, unit="files",
                    message=f"{len(result.entries)} indexed / {result.scanned} scanned"))

    result.entries.sort(key=lambda entry: entry.path)
    emit(progress, OperationProgress(
        operation=OP_BUNDLE, phase=PHASE_DISCOVER,
        current=len(result.entries), total=len(result.entries), unit="files",
        message=f"Indexed {len(result.entries)} files"))
    return result


def scan_subtree(root: Path, base_path: Path, **kwargs) -> ScanResult:
    """Targeted scan of one previously-pruned directory.

    Risk R1, the "ghost children" case. A pruned root is never walked, so an
    explicit child override or a GUI expand has nothing to show. Rather than
    weaken the pruning, the caller asks for this one subtree on demand and the
    result becomes a **new plan generation** - never a mutation of the old plan.
    """
    return scan_metadata(Path(root), Path(base_path), **kwargs)


def _safe_stat_with_error(path: str) -> Tuple[int, int, str]:
    """Size and mtime, or a reason. An unreadable file is Unknown, not absent."""
    try:
        info = os.stat(path)
        return info.st_size, getattr(info, "st_mtime_ns", 0), ""
    except OSError as error:
        return 0, 0, f"{type(error).__name__}: {error.strerror or error}"
