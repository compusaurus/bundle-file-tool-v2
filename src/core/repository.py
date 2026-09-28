"""Read-only repository contracts used by BFT integration.

This module deliberately does not import Git, ``vcs_tool``, or a subprocess
provider.  BFT consumes small repository-reader protocols and remains the
authority for selection, bundle creation, and extraction.  In repository
source mode the adapter also supplies plan-bound source bytes; provider
internals never cross this seam.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Dict, Optional, Protocol, Sequence, Tuple

from core.exceptions import BundleFileToolError
from core.selection import SelectionPlan, State, normalise


class RepositoryIntegrationError(BundleFileToolError):
    """The requested repository-backed operation cannot proceed safely."""


class RepositorySourceMode(str, Enum):
    """How repository evidence participates in source selection."""

    FILESYSTEM = "filesystem"
    TRACKED = "tracked"


@dataclass(frozen=True)
class RepositoryStatus:
    """The local repository identity needed by BFT.

    Paths are intentionally local-only evidence.  They are never written into
    a bundle transport header or portable selection report.
    """

    requested_root: Path
    repository_root: Optional[Path]
    is_repository: bool
    is_clean: Optional[bool]
    provider_id: str = "unknown"
    provider_version: Optional[str] = None
    warnings: Tuple[str, ...] = ()


@dataclass(frozen=True)
class RepositoryFile:
    """One repository-relative path and its mutually exclusive class."""

    path: str
    tracked: bool = False
    untracked: bool = False
    ignored: bool = False
    index_state: str = "none"
    worktree_state: str = "none"

    def __post_init__(self) -> None:
        canonical = _safe_relative(self.path)
        object.__setattr__(self, "path", canonical)
        classes = sum((self.tracked, self.untracked, self.ignored))
        if classes != 1:
            raise RepositoryIntegrationError(
                f"Repository path {canonical!r} must be exactly one of "
                "tracked, untracked, or ignored."
            )

    @property
    def classification(self) -> str:
        if self.tracked:
            return "tracked"
        if self.untracked:
            return "untracked"
        return "ignored"


@dataclass(frozen=True)
class RepositoryInventory:
    """Deterministic local inventory returned by a repository reader."""

    repository_root: Path
    files: Tuple[RepositoryFile, ...]
    provider_id: str = "unknown"
    provider_version: Optional[str] = None
    warnings: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        ordered = tuple(sorted(self.files, key=lambda item: item.path.encode("utf-8")))
        paths = [item.path for item in ordered]
        if len(paths) != len(set(paths)):
            raise RepositoryIntegrationError("Repository inventory contains duplicate paths.")
        object.__setattr__(self, "files", ordered)

    def by_path(self) -> Dict[str, RepositoryFile]:
        return {item.path: item for item in self.files}

    def tracked_paths(self) -> frozenset[str]:
        return frozenset(item.path for item in self.files if item.tracked)

    def digest(self) -> str:
        """Hash selection-relevant state without machine-specific paths."""
        payload = [
            {
                "path": item.path,
                "tracked": item.tracked,
                "untracked": item.untracked,
                "ignored": item.ignored,
                "index_state": item.index_state,
                "worktree_state": item.worktree_state,
            }
            for item in self.files
        ]
        encoded = json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


class RepositoryReader(Protocol):
    """BFT-facing read-only subset of the VCS Tool adapter."""

    def inspect(self, root: Path, *, allowed_root: Path) -> RepositoryStatus: ...

    def list_files(
        self,
        root: Path,
        *,
        allowed_root: Path,
        include_tracked: bool,
        include_untracked: bool,
        include_ignored: bool,
    ) -> RepositoryInventory: ...

    def open_read_session(
        self,
        root: Path,
        *,
        allowed_root: Path,
        max_file_bytes: int,
    ) -> "RepositoryReadSession": ...


class RepositoryReadSession(Protocol):
    """Plan-bound repository source used for one BFT read phase.

    The inventory must describe the same session that authorizes
    :meth:`read_bytes`.  Implementations reject a read when its bytes no longer
    match that session's plan.
    """

    inventory: RepositoryInventory
    plan_manifest_digest: str

    def read_bytes(self, path: str) -> bytes: ...

    def close(self) -> None: ...

    def __enter__(self) -> "RepositoryReadSession": ...

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None: ...


@dataclass(frozen=True)
class RepositorySourceEvidence:
    """Repository snapshot bound to one approved BFT selection plan."""

    mode: RepositorySourceMode
    status: RepositoryStatus
    inventory: RepositoryInventory
    inventory_digest: str

    def to_dict(self) -> Dict[str, object]:
        """Portable plan-report projection; excludes local absolute paths."""
        return {
            "mode": self.mode.value,
            "provider_id": self.status.provider_id,
            "provider_version": self.status.provider_version,
            "is_repository": self.status.is_repository,
            "is_clean": self.status.is_clean,
            "tracked_count": len(self.inventory.tracked_paths()),
            "inventory_digest": self.inventory_digest,
            "warnings": list(self.status.warnings + self.inventory.warnings),
        }


@dataclass(frozen=True)
class RepositoryExtractionPolicy:
    """Explicit authorization policy for extraction into a repository root."""

    require_clean: bool = True
    allow_tracked_overwrite: bool = False
    allow_untracked_overwrite: bool = False
    allow_ignored_overwrite: bool = False
    allow_other_overwrite: bool = False


@dataclass(frozen=True)
class RepositoryCollision:
    path: str
    classification: str
    allowed: bool

    def to_dict(self) -> Dict[str, object]:
        return {
            "path": self.path,
            "classification": self.classification,
            "allowed": self.allowed,
        }


@dataclass(frozen=True)
class RepositoryExtractionPreflight:
    """Read-only decision made before BFT opens any extraction output."""

    allowed: bool
    status: RepositoryStatus
    inventory: RepositoryInventory
    collisions: Tuple[RepositoryCollision, ...] = ()
    reasons: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, object]:
        return {
            "allowed": self.allowed,
            "provider_id": self.status.provider_id,
            "is_repository": self.status.is_repository,
            "is_clean": self.status.is_clean,
            "collisions": [item.to_dict() for item in self.collisions],
            "reasons": list(self.reasons),
        }

    def require_allowed(self) -> None:
        if self.allowed:
            return
        detail = "; ".join(self.reasons) or "repository preflight failed"
        raise RepositoryIntegrationError(f"Repository extraction is blocked: {detail}")


def build_source_evidence(
    reader: RepositoryReader, root: Path, mode: RepositorySourceMode
) -> RepositorySourceEvidence:
    """Inspect and inventory a repository for a BFT source plan."""
    resolved = Path(root).resolve()
    if mode is RepositorySourceMode.FILESYSTEM:
        raise RepositoryIntegrationError("Filesystem mode does not require repository evidence.")
    status = reader.inspect(resolved, allowed_root=resolved)
    _require_exact_repository_root(status, resolved)
    inventory = reader.list_files(
        resolved,
        allowed_root=resolved,
        include_tracked=True,
        include_untracked=False,
        include_ignored=False,
    )
    _require_inventory_root(inventory, resolved)
    return RepositorySourceEvidence(
        mode=mode,
        status=status,
        inventory=inventory,
        inventory_digest=inventory.digest(),
    )


def filter_plan_to_repository(
    plan: SelectionPlan, evidence: Optional[RepositorySourceEvidence]
) -> SelectionPlan:
    """Narrow included paths without overriding any BFT decision.

    Repository membership is an intersection after BFT's rule and emission
    safety decisions.  It is deliberately not represented as another rule
    layer: VCS cannot include, unblock, or make an unknown path safe.
    """
    if evidence is None or evidence.mode is RepositorySourceMode.FILESYSTEM:
        return plan
    tracked = evidence.inventory.tracked_paths()
    decisions = []
    for decision in plan.decisions:
        if decision.state is State.INCLUDED and decision.path not in tracked:
            decisions.append(
                replace(
                    decision,
                    state=State.EXCLUDED,
                    winning_rule="repository:tracked-intersection",
                    winning_layer=None,
                    code="EXCLUDED_NOT_TRACKED",
                    detail=(
                        "Excluded by the read-only repository inventory after "
                        "BFT safety and selection evaluation."
                    ),
                    confirm_required=False,
                    group="",
                )
            )
        else:
            decisions.append(decision)
    warning = (
        "Repository tracked mode intersected the BFT-safe plan with the "
        "approved tracked-file inventory."
    )
    warnings = tuple(plan.warnings)
    if warning not in warnings:
        warnings += (warning,)
    return replace(plan, decisions=tuple(decisions), warnings=warnings)


def build_extraction_preflight(
    reader: RepositoryReader,
    output_dir: Path,
    manifest_paths: Sequence[str],
    policy: RepositoryExtractionPolicy,
) -> RepositoryExtractionPreflight:
    """Classify existing targets and apply an explicit extraction policy."""
    root = Path(output_dir).resolve()
    status = reader.inspect(root, allowed_root=root)
    reasons = []
    valid_repository = True
    try:
        _require_exact_repository_root(status, root)
    except RepositoryIntegrationError as error:
        reasons.append(str(error))
        valid_repository = False

    if valid_repository:
        inventory = reader.list_files(
            root,
            allowed_root=root,
            include_tracked=True,
            include_untracked=True,
            include_ignored=True,
        )
        try:
            _require_inventory_root(inventory, root)
        except RepositoryIntegrationError as error:
            reasons.append(str(error))
    else:
        inventory = RepositoryInventory(
            repository_root=root,
            files=(),
            provider_id=status.provider_id,
            provider_version=status.provider_version,
        )

    if policy.require_clean and status.is_clean is not True:
        state = "dirty" if status.is_clean is False else "unknown"
        reasons.append(f"repository worktree cleanliness is {state}")

    known = inventory.by_path()
    collisions = []
    for raw_path in manifest_paths:
        relative = _safe_relative(raw_path)
        target = root.joinpath(*PurePosixPath(relative).parts)
        if not os.path.lexists(target):
            continue
        record = known.get(relative)
        classification = record.classification if record else "other"
        allowed = {
            "tracked": policy.allow_tracked_overwrite,
            "untracked": policy.allow_untracked_overwrite,
            "ignored": policy.allow_ignored_overwrite,
            "other": policy.allow_other_overwrite,
        }[classification]
        collisions.append(
            RepositoryCollision(
                path=relative,
                classification=classification,
                allowed=allowed,
            )
        )
        if not allowed:
            reasons.append(
                f"{classification} destination exists and overwrite was not "
                f"approved: {relative}"
            )

    return RepositoryExtractionPreflight(
        allowed=not reasons,
        status=status,
        inventory=inventory,
        collisions=tuple(collisions),
        reasons=tuple(reasons),
    )


def _safe_relative(path: str) -> str:
    canonical = normalise(path)
    candidate = PurePosixPath(canonical)
    windows = PureWindowsPath(canonical)
    if (
        not canonical
        or candidate.is_absolute()
        or windows.is_absolute()
        or bool(windows.drive)
        or any(part in ("", ".", "..") for part in candidate.parts)
    ):
        raise RepositoryIntegrationError(
            f"Repository inventory path is not safely relative: {path!r}"
        )
    return canonical


def _require_exact_repository_root(status: RepositoryStatus, requested_root: Path) -> None:
    if not status.is_repository or status.repository_root is None:
        raise RepositoryIntegrationError("The selected directory is not a repository root.")
    requested = Path(requested_root).resolve()
    reported_request = Path(status.requested_root).resolve()
    reported_root = Path(status.repository_root).resolve()
    if reported_request != requested or reported_root != requested:
        raise RepositoryIntegrationError(
            "The prototype requires the selected directory to be the exact " "repository root."
        )


def _require_inventory_root(inventory: RepositoryInventory, requested_root: Path) -> None:
    if Path(inventory.repository_root).resolve() != Path(requested_root).resolve():
        raise RepositoryIntegrationError(
            "Repository inventory root does not match the selected directory."
        )
