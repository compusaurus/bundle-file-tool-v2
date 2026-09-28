# BFT_B106_PROGRESS_CONTRACT_TESTS
# ============================================================================
# SOURCEFILE: test_progress_contract.py
# RELPATH: bundle_file_tool_v2/tests/unit/test_progress_contract.py
# PROJECT: Bundle File Tool v2.1
# VERSION: 2.1.106
# LIFECYCLE: Testing
# STATUS: Build 106 - BFT_B106_PROGRESS_CONTRACT_TESTS
# ============================================================================
"""The OperationProgress contract.

Paul's Build 104 review asked for a serializable, BFT-owned progress event that
the CLI, Tkinter and Web adapters can all render, and noted that BFT could not
yet supply a rising discovery count because `discover_files()` returned a
finished list with no visibility into the walk.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from core.progress import (
    MODE_DETERMINATE,
    MODE_INDETERMINATE,
    OP_BUNDLE,
    PHASE_DISCOVER,
    PHASE_READ,
    OperationProgress,
    ProgressRecorder,
    emit,
)
from core.writer import BundleCreator


@pytest.fixture
def tree(tmp_path):
    (tmp_path / "pkg").mkdir()
    for rel in ("a.py", "b.py", "pkg/c.py"):
        (tmp_path / rel).write_text("X = 1\n", encoding="utf-8")
    (tmp_path / "skip.log").write_text("noise\n", encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# The event itself
# ---------------------------------------------------------------------------

def test_mode_follows_whether_a_total_is_known():
    assert OperationProgress(OP_BUNDLE, PHASE_DISCOVER, current=7).mode == MODE_INDETERMINATE
    assert OperationProgress(OP_BUNDLE, PHASE_READ, current=7, total=10).mode == MODE_DETERMINATE


def test_percent_is_none_when_unknown_never_zero():
    """A renderer given 0.0 draws an empty bar and implies 'nothing yet'.

    The honest answer when there is no total is 'unknown', so percent is None.
    """
    assert OperationProgress(OP_BUNDLE, PHASE_DISCOVER, current=99).percent is None
    assert OperationProgress(OP_BUNDLE, PHASE_READ, current=5, total=10).percent == 50.0


def test_percent_is_clamped_and_safe_at_zero_total():
    assert OperationProgress(OP_BUNDLE, PHASE_READ, current=99, total=10).percent == 100.0
    assert OperationProgress(OP_BUNDLE, PHASE_READ, current=1, total=0).percent is None


def test_event_is_immutable():
    event = OperationProgress(OP_BUNDLE, PHASE_READ, current=1, total=2)
    with pytest.raises(Exception):
        event.current = 5           # type: ignore[misc]


def test_event_serializes_with_derived_fields():
    """A web adapter on the far side of a socket cannot call a property."""
    payload = OperationProgress(OP_BUNDLE, PHASE_READ, current=3, total=4,
                                unit="files", message="hi").to_dict()
    assert payload == {
        "operation": "bundle", "phase": "read", "mode": "determinate",
        "current": 3, "total": 4, "unit": "files", "message": "hi", "percent": 75.0,
    }
    import json
    json.dumps(payload)             # must be JSON-serializable


# ---------------------------------------------------------------------------
# A sink must never break the work
# ---------------------------------------------------------------------------

def test_emit_tolerates_a_missing_sink():
    emit(None, OperationProgress(OP_BUNDLE, PHASE_READ))


def test_emit_swallows_a_failing_sink():
    def hostile(_event):
        raise RuntimeError("sink exploded")

    emit(hostile, OperationProgress(OP_BUNDLE, PHASE_READ))


def test_a_failing_sink_does_not_abort_discovery(tree):
    """Reporting is secondary to the work being reported on."""
    def hostile(_event):
        raise RuntimeError("sink exploded")

    files = BundleCreator(allow_globs=["**/*.py"]).discover_files(
        tree, base_path=tree, progress=hostile)
    assert len(files) == 3


# ---------------------------------------------------------------------------
# Discovery: the rising count that therm needs
# ---------------------------------------------------------------------------

def test_discovery_emits_a_rising_indeterminate_count(tree):
    recorder = ProgressRecorder()
    BundleCreator(allow_globs=["**/*.py"]).discover_files(
        tree, base_path=tree, progress=recorder)

    discovery = [e for e in recorder.events if e.phase == PHASE_DISCOVER]
    assert discovery, "discovery emitted no progress"

    counts = [e.current for e in discovery]
    assert counts == sorted(counts), "the count must rise monotonically"
    assert counts[-1] == 3

    # every event but the last has no total; the last one does
    assert all(e.mode == MODE_INDETERMINATE for e in discovery[:-1])
    assert discovery[-1].mode == MODE_DETERMINATE
    assert discovery[-1].total == 3


def test_discovery_count_excludes_filtered_files(tree):
    recorder = ProgressRecorder()
    BundleCreator(allow_globs=["**/*.py"]).discover_files(
        tree, base_path=tree, progress=recorder)
    assert recorder.last_for(PHASE_DISCOVER).current == 3   # skip.log not counted


def test_read_phase_is_determinate_from_the_first_event(tree):
    creator = BundleCreator(allow_globs=["**/*.py"])
    files = creator.discover_files(tree, base_path=tree)

    recorder = ProgressRecorder()
    creator.create_manifest(files, tree, "plain_marker", progress=recorder)

    read = [e for e in recorder.events if e.phase == PHASE_READ]
    assert len(read) == 4
    assert all(e.mode == MODE_DETERMINATE and e.total == 3 for e in read)
    assert [e.current for e in read] == [0, 1, 2, 3]


def test_phases_arrive_in_order(tree):
    recorder = ProgressRecorder()
    creator = BundleCreator(allow_globs=["**/*.py"])
    files = creator.discover_files(tree, base_path=tree, progress=recorder)
    creator.create_manifest(files, tree, "plain_marker", progress=recorder)
    assert recorder.phases() == [PHASE_DISCOVER, PHASE_READ]


def test_progress_is_entirely_optional(tree):
    """Every call site must work with no sink at all."""
    creator = BundleCreator(allow_globs=["**/*.py"])
    files = creator.discover_files(tree, base_path=tree)
    manifest = creator.create_manifest(files, tree, "plain_marker")
    assert len(manifest.entries) == 3


# ---------------------------------------------------------------------------
# The core must stay renderer-agnostic
# ---------------------------------------------------------------------------

def test_progress_module_imports_no_interface():
    """No toolkit, no therm, no printing. An event is data."""
    source = (Path(__file__).resolve().parents[2]
              / "src" / "core" / "progress.py").read_text(encoding="utf-8")
    for forbidden in ("import tkinter", "import therm", "from therm", "import flask"):
        assert forbidden not in source.lower(), f"core progress imports {forbidden}"
