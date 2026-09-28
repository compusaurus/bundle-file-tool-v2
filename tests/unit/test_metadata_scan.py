# BFT_B114_METADATA_SCAN_TESTS
# ============================================================================
# SOURCEFILE: test_metadata_scan.py
# RELPATH: bundle_file_tool_v2/tests/unit/test_metadata_scan.py
# PROJECT: Bundle File Tool v2.2
# VERSION: 2.1.114
# LIFECYCLE: Testing
# STATUS: Build 114 - WP3 - BFT_B114_METADATA_SCAN_TESTS
# ============================================================================
"""The scan that opens nothing and prunes before it descends.

Two properties carry the whole design and are asserted here rather than
assumed: the scan never reads content, and a classified directory is skipped
*before* its children are touched. If either fails, planning stops being cheap
and the workspace loses the premise it was designed on.
"""

from __future__ import annotations

import builtins
import os

import pytest

from core.cancellation import CancelRecorder, OperationCancelled
from core.metadata_scan import PathMetadata, scan_metadata, scan_subtree
from core.progress import PHASE_DISCOVER, ProgressRecorder


@pytest.fixture
def tree(tmp_path):
    """A project with one real environment and one ambiguous directory."""
    # write_bytes, not write_text: on Windows text mode translates "\n" into
    # "\r\n", so a size assertion written against the source literal is off by
    # one per line and would bake a platform quirk into the expectation.
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_bytes(b"print(1)\n")
    (tmp_path / "src" / "util.py").write_bytes(b"x = 2\n")
    (tmp_path / "readme.md").write_bytes(b"# hi\n")

    env = tmp_path / ".venv312"
    (env / "Scripts").mkdir(parents=True)
    (env / "Lib" / "site-packages" / "pytest").mkdir(parents=True)
    (env / "pyvenv.cfg").write_text("home = C:\\Python312\n", encoding="utf-8")
    (env / "Scripts" / "python.exe").write_bytes(b"MZ")
    for index in range(25):
        (env / "Lib" / "site-packages" / "pytest" / f"m{index}.py").write_text(
            "pass\n", encoding="utf-8")

    # A checked-in activate script with no interpreter beside it: ambiguous.
    ambiguous = tmp_path / "tools"
    (ambiguous / "bin").mkdir(parents=True)
    (ambiguous / "bin" / "activate").write_text("# shim\n", encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# The two load-bearing properties
# ---------------------------------------------------------------------------

def test_the_scan_opens_no_file(tree):
    real_open = builtins.open
    opened = []

    def watched(file, *args, **kwargs):
        opened.append(str(file))
        return real_open(file, *args, **kwargs)

    builtins.open = watched
    try:
        scan_metadata(tree)
    finally:
        builtins.open = real_open

    assert [p for p in opened if str(tree) in p] == []


def test_a_classified_environment_is_pruned_before_descent(tree, monkeypatch):
    """Not merely absent from the result - never statted.

    Filtering after the walk would give the same file list at a cost that
    scales with the environment, which on a real tree is most of the tree.
    """
    statted = []
    real_stat = os.stat

    def watched(path, *args, **kwargs):
        statted.append(str(path))
        return real_stat(path, *args, **kwargs)

    monkeypatch.setattr(os, "stat", watched)
    result = scan_metadata(tree)

    # The detector *must* probe marker files to classify the directory at all -
    # that is what makes recognition signature-based rather than name-based.
    # The property that matters is that the classification is where the cost
    # stops: none of the 25 files the environment contains is ever touched.
    contents = [p for p in statted if "site-packages" in p]
    assert contents == [], f"pruned subtree contents were statted: {contents[:3]}"

    probes = [p for p in statted if ".venv312" in p]
    assert len(probes) < 10, (
        f"classification cost must be bounded per directory, saw {len(probes)}")
    assert ".venv312" in result.pruned_roots()


def test_the_ambiguous_directory_is_traversed_and_indexed(tree):
    """A lone `bin/activate` must not silently take its subtree with it."""
    result = scan_metadata(tree)
    assert "tools/bin/activate" in [entry.path for entry in result.entries]
    assert "tools" not in result.pruned_roots()
    assert any("tools" in path for path in result.ledger.ambiguous)


# ---------------------------------------------------------------------------
# Shape of the result
# ---------------------------------------------------------------------------

def test_paths_are_normalised_relative_and_sorted(tree):
    result = scan_metadata(tree)
    paths = [entry.path for entry in result.entries]
    assert paths == sorted(paths)
    assert all(not p.startswith("/") and "\\" not in p for p in paths)
    assert "src/app.py" in paths


def test_sizes_are_recorded_without_reading(tree):
    result = scan_metadata(tree)
    index = result.by_path()
    assert index["src/app.py"].size == len("print(1)\n")


def test_candidates_are_path_size_pairs(tree):
    result = scan_metadata(tree)
    assert ("src/app.py", 9) in result.candidates()


def test_a_base_path_makes_paths_relative_to_it(tree):
    result = scan_metadata(tree / "src", base_path=tree)
    assert sorted(e.path for e in result.entries) == ["src/app.py", "src/util.py"]


def test_a_single_file_source_is_relative_to_its_parent(tree):
    result = scan_metadata(tree / "readme.md")
    assert [entry.path for entry in result.entries] == ["readme.md"]
    assert result.scanned == 1


def test_a_single_file_honours_an_explicit_base(tree):
    result = scan_metadata(tree / "src" / "app.py", base_path=tree)
    assert [entry.path for entry in result.entries] == ["src/app.py"]


def test_an_empty_directory_scans_to_an_empty_result(tmp_path):
    result = scan_metadata(tmp_path)
    assert result.entries == [] and result.scanned == 0


# ---------------------------------------------------------------------------
# Overrides
# ---------------------------------------------------------------------------

def test_include_root_descends_into_a_directory_that_would_be_pruned(tree):
    """The ghost-children case. Crossing into a pruned tree is possible, but
    only because the operator asked for it by name."""
    result = scan_metadata(tree, unprune=[".venv312"])
    inside = [e.path for e in result.entries if e.path.startswith(".venv312/")]
    assert inside, "the un-pruned root was still skipped"
    assert ".venv312" not in result.pruned_roots()


def test_unprune_normalises_the_root_it_is_given(tree):
    result = scan_metadata(tree, unprune=[".venv312/"])
    assert any(e.path.startswith(".venv312/") for e in result.entries)


def test_scan_subtree_targets_one_directory_against_the_original_base(tree):
    result = scan_subtree(tree / "src", tree)
    assert sorted(e.path for e in result.entries) == ["src/app.py", "src/util.py"]


# ---------------------------------------------------------------------------
# Progress and cancellation
# ---------------------------------------------------------------------------

def test_discovery_progress_closes_determinate(tree):
    recorder = ProgressRecorder()
    result = scan_metadata(tree, progress=recorder)
    discover = [e for e in recorder.events if e.phase == PHASE_DISCOVER]
    assert discover, "no discovery progress was emitted"
    assert discover[-1].current == len(result.entries)
    assert discover[-1].total == len(result.entries)


def test_progress_never_goes_backwards(tree):
    recorder = ProgressRecorder()
    scan_metadata(tree, progress=recorder)
    currents = [e.current for e in recorder.events]
    assert currents == sorted(currents)


def test_cancellation_stops_the_walk_and_names_the_phase(tree):
    with pytest.raises(OperationCancelled) as error:
        scan_metadata(tree, cancel=CancelRecorder(after=0))
    assert error.value.phase == PHASE_DISCOVER


def test_a_scan_without_cancellation_completes(tree):
    assert scan_metadata(tree, cancel=None).entries


# ---------------------------------------------------------------------------
# Failure handling
# ---------------------------------------------------------------------------

def test_an_unreadable_file_becomes_unknown_rather_than_vanishing(tree, monkeypatch):
    """A file the tool could not stat must still appear, marked, because a
    silently absent file is indistinguishable from one that was excluded."""
    real_stat = os.stat

    def failing(path, *args, **kwargs):
        if str(path).endswith("util.py"):
            raise PermissionError(13, "Access is denied")
        return real_stat(path, *args, **kwargs)

    monkeypatch.setattr(os, "stat", failing)
    result = scan_metadata(tree)

    assert "src/util.py" in [entry.path for entry in result.entries]
    assert "src/util.py" in result.unknown
    assert any("util.py" in warning for warning in result.warnings)


def test_a_walk_error_is_recorded_as_a_warning(tree, monkeypatch):
    real_walk = os.walk

    def erroring(top, **kwargs):
        onerror = kwargs.get("onerror")
        if onerror is not None:
            onerror(OSError(5, "Access is denied", str(top)))
        return real_walk(top, **kwargs)

    monkeypatch.setattr(os, "walk", erroring)
    result = scan_metadata(tree)
    assert result.warnings
    assert all(isinstance(warning, str) for warning in result.warnings)
    assert result.unknown

    import json
    json.dumps(result.warnings)


def test_path_metadata_defaults_are_inert():
    entry = PathMetadata(path="a.py")
    assert entry.as_candidate() == ("a.py", 0)
    assert entry.mtime_ns == 0 and entry.absolute == ""
