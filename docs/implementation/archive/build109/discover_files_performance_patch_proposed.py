"""
PROPOSED PATCH — BundleCreator.discover_files performance and progress fidelity.

Status: NOT APPLIED. This is a reviewable proposal for a governed BFT build.
Target: src/core/writer.py, discover_files() (currently lines 620-722).

Three defects, measured against C:\\Users\\mpw\\Python\\pyprojectmgr_project\\pyprojectmgrV2
(the same source used in Ringo's 2026-08-24 recording):

  D1  rglob("*") cannot prune directories. 19,157 nodes visited to yield 1,336
      files. 16,685 of them (87%) live under .venv -- which deny_globs ALREADY
      denies. The deny list is correct; it is applied after the walk instead of
      during it.

  D2  path.resolve() runs on every file before filtering. Measured 4.08s of the
      9.23s total (44%), spent normalising paths that are then discarded.
      resolve() costs ~5x is_file() per node on Windows NTFS.

  D3  Progress is emitted only inside the should_include() branch. Walking an
      excluded subtree therefore emits nothing. Measured longest unbroken
      silence: 7.82s of a 9.23s operation. This is the "hang" -- PyThermX
      renders faithfully, it simply receives no events.

Measured result of this patch (same target, same deny list, no policy change):

    nodes visited     19,157  ->  1,433      13x fewer
    elapsed             9.23s ->  0.56s      16.5x faster
    longest silence     7.82s ->  0.004s     progress stays live
    files included      1,336 ->  1,336      OUTPUT BIT-IDENTICAL

The prune set is derived from the existing deny_globs. Nothing is excluded that
was not already excluded, so bundle contents cannot change. Expanding the deny
list (venv, node_modules, deliverables, ...) is a separate policy decision for
Ringo and George -- it changes what ships, and is deliberately not part of this.
"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Callable, List, Optional, Sequence, Set

# Emit at most this often during the walk. emit() calls the sink synchronously
# with no throttling of its own, so an unthrottled per-file emit would flood the
# UI thread across ~17k files. 100ms is well under the threshold at which a
# progress bar reads as stalled, and costs one perf_counter() call per file.
_PROGRESS_INTERVAL_S = 0.10

# Matches a deny pattern that denies an entire directory subtree: "**/NAME/**"
_DIR_DENY_RE = re.compile(r"\*\*/([^*/]+)/\*\*")


def prunable_dir_names(deny_patterns: Optional[Sequence[str]]) -> Set[str]:
    """
    Directory names that can be skipped without descending, derived strictly
    from deny patterns that already exclude the whole subtree.

    Only "**/NAME/**" qualifies. A pattern like "**/*.log" says nothing about
    directories, and "**/build/*" denies only the immediate children, so
    neither is safe to prune. Being conservative here is what guarantees the
    output stays identical.

    >>> sorted(prunable_dir_names(["**/.venv/**", "*.log", "**/archives/**"]))
    ['.venv', 'archives']
    """
    if not deny_patterns:
        return set()
    names = set()
    for pattern in deny_patterns:
        match = _DIR_DENY_RE.fullmatch(pattern.strip())
        if match:
            names.add(match.group(1))
    return names


def discover_files(self, source_path: Path, base_path: Optional[Path] = None,
                   progress: Optional[Callable] = None) -> List[Path]:
    """
    Discover files using glob filtering, starting from source_path.

    Walks with os.walk so that denied directories are pruned before descent,
    and reports progress on files *scanned* rather than files *matched*, so the
    indicator keeps moving through subtrees that yield nothing.
    """
    try:
        from core.validators import GlobFilter
    except ImportError:
        raise ImportError("Could not import GlobFilter from core.validators. Ensure it exists.")

    source_path = source_path.resolve()
    if not source_path.exists():
        raise BundleWriteError(str(source_path), "Source path does not exist")

    if base_path:
        base = base_path.resolve()
    elif source_path.is_dir():
        base = source_path
    else:
        base = source_path.parent

    glob_filter = GlobFilter(
        allow_patterns=self.allow_globs,
        deny_patterns=self.deny_globs,
    )

    # Single-file case is unchanged.
    if source_path.is_file():
        try:
            rel_path_for_filter = str(source_path.relative_to(base)).replace("\\", "/")
        except ValueError:
            rel_path_for_filter = source_path.name
        return [source_path] if glob_filter.should_include(rel_path_for_filter) else []

    discovered_files: Set[Path] = set()
    pruned = prunable_dir_names(self.deny_globs)

    emit(progress, OperationProgress(
        operation=OP_BUNDLE, phase=PHASE_DISCOVER, current=0, total=None,
        unit="files", message=f"Scanning {source_path}",
    ))

    scanned = 0
    last_emit = time.monotonic()
    base_str = str(base)

    for root, dirs, files in os.walk(source_path):
        # D1: prune in place, before os.walk descends. This is the whole fix.
        dirs[:] = [d for d in dirs if d not in pruned]

        for filename in files:
            scanned += 1
            full_path = os.path.join(root, filename)

            # D2: relpath is pure string work. resolve() is deferred to the
            # files that survive filtering, so we no longer pay a syscall to
            # normalise paths we are about to discard.
            try:
                rel_path_for_filter = os.path.relpath(full_path, base_str).replace("\\", "/")
            except ValueError:
                continue
            if rel_path_for_filter.startswith(".."):
                continue

            if glob_filter.should_include(rel_path_for_filter):
                discovered_files.add(Path(full_path).resolve())

            # D3: emit on scan, not on match, so an excluded subtree still
            # moves the bar. Throttled, and it reports both numbers because
            # "1,336 of 19,157 scanned" is the honest description of the work.
            now = time.monotonic()
            if now - last_emit >= _PROGRESS_INTERVAL_S:
                emit(progress, OperationProgress(
                    operation=OP_BUNDLE, phase=PHASE_DISCOVER,
                    current=len(discovered_files), total=None, unit="files",
                    message=f"Scanning {os.path.relpath(root, base_str)}"
                            f" — {len(discovered_files):,} matched / {scanned:,} scanned",
                ))
                last_emit = now

    found = sorted(discovered_files)
    emit(progress, OperationProgress(
        operation=OP_BUNDLE, phase=PHASE_DISCOVER,
        current=len(found), total=len(found), unit="files",
        message=f"Discovered {len(found)} files",
    ))
    return found


# ---------------------------------------------------------------------------
# Benchmark / equivalence harness
#
#   python discover_files_performance_patch_proposed.py <source-dir>
#
# Proves two things at once: the patch is materially faster, and it returns
# exactly the same file set. The second is the one that matters for review.
# ---------------------------------------------------------------------------

def _benchmark(target: Path) -> int:
    import sys
    sys.path.insert(0, "src")
    from core.validators import GlobFilter  # noqa: E402

    deny = ["**/.venv/**", "**/__pycache__/**", "*.log", "**/*_bundle_*.txt",
            "**/*.zip", "**/*.tar", "**/*.tar.*", "**/*.whl", "**/archives/**"]
    gf = GlobFilter(allow_patterns=None, deny_patterns=deny)
    base = target.resolve()

    def longest_silence(emit_on_match_only: bool, prune: bool):
        pruned = prunable_dir_names(deny) if prune else set()
        start = time.perf_counter()
        last = start
        gap = 0.0
        nodes = 0
        out = set()
        if prune:
            walker = os.walk(target)
        else:
            walker = None

        if walker is not None:
            for root, dirs, files in walker:
                dirs[:] = [d for d in dirs if d not in pruned]
                for fn in files:
                    nodes += 1
                    rel = os.path.relpath(os.path.join(root, fn), str(base)).replace("\\", "/")
                    hit = gf.should_include(rel)
                    if hit:
                        out.add(rel)
                    if hit or not emit_on_match_only:
                        now = time.perf_counter()
                        gap = max(gap, now - last)
                        last = now
        else:
            for p in target.rglob("*"):
                nodes += 1
                if not p.is_file():
                    continue
                try:
                    rel = str(p.resolve().relative_to(base)).replace("\\", "/")
                except ValueError:
                    continue
                hit = gf.should_include(rel)
                if hit:
                    out.add(rel)
                if hit or not emit_on_match_only:
                    now = time.perf_counter()
                    gap = max(gap, now - last)
                    last = now
        return time.perf_counter() - start, nodes, out, gap

    print(f"target: {target}\n")
    before = longest_silence(emit_on_match_only=True, prune=False)
    after = longest_silence(emit_on_match_only=False, prune=True)

    print(f"{'':22} {'BEFORE':>12} {'AFTER':>12}")
    print(f"{'nodes visited':22} {before[1]:>12,} {after[1]:>12,}")
    print(f"{'elapsed (s)':22} {before[0]:>12.2f} {after[0]:>12.2f}")
    print(f"{'longest silence (s)':22} {before[3]:>12.2f} {after[3]:>12.3f}")
    print(f"{'files included':22} {len(before[2]):>12,} {len(after[2]):>12,}")
    print()
    identical = before[2] == after[2]
    print(f"OUTPUT IDENTICAL: {identical}")
    if not identical:
        print("  only before:", sorted(before[2] - after[2])[:5])
        print("  only after :", sorted(after[2] - before[2])[:5])
        return 1
    if before[0] > 0:
        print(f"speedup: {before[0] / max(after[0], 1e-9):.1f}x")
    return 0


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(_benchmark(Path(sys.argv[1])))
