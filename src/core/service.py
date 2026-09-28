# BFT_B106_SERVICE_FACADE - one shared service beneath every interface
# ===================================================================================================
# SOURCEFILE: service.py
# RELPATH: bundle_file_tool_v2/src/core/service.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.106
# LIFECYCLE: Testing
# STATUS: Build 106 - BFT_B106_SERVICE_FACADE
# DESCRIPTION: BundleToolService - the WP2 facade the CLI, Tkinter and Web
#              adapters are all meant to sit on.
# Relative Path: src/core/service.py
# Purpose:
# independent_entry_point:
# ===================================================================================================
"""One service, three interfaces.

Build 100's mandatory scope (D-002) is a single `BundleToolService` with CLI,
Tkinter and Web adapters over it. Paul's Build 104 review recorded WP2 as **not
started**: the CLI still constructs the parser, writer, creator and registry
directly, so every interface re-derives the same orchestration and any two of
them can drift.

This module is that facade. Three rules shape it:

1. **It returns data, never renderer objects.** Results are plain dataclasses and
   progress arrives as `OperationProgress` events. A CLI maps those to therm, a
   Tkinter adapter queues them onto the UI thread, a web adapter serializes
   them. None of that belongs here.
2. **It imports no interface.** No `print`, no toolkit, no therm. The one place
   the old code leaked interface concerns into the core - diagnostics on stdout -
   was a Build 105 blocker.
3. **The safety gates are inside, not in the adapters.** Integrity checking and
   extract reconciliation run here, so no interface can skip them by
   constructing the pieces itself. That is the failure mode the facade exists to
   prevent.

Scope note: this build introduces the facade and its contract. Migrating the CLI
onto it is WP5 and a separate build, so the two changes can be reviewed and
rolled back independently.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field, replace
import math
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple, Union

import sys
import os
import stat
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.bundle_integrity import assert_bundle_clean
from core.checking import (
    CheckResult,
    SUBJECT_BUNDLE,
    SUBJECT_OUTPUT,
    SUBJECT_SELECTION,
    check_manifest as run_manifest_check,
    format_blocked_check,
)
from core.config import ConfigManager
from core.exceptions import (
    BundleFileToolError,
    BundleWriteError,
    PlanDriftError,
    ValidationError,
)
from core.models import BundleManifest
from core.parser import BundleParser, ProfileRegistry
from core.cancellation import CancelCheck, raise_if_cancelled
from core.progress import (
    OP_BUNDLE,
    OP_CHECK,
    OP_EXTRACT,
    OP_VALIDATE,
    PHASE_COMPLETE,
    PHASE_FINALIZE,
    PHASE_FORMAT,
    PHASE_PARSE,
    PHASE_VERIFY,
    PHASE_VERIFY_READ,
    PHASE_VERIFY_SOURCE,
    PHASE_WRITE,
    OperationProgress,
    ProgressSink,
    ThrottledReporter,
    emit,
)
from core.repository import (
    RepositoryExtractionPolicy,
    RepositoryExtractionPreflight,
    RepositoryIntegrationError,
    RepositoryReader,
    RepositorySourceEvidence,
    RepositorySourceMode,
    build_extraction_preflight,
    build_source_evidence,
    filter_plan_to_repository,
)
from core.writer import BundleCreator, BundleWriter, prunable_dir_names

# Build 114 (WP3). The selection workspace beneath the facade. Every one of
# these is I/O-free except metadata_scan, which stats and never opens.
from core.metadata_scan import ScanResult, scan_metadata
from core.rule_sources import (
    RuleSourceError,
    RuleStack,
    available_presets,
    resolve_base_action,
    cli_rules,
    load_rules_file,
    parse_group_specs,
    preset_rules,
    session_rules,
)
from core.selection import (
    Action,
    ChainEntry,
    Layer,
    SelectionRule,
    matches,
    rule_stack_digest,
    SelectionEngine,
    SelectionGroup,
    SelectionPlan,
    State,
    base_action_for,
    normalise,
    rule_source_digest,
    rules_from_globs,
)


# ===================================================================================================
# Results - plain data, safe to serialize or hand to any adapter
# ===================================================================================================

_MIB = 1024 * 1024
_LARGE_PLAN_FILES = 10_000
_LARGE_PLAN_BYTES = 128 * _MIB
_EXTREME_PLAN_FILES = 50_000
_EXTREME_PLAN_BYTES = 512 * _MIB
_ESTIMATED_ENTRY_OVERHEAD = 512
_INLINE_RESULT_LIMIT = 16 * _MIB
_COPY_CHUNK_BYTES = 1024 * 1024


@dataclass(frozen=True)
class PlanEstimate:
    """Conservative capacity estimate derived without opening source files."""

    file_count: int
    raw_bytes: int
    output_bytes: int
    temporary_bytes: int
    peak_memory_bytes: int
    level: str

    @property
    def requires_confirmation(self) -> bool:
        return self.level in {"large", "extreme"}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_count": self.file_count,
            "raw_bytes": self.raw_bytes,
            "output_bytes": self.output_bytes,
            "temporary_bytes": self.temporary_bytes,
            "peak_memory_bytes": self.peak_memory_bytes,
            "level": self.level,
            "requires_confirmation": self.requires_confirmation,
        }

@dataclass(frozen=True)
class BundleResult:
    """The outcome of building a bundle."""

    text: str
    manifest: BundleManifest
    file_count: int
    profile: str
    output_path: Optional[Path] = None
    artifact_path: Optional[Path] = None
    byte_count: int = 0
    temporary_artifact: bool = False

    def read_text(self) -> str:
        """Return artifact text, loading the spool only when explicitly asked."""
        if self.text:
            return self.text
        if self.artifact_path is None:
            return ""
        with Path(self.artifact_path).open(
                "r", encoding="utf-8", newline="") as source:
            return source.read()

    def write_to(self, binary_stream) -> int:
        """Stream the exact UTF-8 artifact to a binary output."""
        if self.artifact_path is not None:
            written = 0
            with Path(self.artifact_path).open("rb") as source:
                while True:
                    chunk = source.read(_COPY_CHUNK_BYTES)
                    if not chunk:
                        break
                    binary_stream.write(chunk)
                    written += len(chunk)
            return written
        payload = self.text.encode("utf-8")
        binary_stream.write(payload)
        return len(payload)

    def cleanup(self) -> None:
        """Remove a service-owned temporary artifact, never a published file."""
        if self.temporary_artifact and self.artifact_path is not None:
            try:
                Path(self.artifact_path).unlink(missing_ok=True)
            except OSError:
                pass

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_count": self.file_count,
            "profile": self.profile,
            "output_path": str(self.output_path) if self.output_path else None,
            "bytes": self.byte_count or len(self.text.encode("utf-8")),
            "text_inline": bool(self.text) or self.byte_count == 0,
        }


@dataclass(frozen=True)
class ExtractResult:
    """The outcome of extracting a bundle."""

    processed: int
    skipped: int
    errors: int
    output_dir: Path
    profile: str
    repository_preflight: Optional[RepositoryExtractionPreflight] = None

    @property
    def total(self) -> int:
        return self.processed + self.skipped + self.errors

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "processed": self.processed,
            "skipped": self.skipped,
            "errors": self.errors,
            "total": self.total,
            "output_dir": str(self.output_dir),
            "profile": self.profile,
        }
        if self.repository_preflight is not None:
            payload["repository_preflight"] = (
                self.repository_preflight.to_dict())
        return payload


@dataclass(frozen=True)
class ValidationResult:
    """The outcome of validating a bundle."""

    valid: bool
    profile: Optional[str]
    file_count: int
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "profile": self.profile,
            "file_count": self.file_count,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class LoadedBundleResult:
    """A parsed manifest paired with the check that authorizes its use."""

    manifest: BundleManifest
    check: CheckResult

    def to_dict(self) -> Dict[str, Any]:
        return self.check.to_dict()


@dataclass(frozen=True)
class PlanResult:
    """A selection plan plus everything needed to act on or explain it.

    This is the WP3 contract object: the CLI renders it, the desktop workspace
    (WP4) binds a tree to it, and `create_bundle(plan=...)` consumes it. It
    carries no renderer and no open file handle, so it can be serialised,
    cached (WP5) or handed across a thread boundary unchanged.
    """

    plan: SelectionPlan
    base_path: Path
    sources: List[Path]
    scan: ScanResult
    presets_applied: List[str] = field(default_factory=list)
    notices: List[str] = field(default_factory=list)
    base_action: str = Action.INCLUDE.value
    #: The arguments that produced this plan. `BundleToolService.replan` varies
    #: one of them and reuses `scan`, which is what makes a checkbox toggle in
    #: the desktop workspace cost zero filesystem reads.
    inputs: Dict[str, Any] = field(default_factory=dict)
    #: The assembled rule stack, so an adapter can show "rules in effect"
    #: without re-deriving it. Deliberately absent from `to_dict()`: the
    #: selection report is a decisions document with a fixed shape, and the
    #: Build 114 determinism tests pin it.
    rules: Tuple[SelectionRule, ...] = ()
    #: Optional read-only repository evidence used to narrow this exact plan.
    #: Absolute repository paths stay in memory and are never serialized.
    repository: Optional[RepositorySourceEvidence] = None

    @property
    def included_paths(self) -> List[str]:
        return self.plan.ordered_paths()

    @property
    def file_count(self) -> int:
        return len(self.plan.included())

    def absolute_paths(self) -> List[Path]:
        """Included paths resolved back to disk, in emission order."""
        index = self.scan.by_path()
        resolved: List[Path] = []
        for relative in self.plan.ordered_paths():
            entry = index.get(relative)
            resolved.append(Path(entry.absolute) if entry and entry.absolute
                            else self.base_path / relative)
        return resolved

    def estimated_bytes(self, header_bytes: int = 0) -> int:
        return self.plan.estimated_payload_bytes(header_bytes=header_bytes)

    def estimate(self) -> PlanEstimate:
        """Estimate artifact, temporary storage and bounded working memory.

        Planning deliberately does not open files, so it cannot know which
        inputs will be base64. ``output_bytes`` therefore uses an all-binary
        upper estimate plus per-entry transport overhead. The memory estimate
        describes Build 124's spooled execution path: metadata plus the largest
        allowed entry and a fixed renderer/IO working allowance, rather than a
        second complete artifact in RAM.
        """
        included = self.plan.included()
        count = len(included)
        raw = sum(max(0, int(item.size)) for item in included)
        encoded_upper = 4 * -(-raw // 3)
        output = max(raw, encoded_upper) + count * _ESTIMATED_ENTRY_OVERHEAD
        temporary = output * 2
        largest = max((max(0, int(item.size)) for item in included), default=0)
        peak = 64 * _MIB + count * 2048 + largest * 3
        if count >= _EXTREME_PLAN_FILES or raw >= _EXTREME_PLAN_BYTES:
            level = "extreme"
        elif count >= _LARGE_PLAN_FILES or raw >= _LARGE_PLAN_BYTES:
            level = "large"
        else:
            level = "normal"
        return PlanEstimate(count, raw, output, temporary, peak, level)

    def to_dict(self) -> Dict[str, Any]:
        """The `--report` payload. Deterministic: no clock, no absolute paths.

        Absolute paths are deliberately absent. A selection report is meant to
        be committed and diffed across machines, and Paul's Build 131 note
        forbids baking one person's sibling paths into shared artifacts.
        """
        payload = self.plan.to_dict()
        payload.update({
            "base_action": self.base_action,
            "presets_applied": list(self.presets_applied),
            "notices": list(self.notices),
            "sources": [normalise(os.path.relpath(Path(s), self.base_path))
                        for s in self.sources],
            "detectors": self.scan.ledger.to_report(),
            "scanned": self.scan.scanned,
            "estimated_bytes": self.estimated_bytes(),
            "capacity_estimate": self.estimate().to_dict(),
        })
        if self.repository is not None:
            payload["repository"] = self.repository.to_dict()
        return payload


# ===================================================================================================
# The service
# ===================================================================================================

class BundleToolService:
    """Orchestrates bundling, extraction and validation for every interface."""

    def __init__(self,
                 config: Optional[ConfigManager] = None,
                 registry: Optional[ProfileRegistry] = None,
                 repository_reader: Optional[RepositoryReader] = None) -> None:
        self.config = config or ConfigManager()
        self.registry = registry or ProfileRegistry()
        self.parser = BundleParser(registry=self.registry)
        self.repository_reader = repository_reader

    # -----------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------

    def _setting(self, key: str, default: Any) -> Any:
        try:
            value = self.config.get(key, default)
        except Exception:
            return default
        return default if value is None else value

    def default_profile(self) -> str:
        return self._setting("app_defaults.bundle_profile", "plain_marker")

    @staticmethod
    def _is_bft_source_root(candidate: Path) -> bool:
        """Recognise this product by its governed source layout, not its name."""
        root = Path(candidate)
        return root.is_dir() and all((root / marker).is_file() for marker in (
            "pyproject.toml",
            "bundle_config.json",
            "src/core/service.py",
            "src/ui/main_window.py",
        ))

    def recommended_presets(self, sources: List[Path],
                            base_path: Optional[Path] = None) -> List[str]:
        """Return a project-specific preset for BFT's measured self-bundle case."""
        candidates = ([Path(base_path)] if base_path is not None
                      else [Path(source) for source in sources])
        return (["bft-source"]
                if any(self._is_bft_source_root(path) for path in candidates)
                else [])

    def _effective_max_file_mb(self, requested: Optional[float]) -> float:
        """Resolve the governed size limit once and carry it in the plan."""
        value = (self._setting("safety.max_file_mb", 10.0)
                 if requested is None else requested)
        try:
            result = float(value)
        except (TypeError, ValueError) as error:
            raise BundleFileToolError(
                f"Maximum file size must be a number, got {value!r}.") from error
        if result <= 0:
            raise BundleFileToolError(
                f"Maximum file size must be greater than zero, got {result}.")
        return result

    @staticmethod
    def _repository_mode(value: Union[str, RepositorySourceMode]
                         ) -> RepositorySourceMode:
        try:
            return (value if isinstance(value, RepositorySourceMode)
                    else RepositorySourceMode(str(value)))
        except ValueError as error:
            choices = ", ".join(item.value for item in RepositorySourceMode)
            raise RepositoryIntegrationError(
                f"Unknown repository source mode {value!r}; choose {choices}.") from error

    def _load_repository_source(
            self,
            base_path: Path,
            mode: Union[str, RepositorySourceMode]
            ) -> Optional[RepositorySourceEvidence]:
        effective = self._repository_mode(mode)
        if effective is RepositorySourceMode.FILESYSTEM:
            return None
        if self.repository_reader is None:
            raise RepositoryIntegrationError(
                "Repository tracked mode requires an installed repository "
                "reader adapter.")
        return build_source_evidence(
            self.repository_reader, Path(base_path), effective)

    def _validate_repository_source(self, result: PlanResult) -> None:
        """Fail when tracked membership changed after the reviewed plan."""
        approved = result.repository
        if approved is None:
            return
        current = self._load_repository_source(
            result.base_path, approved.mode)
        if current is None:
            raise PlanDriftError(
                "repository evidence disappeared after review")
        if current.inventory_digest == approved.inventory_digest:
            return
        old = approved.inventory.by_path()
        new = current.inventory.by_path()
        changed = sorted(
            path for path in set(old) | set(new)
            if old.get(path) != new.get(path)
        )
        raise PlanDriftError(
            "repository tracked-file inventory changed after review",
            changed)

    @contextmanager
    def _repository_content_reader(
            self,
            result: PlanResult,
            max_file_mb: float,
            ) -> Iterator[Optional[Callable[[str], bytes]]]:
        """Open the VCS plan-bound byte source for repository-mode reads."""
        approved = result.repository
        if approved is None:
            yield None
            return
        if self.repository_reader is None:
            raise RepositoryIntegrationError(
                "Repository source evidence exists but its reader is unavailable.")

        max_file_bytes = max(1, math.ceil(max_file_mb * 1024 * 1024))
        with self.repository_reader.open_read_session(
                result.base_path,
                allowed_root=result.base_path,
                max_file_bytes=max_file_bytes) as session:
            session_root = Path(session.inventory.repository_root).resolve()
            if session_root != Path(result.base_path).resolve():
                raise RepositoryIntegrationError(
                    "Repository read-session root does not match the approved base.")
            if session.inventory.digest() != approved.inventory_digest:
                old = approved.inventory.by_path()
                new = session.inventory.by_path()
                changed = sorted(
                    path for path in set(old) | set(new)
                    if old.get(path) != new.get(path)
                )
                raise PlanDriftError(
                    "repository read-session inventory differs from the "
                    "reviewed plan",
                    changed,
                )
            if not session.plan_manifest_digest:
                raise RepositoryIntegrationError(
                    "Repository read session has no plan-manifest digest.")
            yield session.read_bytes

    @staticmethod
    def _unsafe_relative(path: str) -> bool:
        candidate = PurePosixPath(normalise(path))
        return candidate.is_absolute() or any(
            part in ("", ".", "..") for part in candidate.parts)

    def _validate_plan_snapshot(self, result: PlanResult,
                                output_path: Optional[Path],
                                *,
                                progress: Optional[ProgressSink] = None,
                                cancel: Optional[CancelCheck] = None,
                                phase: str = PHASE_VERIFY_SOURCE,
                                label: str = "approved snapshot",
                                operation: str = OP_BUNDLE) -> None:
        """Fail closed when the approved metadata snapshot has drifted.

        This check runs both immediately before and immediately after the
        writer reads.  The manifest reconciliation that follows is the final
        path/size authority.  No output file is opened until all three agree.
        """
        index = result.scan.by_path()
        base = Path(result.base_path).resolve()
        output = Path(output_path).resolve() if output_path is not None else None
        included = result.plan.included()
        total = len(included)
        reporter = ThrottledReporter(
            progress, operation, phase, "files", total=total)

        for position, decision in enumerate(included, start=1):
            raise_if_cancelled(
                cancel, operation=operation, phase=phase,
                completed=position - 1, total=total)
            relative = normalise(decision.path)
            entry = index.get(relative)
            if entry is None:
                raise PlanDriftError(
                    "an included decision has no metadata record", [relative])
            if self._unsafe_relative(relative):
                raise PlanDriftError(
                    "an included path is not safely relative to the base",
                    [relative])

            source = Path(entry.absolute) if entry.absolute else base / relative
            resolved = source.resolve()
            try:
                resolved.relative_to(base)
            except ValueError:
                raise PlanDriftError(
                    "an included path resolves outside the approved base",
                    [relative]) from None

            if output is not None and resolved == output:
                raise PlanDriftError(
                    "the active output file is also selected as an input",
                    [relative])

            try:
                file_stat = resolved.stat()
            except FileNotFoundError:
                raise PlanDriftError(
                    "a planned file was deleted or renamed", [relative]) from None
            except OSError as error:
                raise PlanDriftError(
                    f"a planned file cannot be inspected ({type(error).__name__})",
                    [relative]) from None

            if not stat.S_ISREG(file_stat.st_mode):
                raise PlanDriftError(
                    "a planned file is no longer a regular file", [relative])
            current_mtime = getattr(file_stat, "st_mtime_ns", 0)
            if file_stat.st_size != entry.size or (
                    entry.mtime_ns and current_mtime != entry.mtime_ns):
                raise PlanDriftError(
                    "a planned file changed after review", [relative])
            reporter.tick(
                position,
                message=f"Checking {label}: {relative}")

        raise_if_cancelled(
            cancel, operation=operation, phase=phase,
            completed=total, total=total)
        reporter.close(total, message=f"Verified {label} ({total} files)")

    @staticmethod
    def _reconcile_plan_manifest(result: PlanResult,
                                 manifest: BundleManifest) -> None:
        """Require the artifact manifest to equal the approved emission list."""
        expected = result.plan.ordered_paths()
        actual = [normalise(entry.path) for entry in manifest.entries]
        skipped = list(getattr(manifest, "skipped_entries", ()) or ())

        if skipped:
            paths = [normalise(str(item.get("path", "<unknown>")))
                     for item in skipped]
            raise PlanDriftError(
                "the writer skipped files that the plan approved", paths)

        if actual != expected:
            missing = [path for path in expected if path not in set(actual)]
            extra = [path for path in actual if path not in set(expected)]
            affected = missing + extra
            reason = "the writer manifest does not equal the approved emission list"
            if not affected:
                reason += " (emission order changed)"
            raise PlanDriftError(reason, affected)

        metadata = result.scan.by_path()
        changed = []
        for bundle_entry in manifest.entries:
            relative = normalise(bundle_entry.path)
            planned = metadata.get(relative)
            emitted_size = getattr(bundle_entry, "file_size_bytes", None)
            if planned is None or emitted_size != planned.size:
                changed.append(relative)
        if changed:
            raise PlanDriftError(
                "emitted file sizes differ from the approved snapshot", changed)

    @staticmethod
    def _publish_text_atomically(output_path: Path, text: str) -> None:
        """Publish only a complete formatted artifact in the target directory."""
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary: Optional[Path] = None
        try:
            with tempfile.NamedTemporaryFile(
                    mode="w", encoding="utf-8", newline="", delete=False,
                    dir=str(target.parent),
                    prefix=f".{target.name}.", suffix=".tmp") as handle:
                temporary = Path(handle.name)
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
        except Exception as error:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass
            raise BundleWriteError(str(target), str(error)) from error

    @staticmethod
    def _open_artifact_temp(*, preferred: Optional[Path] = None,
                            prefix: str = ".bft-artifact-"):
        """Open a writable named temporary file with deterministic fallbacks."""
        candidates: List[Path] = []
        if preferred is not None:
            candidates.append(Path(preferred))
        configured = os.environ.get("BFT_TEMP_DIR")
        if configured:
            candidates.append(Path(configured))
        candidates.extend((Path(tempfile.gettempdir()), Path.cwd() / "tmp"))
        attempted = []
        for directory in candidates:
            key = str(directory.resolve(strict=False))
            if key in attempted:
                continue
            attempted.append(key)
            try:
                directory.mkdir(parents=True, exist_ok=True)
                return tempfile.NamedTemporaryFile(
                    mode="w+b", delete=False, dir=str(directory),
                    prefix=prefix, suffix=".tmp")
            except OSError:
                continue
        raise BundleWriteError(
            str(preferred or "temporary directory"),
            "No writable directory is available for the bounded artifact spool")

    def _format_to_spool(self, profile_impl, manifest: BundleManifest,
                         output_path: Optional[Path],
                         progress: Optional[ProgressSink],
                         cancel: Optional[CancelCheck]) -> Tuple[Path, int]:
        """Format one entry at a time into a bounded UTF-8 artifact spool."""
        preferred = Path(output_path).parent if output_path is not None else None
        handle = self._open_artifact_temp(preferred=preferred)
        spool = Path(handle.name)
        total = len(manifest.entries)
        reporter = ThrottledReporter(
            progress, OP_BUNDLE, PHASE_FORMAT, "entries", total=total)
        written = 0
        try:
            for position, text_chunk in enumerate(
                    profile_impl.iter_format_manifest(manifest), start=1):
                raise_if_cancelled(
                    cancel, operation=OP_BUNDLE, phase=PHASE_FORMAT,
                    completed=position - 1, total=total)
                payload = text_chunk.encode("utf-8")
                handle.write(payload)
                written += len(payload)
                reporter.tick(
                    min(position, total),
                    message=f"Formatted {min(position, total)} of {total} entries")
            raise_if_cancelled(
                cancel, operation=OP_BUNDLE, phase=PHASE_FORMAT,
                completed=total, total=total)
            handle.flush()
            reporter.close(total, message=f"Formatted {total} entries")
            return spool, written
        except BaseException:
            try:
                handle.close()
            finally:
                spool.unlink(missing_ok=True)
            raise
        finally:
            if not handle.closed:
                handle.close()

    @staticmethod
    def _publish_spool_atomically(spool: Path, output_path: Path,
                                  progress: Optional[ProgressSink],
                                  cancel: Optional[CancelCheck]) -> int:
        """Copy a complete spool, fsync, then atomically publish the target."""
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        total = spool.stat().st_size
        temporary: Optional[Path] = None
        reporter = ThrottledReporter(
            progress, OP_BUNDLE, PHASE_WRITE, "bytes", total=total)
        completed = 0
        try:
            with tempfile.NamedTemporaryFile(
                    mode="w+b", delete=False, dir=str(target.parent),
                    prefix=f".{target.name}.", suffix=".tmp") as destination:
                temporary = Path(destination.name)
                with spool.open("rb") as source:
                    while True:
                        raise_if_cancelled(
                            cancel, operation=OP_BUNDLE, phase=PHASE_WRITE,
                            completed=completed, total=total)
                        chunk = source.read(_COPY_CHUNK_BYTES)
                        if not chunk:
                            break
                        destination.write(chunk)
                        completed += len(chunk)
                        reporter.tick(
                            completed,
                            message=f"Wrote {completed:,} of {total:,} bytes")
                reporter.close(total, message=f"Wrote {total:,} bytes")
                emit(progress, OperationProgress(
                    operation=OP_BUNDLE, phase=PHASE_FINALIZE,
                    current=0, total=None, unit="artifact",
                    message="Flushing and publishing the complete artifact"))
                raise_if_cancelled(
                    cancel, operation=OP_BUNDLE, phase=PHASE_FINALIZE,
                    completed=0, total=1)
                destination.flush()
                os.fsync(destination.fileno())
            os.replace(temporary, target)
            emit(progress, OperationProgress(
                operation=OP_BUNDLE, phase=PHASE_FINALIZE,
                current=1, total=None, unit="artifact",
                message="Artifact published atomically"))
            return total
        except BaseException as error:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass
            if isinstance(error, BundleFileToolError):
                raise
            raise BundleWriteError(str(target), str(error)) from error

    def available_profiles(self) -> List[str]:
        return self.registry.list_profiles()

    def _read_text(self,
                   source: Union[str, Path],
                   *,
                   encoding: Optional[str] = None,
                   progress: Optional[ProgressSink] = None,
                   operation: str = OP_EXTRACT) -> str:
        """Accept decoded text or strictly decode a path at parser ingress.

        A string is already decoded and therefore has no transport encoding to
        select.  Paths always use the parser's shared, fail-closed reader so the
        service cannot drift from CLI or desktop ingress semantics.
        """
        if isinstance(source, Path):
            return self.parser.read_bundle_text(
                source,
                encoding=encoding,
                progress=progress,
                operation=operation,
            )
        return source

    # -----------------------------------------------------------------
    # Check
    # -----------------------------------------------------------------

    def check_manifest(self,
                       manifest: BundleManifest,
                       *,
                       subject: str = SUBJECT_BUNDLE,
                       label: str = "bundle",
                       generation: Optional[int] = None,
                       operation: str = OP_CHECK,
                       progress: Optional[ProgressSink] = None,
                       cancel: Optional[CancelCheck] = None) -> CheckResult:
        """Return the shared checked/blocked/ready state for one manifest."""
        return run_manifest_check(
            manifest,
            subject=subject,
            label=label,
            generation=generation,
            operation=operation,
            progress=progress,
            cancel=cancel,
        )

    def load_checked_bundle(self,
                            source: Union[str, Path],
                            profile: Optional[str] = None,
                            progress: Optional[ProgressSink] = None,
                            cancel: Optional[CancelCheck] = None,
                            encoding: Optional[str] = None,
                            subject: str = SUBJECT_BUNDLE) -> LoadedBundleResult:
        """Read and parse an existing bundle once, then check that manifest."""
        text = self._read_text(
            source,
            encoding=encoding,
            progress=progress,
            operation=OP_CHECK,
        )
        emit(progress, OperationProgress(
            operation=OP_CHECK,
            phase=PHASE_PARSE,
            current=0,
            total=None,
            unit="entries",
            message="Parsing bundle for checking",
        ))
        manifest = self.parser.parse(text, profile_name=profile)
        count = len(manifest.entries)
        emit(progress, OperationProgress(
            operation=OP_CHECK,
            phase=PHASE_PARSE,
            current=count,
            total=count,
            unit="entries",
            message=f"Parsed {count} entries",
        ))
        label = str(source) if isinstance(source, Path) else "bundle text"
        result = self.check_manifest(
            manifest,
            subject=subject,
            label=label,
            progress=progress,
            cancel=cancel,
        )
        emit(progress, OperationProgress(
            operation=OP_CHECK,
            phase=PHASE_COMPLETE,
            current=count,
            total=count,
            unit="entries",
            message=("Check passed" if result.valid else "Check blocked"),
        ))
        return LoadedBundleResult(manifest=manifest, check=result)

    def check_bundle(self,
                     source: Union[str, Path],
                     profile: Optional[str] = None,
                     progress: Optional[ProgressSink] = None,
                     cancel: Optional[CancelCheck] = None,
                     encoding: Optional[str] = None,
                     subject: str = SUBJECT_BUNDLE) -> CheckResult:
        """Check a bundle path or decoded bundle string."""
        return self.load_checked_bundle(
            source,
            profile=profile,
            progress=progress,
            cancel=cancel,
            encoding=encoding,
            subject=subject,
        ).check

    def check_selection(self,
                        plan: PlanResult,
                        profile: Optional[str] = None,
                        progress: Optional[ProgressSink] = None,
                        cancel: Optional[CancelCheck] = None) -> CheckResult:
        """Read an approved plan and check it without producing an artifact."""
        profile_name = profile or self.default_profile()
        effective_max = float(plan.inputs.get(
            "max_file_mb", self._effective_max_file_mb(None)))
        creator = BundleCreator(
            allow_globs=["**/*"],
            deny_globs=[],
            max_file_mb=effective_max,
            treat_binary_as_base64=self._setting(
                "app_defaults.treat_binary_as_base64", True),
        )
        self._validate_repository_source(plan)
        self._validate_plan_snapshot(
            plan,
            None,
            progress=progress,
            cancel=cancel,
            phase=PHASE_VERIFY_SOURCE,
            label="check pre-read snapshot",
            operation=OP_CHECK,
        )
        with self._repository_content_reader(
                plan, effective_max) as content_reader:
            manifest = creator.create_manifest(
                plan.absolute_paths(),
                plan.base_path,
                profile_name,
                progress=progress,
                cancel=cancel,
                operation=OP_CHECK,
                content_reader=content_reader,
            )
        self._validate_repository_source(plan)
        self._validate_plan_snapshot(
            plan,
            None,
            progress=progress,
            cancel=cancel,
            phase=PHASE_VERIFY_READ,
            label="check post-read snapshot",
            operation=OP_CHECK,
        )
        self._reconcile_plan_manifest(plan, manifest)
        result = self.check_manifest(
            manifest,
            subject=SUBJECT_SELECTION,
            label=str(plan.base_path),
            generation=plan.plan.generation,
            progress=progress,
            cancel=cancel,
        )
        emit(progress, OperationProgress(
            operation=OP_CHECK,
            phase=PHASE_COMPLETE,
            current=result.file_count,
            total=result.file_count,
            unit="files",
            message=("Selection check passed" if result.valid
                     else "Selection check blocked"),
        ))
        return result

    # -----------------------------------------------------------------
    # Bundle
    # -----------------------------------------------------------------

    def create_bundle(self,
                      sources: List[Path],
                      base_path: Path,
                      profile: Optional[str] = None,
                      include: Optional[List[str]] = None,
                      exclude: Optional[List[str]] = None,
                      max_file_mb: Optional[float] = None,
                      output_path: Optional[Path] = None,
                      progress: Optional[ProgressSink] = None,
                      cancel: Optional[CancelCheck] = None,
                      plan: Optional[PlanResult] = None,
                      source_mode: Optional[
                          Union[str, RepositorySourceMode]] = None
                      ) -> BundleResult:
        """Plan (when needed), read, reconcile, gate and format a bundle.

        The integrity gate runs before formatting, so a contaminated manifest
        fails loudly and nothing is written - the D4 rule. Placing it here means
        no adapter can bypass it.

        P0 alignment: an omitted ``plan`` is convenience, not a legacy-engine
        switch.  The service creates the same canonical plan first and then
        executes it.  When a plan is supplied, its paths and metadata are
        verified before and after reading and the manifest must reconcile
        exactly before an output path can be published.
        """
        profile_name = profile or self.default_profile()
        profile_impl = self.registry.get(profile_name)

        if plan is None:
            effective_max = self._effective_max_file_mb(max_file_mb)
            plan = self.plan_bundle(
                sources=[Path(source) for source in sources],
                base_path=Path(base_path),
                include=include,
                exclude=exclude,
                max_file_mb=effective_max,
                output_path=output_path,
                progress=progress,
                cancel=cancel,
                source_mode=(source_mode or RepositorySourceMode.FILESYSTEM),
                _emit_complete=False,
            )
        else:
            planned_max = float(plan.inputs.get(
                "max_file_mb", self._effective_max_file_mb(None)))
            if (max_file_mb is not None
                    and float(max_file_mb) != planned_max):
                raise PlanDriftError(
                    "the creation size limit differs from the approved plan")
            effective_max = planned_max
            if source_mode is not None:
                planned_mode = (plan.repository.mode if plan.repository
                                else RepositorySourceMode.FILESYSTEM)
                if self._repository_mode(source_mode) is not planned_mode:
                    raise PlanDriftError(
                        "the creation repository mode differs from the "
                        "approved plan")

        discovered = plan.absolute_paths()
        base_path = plan.base_path
        creator = BundleCreator(
            allow_globs=["**/*"], deny_globs=[],
            max_file_mb=effective_max,
            treat_binary_as_base64=self._setting(
                "app_defaults.treat_binary_as_base64", True),
        )
        self._validate_repository_source(plan)
        self._validate_plan_snapshot(
            plan, output_path, progress=progress, cancel=cancel,
            phase=PHASE_VERIFY_SOURCE, label="pre-read snapshot")
        return self._finish_bundle(
            creator, discovered, Path(base_path), profile_name,
            profile_impl, output_path, progress, cancel, plan=plan)

    def _finish_bundle(self, creator, discovered, base_path, profile_name,
                       profile_impl, output_path, progress, cancel,
                       plan: Optional[PlanResult] = None) -> BundleResult:
        """Read, gate, format and write. Shared by the planned and legacy paths.

        Extracted in Build 114 so `create_bundle(plan=...)` cannot drift from
        `create_bundle(include=...)`. The integrity gate lives here, which means
        neither entry point can reach an artifact without passing it.
        """
        if plan is None:
            manifest = creator.create_manifest(
                discovered, base_path, profile_name,
                progress=progress, cancel=cancel)
        else:
            with self._repository_content_reader(
                    plan, creator.max_file_mb) as content_reader:
                manifest = creator.create_manifest(
                    discovered, base_path, profile_name,
                    progress=progress, cancel=cancel,
                    content_reader=content_reader)

        if plan is not None:
            # A deletion or read failure can occur after the pre-read check.
            # Validate again, then require one manifest entry for every planned
            # emission path before formatting or publishing anything.
            self._validate_repository_source(plan)
            self._validate_plan_snapshot(
                plan, output_path, progress=progress, cancel=cancel,
                phase=PHASE_VERIFY_READ, label="post-read snapshot")
            self._reconcile_plan_manifest(plan, manifest)

        assert_bundle_clean(
            manifest,
            source_label=str(output_path) if output_path else "stdout",
            progress=progress,
            cancel=cancel,
            operation=OP_BUNDLE,
        )

        spool: Optional[Path] = None
        retain_spool = False
        text = ""
        artifact_path: Optional[Path] = None
        temporary_artifact = False
        try:
            spool, byte_count = self._format_to_spool(
                profile_impl, manifest,
                Path(output_path) if output_path is not None else None,
                progress, cancel)

            if output_path is not None:
                output_path = Path(output_path)
                byte_count = self._publish_spool_atomically(
                    spool, output_path, progress, cancel)
                artifact_path = output_path
                if byte_count <= _INLINE_RESULT_LIMIT:
                    try:
                        with output_path.open(
                                "r", encoding="utf-8", newline="") as source:
                            text = source.read()
                    except OSError:
                        # Publication succeeded. Inline convenience must not
                        # turn a valid artifact into a reported failure.
                        text = ""
            else:
                emit(progress, OperationProgress(
                    operation=OP_BUNDLE, phase=PHASE_WRITE,
                    current=0, total=byte_count, unit="bytes",
                    message="Staging artifact for the caller"))
                emit(progress, OperationProgress(
                    operation=OP_BUNDLE, phase=PHASE_WRITE,
                    current=byte_count, total=byte_count, unit="bytes",
                    message=f"Staged {byte_count:,} bytes"))
                emit(progress, OperationProgress(
                    operation=OP_BUNDLE, phase=PHASE_FINALIZE,
                    current=0, total=None, unit="artifact",
                    message="Preparing the completed artifact result"))
                if byte_count <= _INLINE_RESULT_LIMIT:
                    with spool.open("r", encoding="utf-8", newline="") as source:
                        text = source.read()
                else:
                    artifact_path = spool
                    temporary_artifact = True
                    retain_spool = True
                emit(progress, OperationProgress(
                    operation=OP_BUNDLE, phase=PHASE_FINALIZE,
                    current=1, total=None, unit="artifact",
                    message="Artifact result is ready"))
        finally:
            if spool is not None and not retain_spool:
                try:
                    spool.unlink(missing_ok=True)
                except OSError:
                    pass

        emit(progress, OperationProgress(
            operation=OP_BUNDLE, phase=PHASE_COMPLETE,
            current=len(manifest.entries), total=len(manifest.entries), unit="files",
            message=f"Bundled {len(manifest.entries)} files as {profile_name}",
        ))

        return BundleResult(
            text=text,
            manifest=manifest,
            file_count=len(manifest.entries),
            profile=profile_name,
            output_path=output_path,
            artifact_path=artifact_path,
            byte_count=byte_count,
            temporary_artifact=temporary_artifact,
        )

    # -----------------------------------------------------------------
    # Extract
    # -----------------------------------------------------------------

    def _repository_extraction_preflight(
            self,
            manifest: BundleManifest,
            output_dir: Path,
            policy: RepositoryExtractionPolicy
            ) -> RepositoryExtractionPreflight:
        if self.repository_reader is None:
            raise RepositoryIntegrationError(
                "Repository extraction requires an installed repository "
                "reader adapter.")
        return build_extraction_preflight(
            self.repository_reader,
            Path(output_dir),
            [entry.path for entry in manifest.entries],
            policy,
        )

    def preflight_repository_extraction(
            self,
            source: Union[str, Path],
            output_dir: Path,
            profile: Optional[str] = None,
            policy: Optional[RepositoryExtractionPolicy] = None,
            encoding: Optional[str] = None
            ) -> RepositoryExtractionPreflight:
        """Inspect a repository target without writing bundle entries."""
        text = self._read_text(source, encoding=encoding, operation=OP_CHECK)
        manifest = self.parser.parse(text, profile_name=profile)
        checked = self.check_manifest(
            manifest,
            subject=SUBJECT_BUNDLE,
            label=str(source) if isinstance(source, Path) else "bundle text",
        )
        if not checked.valid:
            raise ValidationError(format_blocked_check(checked))
        return self._repository_extraction_preflight(
            manifest,
            Path(output_dir),
            policy or RepositoryExtractionPolicy(),
        )

    def extract_bundle(self,
                       source: Union[str, Path],
                       output_dir: Path,
                       profile: Optional[str] = None,
                       overwrite_policy: Optional[str] = None,
                       add_headers: Optional[bool] = None,
                       dry_run: bool = False,
                       progress: Optional[ProgressSink] = None,
                       cancel: Optional[CancelCheck] = None,
                       encoding: Optional[str] = None,
                       repository_policy: Optional[
                           RepositoryExtractionPolicy] = None) -> ExtractResult:
        """Parse a bundle and write its entries.

        Extraction reconciliation lives in the writer and is not optional, so a
        short extraction raises rather than reporting success.
        """
        text = self._read_text(
            source,
            encoding=encoding,
            progress=progress,
            operation=OP_EXTRACT,
        )

        emit(progress, OperationProgress(
            operation=OP_EXTRACT, phase=PHASE_PARSE, current=0, total=None, unit="entries",
            message="Parsing bundle",
        ))
        manifest = self.parser.parse(text, profile_name=profile)
        entry_count = len(manifest.entries)
        emit(progress, OperationProgress(
            operation=OP_EXTRACT, phase=PHASE_PARSE,
            current=entry_count, total=entry_count, unit="entries",
        ))

        # Build 125: parsing is not authorization to write.  Every adapter
        # reaches this service gate before extraction, even when its optional
        # on-load convenience check was disabled.
        checked = self.check_manifest(
            manifest,
            subject=SUBJECT_BUNDLE,
            label=str(source) if isinstance(source, Path) else "bundle text",
            operation=OP_EXTRACT,
            progress=progress,
            cancel=cancel,
        )
        if not checked.valid:
            raise ValidationError(format_blocked_check(checked))

        repository_preflight = None
        if repository_policy is not None:
            repository_preflight = self._repository_extraction_preflight(
                manifest, Path(output_dir), repository_policy)
            repository_preflight.require_allowed()

        writer = BundleWriter(
            output_dir=Path(output_dir),
            overwrite_policy=overwrite_policy or self._setting("app_defaults.overwrite_policy", "prompt"),
            dry_run=dry_run,
            add_headers=self._setting("app_defaults.add_headers", True)
            if add_headers is None else add_headers,
        )

        # BFT_B109_SERVICE_PROGRESS_PASSTHROUGH (F-06). The sink goes to the
        # writer so subscribers see a per-file sequence rather than the bracket
        # this used to emit - Paul measured [0, N] for an N-file extraction.
        #
        # `emit_complete=False` because the service owns the terminal event: it
        # also ran the parse phase, which the writer knows nothing about.
        emit(progress, OperationProgress(
            operation=OP_EXTRACT, phase=PHASE_WRITE,
            current=0, total=entry_count, unit="files",
        ))
        stats = writer.extract_manifest(manifest, Path(output_dir),
                                        progress=progress, emit_complete=False,
                                        cancel=cancel)

        emit(progress, OperationProgress(
            operation=OP_EXTRACT, phase=PHASE_COMPLETE,
            current=entry_count, total=entry_count, unit="files",
            message=f"Extracted {stats['processed']} of {entry_count} files",
        ))

        return ExtractResult(
            processed=stats["processed"],
            skipped=stats["skipped"],
            errors=stats["errors"],
            output_dir=Path(output_dir),
            profile=manifest.profile,
            repository_preflight=repository_preflight,
        )

    # -----------------------------------------------------------------
    # Validate
    # -----------------------------------------------------------------

    def validate_bundle(self,
                        source: Union[str, Path],
                        profile: Optional[str] = None,
                        progress: Optional[ProgressSink] = None,
                        encoding: Optional[str] = None) -> ValidationResult:
        text = self._read_text(
            source,
            encoding=encoding,
            progress=progress,
            operation=OP_VALIDATE,
        )

        emit(progress, OperationProgress(
            operation=OP_VALIDATE, phase=PHASE_PARSE, current=0, total=None, unit="entries",
            message="Validating bundle",
        ))
        report = self.parser.validate_bundle(text, profile_name=profile)

        emit(progress, OperationProgress(
            operation=OP_VALIDATE, phase=PHASE_COMPLETE,
            current=report.get("file_count", 0), total=report.get("file_count", 0),
            unit="entries",
            message="valid" if report.get("valid") else "invalid",
        ))

        return ValidationResult(
            valid=bool(report.get("valid")),
            profile=report.get("profile"),
            file_count=int(report.get("file_count", 0)),
            errors=list(report.get("errors", [])),
            warnings=list(report.get("warnings", [])),
        )

    # -----------------------------------------------------------------
    # BFT_B114_SERVICE_PLANNING - Plan (WP3)
    # -----------------------------------------------------------------

    def plan_bundle(self,
                    sources: List[Path],
                    base_path: Optional[Path] = None,
                    preset: Optional[List[str]] = None,
                    rules: Optional[Path] = None,
                    include: Optional[List[str]] = None,
                    exclude: Optional[List[str]] = None,
                    force_include: Optional[List[str]] = None,
                    force_exclude: Optional[List[str]] = None,
                    overrides: Optional[List] = None,
                    groups: Optional[List[str]] = None,
                    include_roots: Optional[List[str]] = None,
                    no_default_rules: bool = False,
                    max_file_mb: Optional[float] = None,
                    output_path: Optional[Path] = None,
                    progress: Optional[ProgressSink] = None,
                    cancel: Optional[CancelCheck] = None,
                    source_mode: Union[
                        str, RepositorySourceMode] = RepositorySourceMode.FILESYSTEM,
                    _emit_complete: bool = True) -> PlanResult:
        """Decide what would be bundled, without reading a single file.

        This is the operation the whole workspace turns on. It scans metadata,
        assembles the rule stack across six ladder layers, and evaluates every
        candidate into a decision that carries its own explanation.

        Nothing here opens a file, so the result is cheap to recompute and safe
        to show before committing to anything. `create_bundle(plan=...)` is the
        step that reads.
        """
        sources = [Path(s) for s in sources]
        if not sources:
            raise BundleFileToolError("At least one source path is required.")
        # A missing source used to scan to an empty result and report success.
        # The CLI happened to check first; the desktop workspace did not, so a
        # mistyped folder produced a confident plan for nothing at all.
        for candidate in sources:
            if not candidate.exists():
                raise BundleFileToolError(
                    f"Source path not found: {candidate} (does not exist)")
        base = (Path(base_path) if base_path
                else self._infer_base_path(sources)).resolve()
        effective_max = self._effective_max_file_mb(max_file_mb)
        effective_source_mode = self._repository_mode(source_mode)
        repository = self._load_repository_source(
            base, effective_source_mode)

        auto_preset = False
        effective_presets = list(preset or [])
        if preset is None and not no_default_rules:
            effective_presets = self.recommended_presets(sources, base)
            auto_preset = bool(effective_presets)

        prune_names = self._planning_prune_names(
            effective_presets, no_default_rules=no_default_rules)

        scan = self._scan_sources(sources, base, include_roots or [],
                                  progress=progress, cancel=cancel,
                                  prune_dir_names=prune_names)

        inputs: Dict[str, Any] = {
            "preset": effective_presets,
            "rules": rules,
            "include": list(include or []),
            "exclude": list(exclude or []),
            "force_include": list(force_include or []),
            "force_exclude": list(force_exclude or []),
            "overrides": [tuple(o) for o in (overrides or [])],
            "groups": list(groups or []),
            "include_roots": list(include_roots or []),
            "no_default_rules": bool(no_default_rules),
            "max_file_mb": effective_max,
            "output_path": Path(output_path) if output_path is not None else None,
            "source_mode": effective_source_mode.value,
        }
        result = self._decide(
            scan, sources, base, inputs, generation=1,
            progress=progress, cancel=cancel, repository=repository)

        if auto_preset:
            result.notices.append(
                "Applied the bft-source preset automatically because the "
                "selected root is a Bundle File Tool source tree. Pass an "
                "explicit empty preset selection to opt out.")

        if _emit_complete:
            decision_count = len(result.plan.decisions)
            included_count = len(result.plan.included())
            emit(progress, OperationProgress(
                operation=OP_BUNDLE, phase=PHASE_COMPLETE,
                current=decision_count, total=decision_count,
                unit="paths",
                message=f"Planned {included_count} included paths across "
                        f"{decision_count} decisions"))
        return result

    def replan(self, previous: PlanResult, *,
               progress: Optional[ProgressSink] = None,
               cancel: Optional[CancelCheck] = None,
               **changes: Any) -> PlanResult:
        """Decide again over the scan `previous` already took.

        The desktop workspace calls this on every checkbox, filter or preset
        change. Re-scanning there would be both slow and *wrong*: the tree the
        operator is looking at would silently change under them mid-decision,
        and a file appearing between two clicks would enter the selection
        without ever being shown.

        Any `plan_bundle` keyword may be varied; everything else carries over.
        `include_roots` is the one exception - crossing into a pruned directory
        needs a walk that never happened, so it re-scans deliberately and the
        result is a **new generation** rather than a mutation of the old plan.

        Raises:
            BundleFileToolError: on an unknown keyword, so a typo cannot
                silently leave the previous value in force.
        """
        inputs = dict(previous.inputs)
        unknown = sorted(set(changes) - set(inputs))
        if unknown:
            raise BundleFileToolError(
                f"replan does not accept {', '.join(unknown)}. "
                f"Valid keys: {', '.join(sorted(inputs))}.")
        inputs.update(changes)

        previous_mode = (previous.repository.mode if previous.repository
                         else RepositorySourceMode.FILESYSTEM)
        requested_mode = self._repository_mode(
            inputs.get("source_mode", previous_mode.value))
        repository = (previous.repository
                      if requested_mode is previous_mode
                      else self._load_repository_source(
                          previous.base_path, requested_mode))

        if list(inputs["include_roots"]) != list(previous.inputs["include_roots"]):
            return self.plan_bundle(sources=previous.sources,
                                    base_path=previous.base_path,
                                    progress=progress, cancel=cancel, **inputs)

        differing = {key for key in inputs
                     if inputs[key] != previous.inputs.get(key)}
        if differing == {"overrides"} and previous.plan.decisions:
            result = self._decide_incrementally(previous, inputs)
        else:
            result = self._decide(
                previous.scan, previous.sources, previous.base_path, inputs,
                generation=previous.plan.generation + 1, previous=previous,
                progress=progress, cancel=cancel, repository=repository)

        decision_count = len(result.plan.decisions)
        included_count = len(result.plan.included())
        emit(progress, OperationProgress(
            operation=OP_BUNDLE, phase=PHASE_COMPLETE,
            current=decision_count, total=decision_count,
            unit="paths",
            message=f"Planned {included_count} included paths across "
                    f"{decision_count} decisions"))
        return result

    def _decide_incrementally(self, previous: PlanResult,
                              inputs: Dict[str, Any]) -> PlanResult:
        """Re-decide only the paths a changed session override can reach.

        A full re-decide of 4,000 paths costs ~430 ms, which is most of a
        second per checkbox and the difference between a workspace that feels
        connected to the mouse and one that does not. But when *only* Layer 1
        changed, almost none of that work can produce a different answer.

        The argument is exact rather than a heuristic. `decide()` evaluates
        each path independently and records a chain entry only for rules that
        actually match it. So for a path matched by no Layer 1 pattern - the
        old set or the new one - every rule it consults is identical, in the
        same order, and its decision and chain are therefore byte-identical.
        Only paths under a pattern that was added or removed can move.

        `test_incremental_and_full_replans_agree` pins that claim by comparing
        the two paths over many override sequences; if the reasoning is ever
        wrong, that test fails rather than a user's bundle changing quietly.
        """
        stack = self._build_rule_stack(
            preset=inputs["preset"], rules=inputs["rules"],
            include=inputs["include"], exclude=inputs["exclude"],
            force_include=inputs["force_include"],
            force_exclude=inputs["force_exclude"],
            overrides=inputs["overrides"],
            groups=inputs["groups"], no_default_rules=inputs["no_default_rules"])

        base_action, _scope = resolve_base_action(stack.allow_by_layer)
        engine = SelectionEngine(rules=stack.rules, groups=stack.groups,
                                 base_action=base_action)

        touched = ({pattern for _, pattern in previous.inputs.get("overrides", ())}
                   | {pattern for _, pattern in inputs["overrides"]})
        # A checkbox on one file produces a literal Layer 1 path, while a
        # folder checkbox produces the deliberately simple ``folder/**``
        # scope. Neither needs the regex glob engine. Build 118 still ran it
        # once per decision (and once per accumulated folder override), which
        # made successive clicks progressively slower under a traced or busy
        # Windows process. Preserve glob semantics for genuinely wildcarded
        # overrides, but use hash/prefix lookups for the two UI-native forms.
        literal_touched = {
            normalise(pattern) for pattern in touched
            if not any(marker in pattern for marker in ("*", "?", "["))
        }
        scoped_touched = {
            normalise(pattern)[:-3] for pattern in touched
            if normalise(pattern).endswith("/**")
            and not any(marker in normalise(pattern)[:-3]
                        for marker in ("*", "?", "["))
        }
        glob_touched = {
            pattern for pattern in touched
            if any(marker in pattern for marker in ("*", "?", "["))
            and not (normalise(pattern).endswith("/**")
                     and not any(marker in normalise(pattern)[:-3]
                                 for marker in ("*", "?", "[")))
        }
        unknown = previous.scan.unknown

        decisions = []
        for old_decision in previous.plan.decisions:
            if (old_decision.path in literal_touched
                    or any(old_decision.path == root
                           or old_decision.path.startswith(root + "/")
                           for root in scoped_touched)
                    or any(matches(pattern, old_decision.path)
                           for pattern in glob_touched)):
                changed = engine.decide(
                    old_decision.path, old_decision.size,
                    unknown.get(old_decision.path, ""))
                decisions.append(self._inherit_emission_contract(
                    changed, old_decision))
            else:
                decisions.append(old_decision)

        plan = SelectionPlan(
            decisions=tuple(decisions),
            groups=engine.groups,
            pruned_roots=previous.plan.pruned_roots,
            warnings=previous.plan.warnings,
            source_digests=tuple(stack.digests),
            rule_stack_digest=rule_stack_digest(stack.digests),
            generation=previous.plan.generation + 1,
        )
        plan = filter_plan_to_repository(plan, previous.repository)
        return PlanResult(
            plan=plan, base_path=previous.base_path, sources=previous.sources,
            scan=previous.scan, presets_applied=stack.presets_applied,
            notices=stack.notices, base_action=engine.base_action.value,
            inputs=inputs, rules=tuple(stack.rules),
            repository=previous.repository)

    def _decide(self, scan: ScanResult, sources: List[Path], base: Path,
                inputs: Dict[str, Any], generation: int,
                previous: Optional[PlanResult] = None,
                progress: Optional[ProgressSink] = None,
                cancel: Optional[CancelCheck] = None,
                repository: Optional[RepositorySourceEvidence] = None
                ) -> PlanResult:
        """The I/O-free half of planning: rules in, decisions out."""
        stack = self._build_rule_stack(
            preset=inputs["preset"], rules=inputs["rules"],
            include=inputs["include"], exclude=inputs["exclude"],
            force_include=inputs["force_include"],
            force_exclude=inputs["force_exclude"],
            overrides=inputs["overrides"],
            groups=inputs["groups"], no_default_rules=inputs["no_default_rules"])

        base_action, _scope = resolve_base_action(stack.allow_by_layer)
        engine = SelectionEngine(rules=stack.rules,
                                 groups=stack.groups,
                                 base_action=base_action)
        plan = engine.plan(
            candidates=scan.candidates(),
            pruned_roots=scan.pruned_roots(),
            warnings=scan.warnings,
            source_digests=stack.digests,
            unknown=scan.unknown,
            generation=generation,
            progress=progress,
            cancel=cancel,
        )
        can_reuse_emission = (
            previous is not None
            and inputs.get("output_path") == previous.inputs.get("output_path")
            and inputs.get("max_file_mb") == previous.inputs.get("max_file_mb")
        )
        if can_reuse_emission:
            plan = self._reapply_emission_contract(
                plan, previous, float(inputs["max_file_mb"]),
                progress=progress, cancel=cancel)
        else:
            plan = self._apply_emission_contract(
                plan, scan, base, float(inputs["max_file_mb"]),
                inputs.get("output_path"), progress=progress, cancel=cancel)
        plan = filter_plan_to_repository(plan, repository)
        return PlanResult(
            plan=plan, base_path=base, sources=sources, scan=scan,
            presets_applied=stack.presets_applied, notices=stack.notices,
            base_action=engine.base_action.value, inputs=inputs,
            rules=tuple(stack.rules), repository=repository)

    @staticmethod
    def _inherit_emission_contract(decision, previous):
        """Reapply immutable emission eligibility without touching the disk.

        Incremental replans vary only Layer 1 overrides.  Base path, output
        target, metadata and size limit are unchanged, so containment and size
        eligibility are unchanged too.  Reusing those outcomes keeps a toggle
        I/O-free while still allowing an override to change an oversize path
        from wanted/Skipped to intentionally Excluded.
        """
        emission_blocks = {
            "BLOCKED_OUTSIDE_BASE",
            "BLOCKED_ACTIVE_OUTPUT",
            "BLOCKED_MISSING_METADATA",
        }
        if previous.code in emission_blocks:
            safety = ChainEntry(
                layer=Layer.HARD_SAFETY,
                rule_id=previous.code,
                action=Action.BLOCK,
                pattern=normalise(decision.path),
                won=True,
            )
            prior = tuple(replace(item, won=False) for item in decision.chain)
            return replace(
                decision,
                state=State.BLOCKED,
                winning_rule=previous.code,
                winning_layer=Layer.HARD_SAFETY,
                chain=(safety,) + prior,
                code=previous.code,
                detail=previous.detail,
                confirm_required=False,
            )

        if (previous.state is State.SKIPPED
                and previous.code == "SKIPPED_OVERSIZE"
                and decision.state is State.INCLUDED):
            return replace(
                decision,
                state=State.SKIPPED,
                code=previous.code,
                detail=previous.detail,
                confirm_required=False,
            )
        return decision

    def _apply_emission_contract(self, plan: SelectionPlan, scan: ScanResult,
                                 base: Path, max_file_mb: float,
                                 output_path: Optional[Path],
                                 progress: Optional[ProgressSink] = None,
                                 cancel: Optional[CancelCheck] = None) -> SelectionPlan:
        """Make writer eligibility visible in the immutable plan.

        Selection rules answer whether a path is wanted.  This pass answers
        whether a wanted path can safely be emitted.  It runs before any
        content is opened and converts known writer-only surprises into P0
        blocks or explicit ``Skipped`` decisions.
        """
        index = scan.by_path()
        resolved_base = Path(base).resolve()
        absolute_base = Path(os.path.abspath(base))
        resolved_output = (Path(output_path).resolve()
                           if output_path is not None else None)
        limit_bytes = float(max_file_mb) * 1024 * 1024
        decisions = []
        total = len(plan.decisions)
        reporter = ThrottledReporter(
            progress, OP_BUNDLE, PHASE_VERIFY, "files", total=total)

        # Resolve reparse points, not every ordinary path.  Windows final-path
        # resolution calls GetFinalPathNameByHandle; doing that 79,826 times
        # consumed most of the post-discovery pause captured in the 2026-08-30
        # recording.  A cached parent walk propagates the resolved location of
        # every ancestor, so junctions and directory symlinks still cannot hide
        # an escape.  Ordinary directories are joined lexically after one
        # lstat, and file symlinks are resolved separately.
        parent_cache: Dict[str, Optional[Path]] = {}

        def is_reparse(path: Path) -> bool:
            status = os.lstat(path)
            attributes = int(getattr(status, "st_file_attributes", 0))
            return (stat.S_ISLNK(status.st_mode)
                    or bool(attributes & 0x400))  # FILE_ATTRIBUTE_REPARSE_POINT

        def resolved_parent(path: Path) -> Optional[Path]:
            key = os.path.normcase(str(path))
            if key in parent_cache:
                return parent_cache[key]
            try:
                path.relative_to(absolute_base)
                if path == absolute_base:
                    resolved = resolved_base
                else:
                    ancestor = resolved_parent(path.parent)
                    if ancestor is None:
                        raise ValueError("ancestor cannot be resolved")
                    resolved = path.resolve() if is_reparse(path) else ancestor / path.name
                resolved.relative_to(resolved_base)
            except (OSError, ValueError):
                resolved = None
            parent_cache[key] = resolved
            return resolved

        for position, decision in enumerate(plan.decisions):
            if position % 128 == 0:
                raise_if_cancelled(
                    cancel, operation=OP_BUNDLE, phase=PHASE_VERIFY,
                    completed=position, total=total)
            relative = normalise(decision.path)
            entry = index.get(relative)
            block_code = ""
            block_detail = ""

            if self._unsafe_relative(relative):
                block_code = "BLOCKED_OUTSIDE_BASE"
                block_detail = "Path is not safely relative to the selected base."
            elif entry is None:
                block_code = "BLOCKED_MISSING_METADATA"
                block_detail = "No metadata record exists for this path."
            else:
                candidate = (Path(entry.absolute) if entry.absolute
                             else resolved_base / relative)
                try:
                    absolute = Path(os.path.abspath(candidate))
                    # Reject a lexically outside candidate before touching it.
                    absolute.relative_to(absolute_base)
                    parent = resolved_parent(absolute.parent)
                    if parent is None:
                        raise ValueError("parent cannot be resolved")
                    resolved = (absolute.resolve() if is_reparse(absolute)
                                else parent / absolute.name)
                    resolved.relative_to(resolved_base)
                except (OSError, ValueError):
                    block_code = "BLOCKED_OUTSIDE_BASE"
                    block_detail = (
                        "Path resolves outside the selected base or cannot be "
                        "resolved safely.")
                else:
                    if resolved_output is not None and resolved == resolved_output:
                        block_code = "BLOCKED_ACTIVE_OUTPUT"
                        block_detail = (
                            "The active output file cannot also be an input.")

            if block_code:
                safety = ChainEntry(
                    layer=Layer.HARD_SAFETY,
                    rule_id=block_code,
                    action=Action.BLOCK,
                    pattern=relative,
                    won=True,
                )
                prior = tuple(replace(item, won=False) for item in decision.chain)
                checked = replace(
                    decision,
                    state=State.BLOCKED,
                    winning_rule=block_code,
                    winning_layer=Layer.HARD_SAFETY,
                    chain=(safety,) + prior,
                    code=block_code,
                    detail=block_detail,
                    confirm_required=False,
                )
            elif decision.state is State.INCLUDED and decision.size > limit_bytes:
                size_mb = decision.size / (1024 * 1024)
                checked = replace(
                    decision,
                    state=State.SKIPPED,
                    code="SKIPPED_OVERSIZE",
                    detail=(f"File is {size_mb:.2f} MB; the approved limit is "
                            f"{max_file_mb:.2f} MB."),
                    confirm_required=False,
                )
            else:
                checked = decision

            decisions.append(checked)

            reporter.tick(
                position + 1,
                message=f"Checked {position + 1} of {total} paths")

        raise_if_cancelled(
            cancel, operation=OP_BUNDLE, phase=PHASE_VERIFY,
            completed=total, total=total)
        reporter.close(total, message=f"Checked {total} paths")

        return replace(plan, decisions=tuple(decisions))

    def _reapply_emission_contract(self, plan: SelectionPlan,
                                   previous: PlanResult,
                                   max_file_mb: float,
                                   progress: Optional[ProgressSink] = None,
                                   cancel: Optional[CancelCheck] = None
                                   ) -> SelectionPlan:
        """Reuse immutable safety evidence when a replan did not change it.

        Presets and ordinary rules change selection, not the scanned paths,
        source base, active output, or size limit.  Re-resolving every Windows
        path in that case is both unnecessary I/O and the direct cause of the
        preset combobox freeze shown in the user's recording.
        """
        prior = {decision.path: decision
                 for decision in previous.plan.decisions}
        limit_bytes = float(max_file_mb) * 1024 * 1024
        decisions = []
        total = len(plan.decisions)
        reporter = ThrottledReporter(
            progress, OP_BUNDLE, PHASE_VERIFY, "files", total=total)

        for position, decision in enumerate(plan.decisions):
            if position % 128 == 0:
                raise_if_cancelled(
                    cancel, operation=OP_BUNDLE, phase=PHASE_VERIFY,
                    completed=position, total=total)
            prior_decision = prior.get(decision.path)
            checked = (self._inherit_emission_contract(decision, prior_decision)
                       if prior_decision is not None else decision)
            if (checked.state is State.INCLUDED
                    and checked.size > limit_bytes):
                size_mb = checked.size / (1024 * 1024)
                checked = replace(
                    checked,
                    state=State.SKIPPED,
                    code="SKIPPED_OVERSIZE",
                    detail=(f"File is {size_mb:.2f} MB; the approved limit is "
                            f"{max_file_mb:.2f} MB."),
                    confirm_required=False,
                )
            decisions.append(checked)
            reporter.tick(
                position + 1,
                message=f"Reused safety checks for {position + 1} of {total} paths")

        raise_if_cancelled(
            cancel, operation=OP_BUNDLE, phase=PHASE_VERIFY,
            completed=total, total=total)
        reporter.close(total, message=f"Checked {total} paths")
        return replace(plan, decisions=tuple(decisions))

    def explain_selection(self,
                          result: PlanResult,
                          path: Optional[str] = None,
                          fmt: str = "text") -> Union[str, Dict[str, Any]]:
        """Why one path - or every path - landed where it did.

        With no `path`, returns the whole plan. With one, returns just that
        decision and its chain. `fmt="json"` returns data rather than text so a
        caller can serialise it without re-parsing rendered output.
        """
        if fmt not in ("text", "json"):
            raise BundleFileToolError(
                f"Unknown explain format '{fmt}'. Use 'text' or 'json'.")

        if path is None:
            if fmt == "json":
                return result.to_dict()
            return "\n".join(
                line for decision in result.plan.decisions
                for line in decision.explain())

        decision = result.plan.explain(path)
        if decision is None:
            known = len(result.plan.decisions)
            raise BundleFileToolError(
                f"'{path}' is not in this plan ({known} paths were scanned). "
                f"If it sits under a pruned directory, re-plan with "
                f"--include-root to descend into it.")
        return decision.to_dict() if fmt == "json" else "\n".join(decision.explain())

    def preview_bundle(self,
                       result: PlanResult,
                       limit: int = 0) -> Dict[str, Any]:
        """A summary of what the plan would produce. Still reads nothing."""
        counts = result.plan.counts()
        paths = result.plan.ordered_paths()
        estimate = result.estimate()
        return {
            "file_count": len(paths),
            "counts": counts,
            "estimated_bytes": result.estimated_bytes(),
            "capacity_estimate": estimate.to_dict(),
            "pruned_roots": list(result.plan.pruned_roots),
            "warnings": list(result.plan.warnings),
            "notices": list(result.notices),
            "presets_applied": list(result.presets_applied),
            "base_action": result.base_action,
            "rule_stack_digest": result.plan.rule_stack_digest,
            "paths": paths[:limit] if limit else paths,
            "truncated": bool(limit and len(paths) > limit),
            "confirm_required": [d.path for d in result.plan.included()
                                 if d.confirm_required],
        }

    # -----------------------------------------------------------------
    # Plan internals
    # -----------------------------------------------------------------

    @staticmethod
    def _infer_base_path(sources: List[Path]) -> Path:
        """The common root of the sources, so relative paths mean something."""
        if len(sources) == 1:
            single = Path(sources[0])
            return single if single.is_dir() else single.parent
        resolved = [str(Path(s).resolve()) for s in sources]
        return Path(os.path.commonpath(resolved))

    def _scan_sources(self, sources: List[Path], base: Path,
                      include_roots: List[str],
                      progress: Optional[ProgressSink] = None,
                      cancel: Optional[CancelCheck] = None,
                      prune_dir_names: Optional[List[str]] = None) -> ScanResult:
        """One merged metadata index across every source."""
        merged = ScanResult()
        seen: Dict[str, None] = {}
        for source in sources:
            partial = scan_metadata(Path(source), base, progress=progress,
                                    cancel=cancel, unprune=include_roots,
                                    prune_dir_names=prune_dir_names or ())
            for entry in partial.entries:
                if entry.path not in seen:
                    seen[entry.path] = None
                    merged.entries.append(entry)
            merged.warnings.extend(partial.warnings)
            merged.unknown.update(partial.unknown)
            merged.scanned += partial.scanned
            for relative, finding in partial.ledger.pruned.items():
                merged.ledger.record(relative, finding)
            for relative, finding in partial.ledger.ambiguous.items():
                merged.ledger.record(relative, finding)
        merged.entries.sort(key=lambda entry: entry.path)
        return merged

    def _planning_prune_names(self, presets: List[str], *,
                              no_default_rules: bool) -> List[str]:
        """Whole-subtree names the metadata scanner may safely skip."""
        patterns: List[str] = []
        if not no_default_rules:
            patterns.extend(self._setting("safety.deny_globs", []) or [])
        configured = self._setting("selection.presets", {}) or {}
        catalogue = available_presets(configured)
        for name in presets:
            body = catalogue.get(name)
            if body is None:
                # Preserve the normal fail-loud error wording and alternatives.
                preset_rules([name], configured)
                continue
            patterns.extend(body.get("deny", ()) or ())
        return sorted(prunable_dir_names(patterns))

    def _build_rule_stack(self, preset: List[str], rules: Optional[Path],
                          include: List[str], exclude: List[str],
                          force_include: List[str], force_exclude: List[str],
                          groups: List[str],
                          no_default_rules: bool,
                          overrides: Optional[List] = None) -> RuleStack:
        """Assemble every layer of the ladder, lowest priority first.

        Order of assembly does not decide precedence - the layer on each rule
        does - but building it bottom-up keeps the code readable against the
        specification's own table.
        """
        stack = RuleStack()

        # Layer 5: governed defaults from bundle_config.json.
        if no_default_rules:
            stack.notices.append(
                "Default rules disabled: only presets, rules files and "
                "command-line patterns are in effect. Priority 0 safety "
                "blocks still apply.")
        else:
            allow = list(self._setting("safety.allow_globs", ["**/*"]) or ["**/*"])
            deny = list(self._setting("safety.deny_globs", []) or [])
            for pattern in allow:
                stack.add_allow(Layer.GOVERNED_DEFAULT, pattern)
            stack.extend(rules_from_globs(allow, deny))
            stack.digests.append(
                ("governed:safety", rule_source_digest({"allow": allow, "deny": deny})))

        # Layer 4: shipped and configured presets.
        if preset:
            configured = self._setting("selection.presets", {}) or {}
            merged = preset_rules(preset, configured)
            stack.extend(merged.rules)
            stack.merge_allow(merged)
            stack.digests.extend(merged.digests)
            stack.presets_applied.extend(merged.presets_applied)
            stack.notices.extend(merged.notices)

        # Layer 2a: project rules file.
        if rules is not None:
            loaded = load_rules_file(Path(rules))
            stack.extend(loaded.rules)
            stack.merge_allow(loaded)
            stack.groups.extend(loaded.groups)
            stack.digests.extend(loaded.digests)
            stack.notices.extend(loaded.notices)

        # Layer 2b: command line.
        command = cli_rules(include, exclude)
        stack.extend(command.rules)
        stack.merge_allow(command)
        stack.notices.extend(command.notices)
        if include or exclude:
            stack.digests.append(
                ("cli", rule_source_digest({"include": list(include),
                                            "exclude": list(exclude)})))

        # Layer 1: session overrides.
        session = session_rules(force_include, force_exclude, overrides or [])
        stack.extend(session.rules)
        if force_include or force_exclude or overrides:
            stack.digests.append(
                ("session", rule_source_digest(
                    {"force_include": list(force_include),
                     "force_exclude": list(force_exclude),
                     "overrides": [list(o) for o in (overrides or [])]})))

        # Groups affect emission order only, never inclusion.
        if groups:
            stack.groups.extend(parse_group_specs(groups))

        return stack

    def presets(self) -> Dict[str, Dict[str, Any]]:
        """Every preset this installation offers, shipped plus configured."""
        return available_presets(self._setting("selection.presets", {}) or {})
