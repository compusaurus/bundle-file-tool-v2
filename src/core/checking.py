"""Structured integrity results shared by CLI, Tk, and the future web UI.

Checking is deliberately data, not presentation.  Adapters can render the
same findings as a table, terminal report, or JSON response without
reimplementing any safety decision.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any, Dict, Iterable, Optional, Tuple
import re
import unicodedata

from core.bundle_integrity import bundle_integrity_report
from core.cancellation import CancelCheck, raise_if_cancelled
from core.models import BundleManifest
from core.progress import (
    OP_CHECK,
    PHASE_INTEGRITY,
    PHASE_VERIFY,
    ProgressSink,
    ThrottledReporter,
)


SEVERITY_INFO = "info"
SEVERITY_WARNING = "warning"
SEVERITY_ERROR = "error"

SUBJECT_SELECTION = "selection"
SUBJECT_BUNDLE = "bundle"
SUBJECT_OUTPUT = "output"
CHECK_RESULT_SCHEMA = "bft.check-result.v1"


@dataclass(frozen=True)
class CheckFinding:
    """One explainable result produced by a check."""

    code: str
    severity: str
    summary: str
    path: str = ""
    detail: str = ""
    remediation: str = ""
    blocking: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "summary": self.summary,
            "path": self.path,
            "detail": self.detail,
            "remediation": self.remediation,
            "blocking": self.blocking,
        }


@dataclass(frozen=True)
class CheckResult:
    """Serializable checked/blocked/ready state for one subject."""

    subject: str
    label: str
    valid: bool
    profile: Optional[str]
    file_count: int
    total_bytes: int = 0
    findings: Tuple[CheckFinding, ...] = field(default_factory=tuple)
    generation: Optional[int] = None

    @property
    def blockers(self) -> Tuple[CheckFinding, ...]:
        return tuple(item for item in self.findings if item.blocking)

    @property
    def warnings(self) -> Tuple[CheckFinding, ...]:
        return tuple(
            item for item in self.findings
            if item.severity == SEVERITY_WARNING
        )

    @property
    def status(self) -> str:
        if self.blockers or not self.valid:
            return "blocked"
        if self.warnings:
            return "warnings"
        return "passed"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": CHECK_RESULT_SCHEMA,
            "subject": self.subject,
            "label": self.label,
            "valid": self.valid,
            "status": self.status,
            "profile": self.profile,
            "file_count": self.file_count,
            "total_bytes": self.total_bytes,
            "generation": self.generation,
            "blocking_count": len(self.blockers),
            "warning_count": len(self.warnings),
            "findings": [item.to_dict() for item in self.findings],
        }


_WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:")


def _unsafe_transport_path(path: str) -> bool:
    """Whether a manifest path is unsafe before an output root is chosen."""
    value = str(path or "").replace("\\", "/")
    if not value or "\x00" in value:
        return True
    pure = PurePosixPath(value)
    return bool(
        pure.is_absolute()
        or value.startswith("//")
        or _WINDOWS_DRIVE_RE.match(value)
        or any(part == ".." for part in pure.parts)
    )


def _normalised_key(path: str) -> str:
    return unicodedata.normalize(
        "NFC", str(path or "").replace("\\", "/")
    ).casefold()


def _duplicate_portable_paths(paths: Iterable[str]) -> Dict[str, Tuple[str, ...]]:
    grouped: Dict[str, list] = {}
    for path in paths:
        grouped.setdefault(_normalised_key(path), []).append(path)
    return {
        key: tuple(values)
        for key, values in grouped.items()
        if len(values) > 1
    }


def check_manifest(
    manifest: BundleManifest,
    *,
    subject: str = SUBJECT_BUNDLE,
    label: str = "bundle",
    generation: Optional[int] = None,
    operation: str = OP_CHECK,
    progress: Optional[ProgressSink] = None,
    cancel: Optional[CancelCheck] = None,
) -> CheckResult:
    """Check an already parsed/read manifest without parsing it again."""
    integrity = bundle_integrity_report(
        manifest,
        progress=progress,
        cancel=cancel,
        operation=operation,
    )
    findings = []

    for path, reason, marker_count in integrity["nested_bundle_entries"]:
        if reason == "content":
            detail = (
                f"The file opens as a complete bundle transport and contains "
                f"{marker_count} embedded '# FILE:' markers."
            )
            code = "NESTED_BUNDLE_CONTENT"
        else:
            detail = "The filename identifies a bundle or archive artifact."
            code = "NESTED_BUNDLE_PATH"
        findings.append(CheckFinding(
            code=code,
            severity=SEVERITY_ERROR,
            summary="Confirmed nested bundle artifact",
            path=path,
            detail=detail,
            remediation=(
                "Exclude this path, move the artifact outside the source, or "
                "include it only through a future opaque-content mode."
            ),
            blocking=True,
        ))

    for path, blocks in integrity["stale_header_entries"]:
        findings.append(CheckFinding(
            code="STALE_TRANSPORT_HEADER",
            severity=SEVERITY_WARNING,
            summary="Source file still carries an extraction header",
            path=path,
            detail=f"Found {blocks} leading transport block.",
            remediation="Review the file and remove the stale header if unintended.",
        ))

    verification = ThrottledReporter(
        progress,
        operation,
        PHASE_VERIFY,
        "entries",
        total=len(manifest.entries),
    )
    for position, entry in enumerate(manifest.entries, start=1):
        raise_if_cancelled(
            cancel,
            operation=operation,
            phase=PHASE_VERIFY,
            completed=position - 1,
            total=len(manifest.entries),
        )
        if _unsafe_transport_path(entry.path):
            findings.append(CheckFinding(
                code="UNSAFE_TRANSPORT_PATH",
                severity=SEVERITY_ERROR,
                summary="Entry path is unsafe for extraction",
                path=entry.path,
                detail="The entry is absolute, empty, or attempts parent traversal.",
                remediation="Regenerate the bundle with relative paths only.",
                blocking=True,
            ))
        if entry.checksum is not None and not entry.verify_checksum():
            findings.append(CheckFinding(
                code="CHECKSUM_MISMATCH",
                severity=SEVERITY_ERROR,
                summary="Entry checksum does not match its content",
                path=entry.path,
                remediation="Regenerate or reacquire the bundle before extraction.",
                blocking=True,
            ))
        verification.tick(
            position, message=f"Verifying entry safety: {entry.path}")
    verification.close(
        len(manifest.entries),
        message=f"Verified safety of {len(manifest.entries)} entries",
    )

    duplicates = _duplicate_portable_paths(entry.path for entry in manifest.entries)
    for paths in duplicates.values():
        findings.append(CheckFinding(
            code="PORTABLE_PATH_COLLISION",
            severity=SEVERITY_ERROR,
            summary="Entries collide on a case-insensitive or Unicode-normalized filesystem",
            path="; ".join(paths),
            remediation="Rename one of the entries before bundling.",
            blocking=True,
        ))

    if not manifest.entries:
        findings.append(CheckFinding(
            code="EMPTY_BUNDLE",
            severity=SEVERITY_WARNING,
            summary="Bundle contains no files",
            remediation="Confirm that the selected rules intentionally produced an empty bundle.",
        ))

    total_bytes = sum(
        entry.file_size_bytes
        for entry in manifest.entries
        if entry.file_size_bytes is not None
    )
    blockers = any(item.blocking for item in findings)
    return CheckResult(
        subject=subject,
        label=label,
        valid=not blockers,
        profile=manifest.profile,
        file_count=len(manifest.entries),
        total_bytes=total_bytes,
        findings=tuple(findings),
        generation=generation,
    )


def format_blocked_check(result: CheckResult) -> str:
    """Concise exception text for non-interactive callers."""
    lines = [
        f"Integrity check blocked {result.subject} '{result.label}'.",
        f"  files checked: {result.file_count}",
        f"  blocking findings: {len(result.blockers)}",
    ]
    for finding in result.blockers[:20]:
        suffix = f": {finding.path}" if finding.path else ""
        lines.append(f"    {finding.code}{suffix}")
    lines.append("Review the check findings and resolve every blocking item.")
    return "\n".join(lines)
