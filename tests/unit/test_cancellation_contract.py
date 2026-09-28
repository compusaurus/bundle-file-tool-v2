# BFT_B112_CANCELLATION_CONTRACT_TESTS
# ============================================================================
# SOURCEFILE: test_cancellation_contract.py
# RELPATH: bundle_file_tool_v2/tests/unit/test_cancellation_contract.py
# PROJECT: Bundle File Tool v2.1
# VERSION: 2.1.112
# LIFECYCLE: Testing
# STATUS: Build 112 - BFT_B112_CANCELLATION_CONTRACT_TESTS
# ============================================================================
"""Cooperative cancellation in the core operations.

PyThermX 0.4.0 supplies the protocol; core owns a one-callable seam so it never
imports a renderer's library. These tests cover the seam and the three long
operations that poll it.

The properties that matter:

1. **Cancellation is a third outcome**, not a failure. Reporting it as an error
   blames the system for the operator's decision.
2. **Work stops between units, never inside one.** Every file already written is
   complete; there are no half-files.
3. **A cancelled extraction is not a short extraction.** Reconciliation exists
   to catch a *silently* incomplete extract; a deliberate stop must not be
   reported as that corruption.
4. **A broken canceller cannot stop work.** Same guarantee `emit()` gives for
   progress, for the same reason.
"""

from __future__ import annotations

import pytest

from core.cancellation import (
    CancelRecorder,
    OperationCancelled,
    is_cancelled,
    raise_if_cancelled,
)
from core.exceptions import BundleFileToolError, ValidationError
from core.models import BundleEntry, BundleManifest
from core.writer import BundleCreator, BundleWriter


@pytest.fixture
def tree(tmp_path):
    source = tmp_path / "src_tree"
    source.mkdir()
    for index in range(8):
        (source / f"f{index:02d}.txt").write_text(f"line {index}\n", encoding="utf-8")
    return source


# ---------------------------------------------------------------------------
# 1. The seam itself
# ---------------------------------------------------------------------------

def test_no_canceller_means_never_cancelled():
    assert is_cancelled(None) is False
    raise_if_cancelled(None)          # must not raise


def test_a_canceller_that_raises_is_treated_as_not_cancelled():
    """A broken canceller must not stop work nobody asked to stop."""
    def broken():
        raise RuntimeError("boom")

    assert is_cancelled(broken) is False
    raise_if_cancelled(broken)        # must not raise


@pytest.mark.parametrize("value,expected", [
    (True, True), (False, False), (1, True), (0, False), ("yes", True), ("", False),
])
def test_the_predicate_result_is_coerced_to_bool(value, expected):
    assert is_cancelled(lambda: value) is expected


def test_raise_if_cancelled_carries_the_work_done():
    with pytest.raises(OperationCancelled) as caught:
        raise_if_cancelled(lambda: True, operation="bundle", phase="read",
                           completed=3, total=10)

    error = caught.value
    assert error.operation == "bundle"
    assert error.phase == "read"
    assert error.completed == 3
    assert error.total == 10
    assert "3 of 10" in str(error)
    assert "read" in str(error)


def test_cancellation_is_a_bundle_error_but_never_reads_as_failure():
    """It subclasses the family error so existing handlers still catch it...

    ...but the CLI reports it before `BundleFileToolError` precisely so it is
    never printed as "ERROR:". This test pins the inheritance the ordering
    depends on.
    """
    error = OperationCancelled(operation="extract")
    assert isinstance(error, BundleFileToolError)
    assert not isinstance(error, ValidationError)
    assert "cancelled" in str(error).lower()


def test_the_recorder_cancels_on_a_known_poll():
    recorder = CancelRecorder(after=2)
    assert [recorder() for _ in range(4)] == [False, False, True, True]
    assert recorder.calls == 4


# ---------------------------------------------------------------------------
# 2. Discovery
# ---------------------------------------------------------------------------

def test_discovery_stops_when_cancelled(tree):
    creator = BundleCreator(allow_globs=["**/*"], deny_globs=[])

    with pytest.raises(OperationCancelled) as caught:
        creator.discover_files(tree, tree, cancel=lambda: True)

    assert caught.value.operation == "bundle"
    assert caught.value.phase == "discover"


def test_discovery_completes_normally_without_a_canceller(tree):
    creator = BundleCreator(allow_globs=["**/*"], deny_globs=[])
    assert len(creator.discover_files(tree, tree, cancel=lambda: False)) == 8


# ---------------------------------------------------------------------------
# 3. Reading files into a manifest
# ---------------------------------------------------------------------------

def test_reading_stops_at_a_known_file(tree):
    creator = BundleCreator(allow_globs=["**/*"], deny_globs=[])
    files = creator.discover_files(tree, tree)
    recorder = CancelRecorder(after=3)

    with pytest.raises(OperationCancelled) as caught:
        creator.create_manifest(files, tree, "plain_marker", cancel=recorder)

    error = caught.value
    assert error.phase == "read"
    assert error.completed == 3, "should stop after exactly three files"
    assert error.total == 8


def test_reading_is_unaffected_when_never_cancelled(tree):
    creator = BundleCreator(allow_globs=["**/*"], deny_globs=[])
    files = creator.discover_files(tree, tree)
    manifest = creator.create_manifest(files, tree, "plain_marker",
                                       cancel=lambda: False)
    assert len(manifest.entries) == 8


# ---------------------------------------------------------------------------
# 4. Extraction - the case with real consequences on disk
# ---------------------------------------------------------------------------

def _manifest(count: int) -> BundleManifest:
    return BundleManifest(
        entries=[BundleEntry(path=f"out{index:02d}.txt",
                             content=f"contents {index}\n")
                 for index in range(count)],
        profile="plain_marker",
    )


def test_extraction_stops_and_reports_what_it_already_wrote(tmp_path):
    out = tmp_path / "out"
    writer = BundleWriter(base_path=out, overwrite_policy="overwrite",
                          add_headers=False)

    with pytest.raises(OperationCancelled) as caught:
        writer.extract_manifest(_manifest(10), out, cancel=CancelRecorder(after=4))

    error = caught.value
    assert error.operation == "extract"
    assert error.phase == "write"
    assert error.completed == 4
    assert error.total == 10
    assert len(error.partial_paths) == 4, "the operator must be told what landed"


def test_every_file_written_before_the_stop_is_complete(tmp_path):
    """Work stops between entries, so there are no half-written files."""
    out = tmp_path / "out"
    writer = BundleWriter(base_path=out, overwrite_policy="overwrite",
                          add_headers=False)

    with pytest.raises(OperationCancelled):
        writer.extract_manifest(_manifest(10), out, cancel=CancelRecorder(after=4))

    written = sorted(out.glob("*.txt"))
    assert len(written) == 4
    for index, path in enumerate(written):
        assert path.read_text(encoding="utf-8") == f"contents {index}\n", (
            f"{path.name} is truncated - cancellation cut into a unit of work"
        )


def test_a_cancelled_extraction_is_not_reported_as_a_corrupt_one(tmp_path):
    """The interaction that would have been easy to get wrong.

    `_reconcile_extraction` halts when an extraction is short, because a
    silently incomplete extract is corruption. A *cancelled* extract is also
    short - deliberately - and must not be reported as corruption. The
    cancellation is raised before reconciliation is reached, so the operator
    gets the real reason rather than a bogus integrity failure.
    """
    out = tmp_path / "out"
    writer = BundleWriter(base_path=out, overwrite_policy="overwrite",
                          add_headers=False)

    with pytest.raises(OperationCancelled):
        writer.extract_manifest(_manifest(10), out, cancel=CancelRecorder(after=2))


def test_reconciliation_still_fires_for_a_genuinely_short_extraction(tmp_path):
    """The cancellation path must not have weakened the corruption guard.

    Cancellation returns early *before* reconciliation, which is correct — but
    it would be easy for that to shade into "short extractions are fine now".
    This drives a silent loss through the normal path and requires that
    reconciliation still halts, exactly as Build 103 ratified.
    """
    out = tmp_path / "out"
    writer = BundleWriter(base_path=out, overwrite_policy="overwrite",
                          add_headers=False)

    original = writer.write_entry
    calls = {"n": 0}

    def lossy(entry, target_path, apply_headers=None):
        # report a write that never reaches the ledger: the exact shape of the
        # silent loss reconciliation exists to catch
        calls["n"] += 1
        if calls["n"] == 3:
            return "skipped", None
        return original(entry, target_path, apply_headers=apply_headers)

    writer.write_entry = lossy

    with pytest.raises(ValidationError, match="reconciliation"):
        writer.extract_manifest(_manifest(4), out)


def test_extraction_without_a_canceller_is_unchanged(tmp_path):
    out = tmp_path / "out"
    writer = BundleWriter(base_path=out, overwrite_policy="overwrite",
                          add_headers=False)
    stats = writer.extract_manifest(_manifest(5), out, cancel=lambda: False)
    assert stats["processed"] == 5


# ---------------------------------------------------------------------------
# 5. Layering
# ---------------------------------------------------------------------------

def test_the_cancellation_seam_does_not_import_pythermx():
    """Core owns the contract; adapters bridge to PyThermX.

    The blanket AST layering test already covers every core module, but this
    states the intent for the one that most obviously *wants* to import it.
    """
    import ast
    from pathlib import Path

    module = Path(__file__).resolve().parents[2] / "src" / "core" / "cancellation.py"
    tree_ast = ast.parse(module.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree_ast):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])

    assert "pythermx" not in imported
