"""Build 110 acceptance gates — discovery performance and oversize handling.

Ratified by ARCH-RULING-2026-08-24-01 (George), from the forensic analysis in
`docs/bft_discovery_performance_analysis_john.md`.

Three defects are pinned here:

  PERF-BFT-001  discovery walked into directories the deny list already
                excluded, because rglob("*") cannot prune.
  PERF-BFT-002  progress was emitted only on *matched* files, so a dense
                excluded subtree produced a measured 13.15s of silence.
  UX-BFT-001    one oversized file raised FileSizeError and aborted the whole
                manifest, making every other discovered file unbundlable.

The equivalence test is the important one: pruning is only safe because it
cannot change which files are discovered.
"""

import time
from pathlib import Path

import pytest

from core.validators import GlobFilter
from core.writer import BundleCreator, prunable_dir_names


DENY = [
    "**/.venv/**",
    "**/node_modules/**",
    "**/__pycache__/**",
    "**/archives/**",
    "*.log",
]


def _build_tree(root: Path, noise_files: int = 400) -> None:
    """A source tree whose bulk sits inside denied directories.

    Mirrors the shape that produced the original hang: a handful of real
    source files beside a large virtualenv that the deny list already covers.
    """
    (root / "src").mkdir(parents=True)
    (root / "src" / "app.py").write_text("print('app')\n", encoding="utf-8")
    (root / "src" / "util.py").write_text("print('util')\n", encoding="utf-8")
    (root / "README.md").write_text("# readme\n", encoding="utf-8")
    (root / "debug.log").write_text("noise\n", encoding="utf-8")

    # The bulk: denied, deeply nested, and containing nothing that matches.
    deep = root / ".venv" / "Lib" / "site-packages" / "pkg"
    deep.mkdir(parents=True)
    for i in range(noise_files):
        (deep / f"mod_{i}.py").write_text("x = 1\n", encoding="utf-8")

    nm = root / "node_modules" / "dep"
    nm.mkdir(parents=True)
    for i in range(noise_files // 4):
        (nm / f"n_{i}.js").write_text("var x=1;\n", encoding="utf-8")


def _legacy_discover(creator: BundleCreator, source: Path) -> set:
    """The pre-Build-110 algorithm, verbatim, as the equivalence baseline."""
    base = source.resolve()
    gf = GlobFilter(allow_patterns=creator.allow_globs, deny_patterns=creator.deny_globs)
    found = set()
    for path in source.rglob("*"):
        if not path.is_file():
            continue
        abs_path = path.resolve()
        try:
            rel = str(abs_path.relative_to(base)).replace("\\", "/")
        except ValueError:
            continue
        if gf.should_include(rel):
            found.add(abs_path)
    return found


@pytest.fixture()
def source_tree(tmp_path: Path) -> Path:
    root = tmp_path / "workspace"
    _build_tree(root)
    return root


@pytest.fixture()
def creator() -> BundleCreator:
    return BundleCreator(allow_globs=["**/*"], deny_globs=DENY, max_file_mb=10)


# ---------------------------------------------------------------------------
# PERF-BFT-001 — purity assertion
# ---------------------------------------------------------------------------

def test_discover_files_output_identical_to_unpruned_baseline(creator, source_tree):
    """Pruning must not change which files are discovered.

    This is the gate that makes the optimisation safe to ship: the prune set is
    derived from deny patterns that already excluded those trees, so the
    surviving file set has to be byte-for-byte the same as the old walk's.
    """
    baseline = _legacy_discover(creator, source_tree)
    actual = set(creator.discover_files(source_tree))

    assert actual == baseline, (
        "pruned discovery changed the file set; "
        f"only-baseline={sorted(str(p) for p in baseline - actual)[:5]} "
        f"only-actual={sorted(str(p) for p in actual - baseline)[:5]}"
    )
    # Sanity: the fixture must actually exercise the denied trees, otherwise
    # this test would pass trivially on an empty comparison.
    assert baseline, "fixture produced no included files"
    assert not any(".venv" in str(p) for p in actual)
    assert not any("node_modules" in str(p) for p in actual)


def test_prunable_dir_names_only_accepts_whole_subtree_patterns():
    """Only `**/NAME/**` is safe to prune on.

    `**/build/*` denies immediate children but not the subtree, and `*.log`
    says nothing about directories. Pruning on either would drop files the
    deny list still permits.
    """
    derived = prunable_dir_names([
        "**/.venv/**",      # safe
        "**/archives/**",   # safe
        "**/build/*",       # NOT safe - children only
        "*.log",            # NOT safe - not a directory pattern
        "**/*_bak*/**",     # NOT safe - contains a wildcard in the name
    ])
    assert derived == {".venv", "archives"}
    assert prunable_dir_names(None) == set()
    assert prunable_dir_names([]) == set()


def test_discover_files_does_not_descend_into_denied_directories(creator, source_tree, monkeypatch):
    """The denied subtree must never be walked, not merely filtered afterwards."""
    import os as _os

    walked = []
    real_walk = _os.walk

    def spy(top, *args, **kwargs):
        for root, dirs, files in real_walk(top, *args, **kwargs):
            walked.append(root)
            yield root, dirs, files

    monkeypatch.setattr("core.writer.os.walk", spy)
    creator.discover_files(source_tree)

    assert not any(".venv" in w for w in walked), "descended into .venv despite deny pattern"
    assert not any("node_modules" in w for w in walked), "descended into node_modules"


# ---------------------------------------------------------------------------
# PERF-BFT-002 — telemetry continuity
# ---------------------------------------------------------------------------

def test_discover_files_max_telemetry_gap_under_250ms(creator, source_tree):
    """Progress must keep flowing while walking subtrees that match nothing.

    Before Build 110 the emit() call sat inside the should_include() branch, so
    a dense excluded tree produced no events at all. The ratified ceiling is
    250ms between events during the discover phase.
    """
    stamps = []

    def sink(_event):
        stamps.append(time.monotonic())

    start = time.monotonic()
    creator.discover_files(source_tree, progress=sink)
    end = time.monotonic()

    assert stamps, "discovery emitted no progress events at all"

    boundaries = [start] + stamps + [end]
    gaps = [b - a for a, b in zip(boundaries, boundaries[1:])]
    worst = max(gaps)

    assert worst < 0.250, f"longest telemetry gap {worst:.3f}s exceeds the 250ms ceiling"


def test_discover_files_reports_scanned_and_included_counts(creator, source_tree):
    """The message must distinguish work done from files matched.

    Reporting only matched files made throughput read as 117 files/s while the
    walk was reading thousands per second - the number described the wrong
    quantity and implied a disk problem that did not exist.
    """
    messages = []

    def sink(event):
        if getattr(event, "message", None):
            messages.append(event.message)

    creator.discover_files(source_tree, progress=sink)
    dual = [m for m in messages if "included" in m and "scanned" in m]
    assert dual, f"no dual-counter progress message emitted; saw {messages[:3]}"


# ---------------------------------------------------------------------------
# UX-BFT-001 — oversize files are skipped, not fatal
# ---------------------------------------------------------------------------

def test_oversized_file_warns_and_allows_bundling(tmp_path):
    """An oversized file must not prevent bundling everything else.

    Regression for the behaviour in Ringo's 2026-08-24 recording: a single
    20.58 MB asset raised FileSizeError, which the GUI turned into a blank
    preview and a disabled Create Bundle button across 1,335 healthy files.
    """
    root = tmp_path / "ws"
    root.mkdir()
    (root / "small_a.txt").write_text("a" * 1024, encoding="utf-8")
    (root / "small_b.txt").write_text("b" * 1024, encoding="utf-8")
    big = root / "huge.bin"
    big.write_bytes(b"\x00" * (2 * 1024 * 1024))  # 2 MB against a 1 MB limit

    creator = BundleCreator(allow_globs=["**/*"], deny_globs=[], max_file_mb=1)
    files = creator.discover_files(root)
    assert big.resolve() in set(files), "oversize file should still be discovered"

    manifest = creator.create_manifest(files, root, "plain_marker")

    included = {e.path for e in manifest.entries}
    assert included == {"small_a.txt", "small_b.txt"}, "healthy files were not bundled"

    assert len(manifest.skipped_entries) == 1
    skipped = manifest.skipped_entries[0]
    assert skipped["path"] == "huge.bin"
    assert skipped["reason"] == "oversize"
    assert skipped["size_mb"] == pytest.approx(2.0, abs=0.05)
    assert skipped["limit_mb"] == 1.0
    assert manifest.metadata["skipped_count"] == 1


def test_manifest_without_oversize_reports_no_skips(tmp_path):
    """The common case must be unchanged: nothing skipped, empty list."""
    root = tmp_path / "ws"
    root.mkdir()
    (root / "only.txt").write_text("hello", encoding="utf-8")

    creator = BundleCreator(allow_globs=["**/*"], deny_globs=[], max_file_mb=10)
    manifest = creator.create_manifest(creator.discover_files(root), root, "plain_marker")

    assert manifest.skipped_entries == []
    assert manifest.metadata["skipped_count"] == 0
    assert len(manifest.entries) == 1
