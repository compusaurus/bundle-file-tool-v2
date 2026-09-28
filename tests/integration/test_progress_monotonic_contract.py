# BFT_B109_PROGRESS_MONOTONIC_CONTRACT
# ============================================================================
# SOURCEFILE: test_progress_monotonic_contract.py
# RELPATH: bundle_file_tool_v2/tests/integration/test_progress_monotonic_contract.py
# PROJECT: Bundle File Tool v2.1
# VERSION: 2.1.109
# LIFECYCLE: Testing
# STATUS: Build 109 - BFT_B109_PROGRESS_MONOTONIC_CONTRACT
# ============================================================================
"""One contract for every entry point that accepts a progress sink.

`ARCH-RULING-2026-08-23-02` §4 item 6 mandates this suite, and it exists because
the same mistake happened twice:

* Build 107 accepted `--progress` on `unbundle`, threaded it partway, and never
  handed it to `extract_manifest`. The bar drew nothing.
* Build 108 fixed that call site — and `BundleToolService.extract_bundle()` had
  the identical omission, which Paul found (F-06): write events of `[0, 2]` for
  a two-file extraction instead of a per-file sequence.

Two instances of one mistake is a pattern, not a slip. The reason it survives is
structural: `emit()` deliberately swallows sink failures so a broken reporter can
never break the operation it observes, which also means a *missing* sink is
indistinguishable from a working one from the inside. Nothing raises, nothing
logs, the operation succeeds.

So this suite tests the class rather than the instances. Every entry point that
takes `progress` must produce a per-unit, non-decreasing sequence that reaches
its total — never just a start and an end.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from core.progress import (
    OP_CHECK,
    PHASE_COMPLETE,
    PHASE_DISCOVER,
    PHASE_INTEGRITY,
    PHASE_PLAN,
    PHASE_PARSE,
    PHASE_READ,
    PHASE_VERIFY,
    PHASE_WRITE,
    ProgressRecorder,
)

SRC = Path(__file__).resolve().parents[2] / "src"


# ---------------------------------------------------------------------------
# Shared assertions
# ---------------------------------------------------------------------------

def assert_per_unit_sequence(events, phase, expected_total):
    """The heart of the contract: a real per-unit climb, not a start and an end."""
    currents = [e.current for e in events if e.phase == phase]
    assert currents, f"no {phase} events were emitted at all"

    assert currents == sorted(currents), f"{phase} progress went backwards: {currents}"
    assert currents[-1] == expected_total, (
        f"{phase} finished at {currents[-1]}, expected {expected_total}"
    )
    assert len(currents) >= expected_total, (
        f"{phase} emitted {len(currents)} events for {expected_total} units - "
        f"this is the F-06 signature (a bracket, not a sequence): {currents}"
    )
    # every unit is individually accounted for
    assert set(range(1, int(expected_total) + 1)) <= set(int(c) for c in currents), (
        f"{phase} skipped units: {currents}"
    )


def assert_terminates_once(events):
    completes = [e for e in events if e.phase == PHASE_COMPLETE]
    assert len(completes) == 1, f"expected exactly one complete event, got {len(completes)}"
    assert events[-1].phase == PHASE_COMPLETE, "events continued after completion"


@pytest.fixture
def sample_tree(tmp_path):
    """A small source tree with a known, deliberately non-trivial file count."""
    source = tmp_path / "source"
    source.mkdir()
    for index in range(5):
        (source / f"file{index}.txt").write_text(f"line {index}\n", encoding="utf-8")
    (source / "nested").mkdir()
    (source / "nested" / "deep.txt").write_text("deep\n", encoding="utf-8")
    return source


FILE_COUNT = 6


# ---------------------------------------------------------------------------
# 1. Core entry points
# ---------------------------------------------------------------------------

def test_discover_files_reports_monotonically_and_closes_determinate(sample_tree):
    """Discovery progress rises monotonically and ends with a known total.

    Build 110 (PERF-BFT-002, ARCH-RULING-2026-08-24-01) changed the emission
    rule from one event per matched file to a throttled event per scan window.
    Per-file emission could not survive: it produced no events at all while
    walking an excluded subtree, and it would have flooded the sink across tens
    of thousands of nodes. What still holds - and is what the progress contract
    actually depends on - is that the running count never goes backwards and
    that the closing event is determinate.
    """
    from core.writer import BundleCreator

    recorder = ProgressRecorder()
    found = BundleCreator(allow_globs=["**/*"], deny_globs=[]).discover_files(
        sample_tree, sample_tree, progress=recorder)

    assert len(found) == FILE_COUNT
    discover = [e for e in recorder.events if e.phase == PHASE_DISCOVER]
    rising = [e.current for e in discover if e.total is None]
    assert rising == sorted(rising), "discovery count must never decrease"
    assert rising[-1] <= FILE_COUNT, "in-flight count must not exceed the final total"
    assert discover[-1].total == FILE_COUNT, "discovery must close determinate"
    assert discover[-1].current == FILE_COUNT


def test_create_manifest_reports_every_file(sample_tree):
    from core.writer import BundleCreator

    creator = BundleCreator(allow_globs=["**/*"], deny_globs=[])
    files = creator.discover_files(sample_tree, sample_tree)

    recorder = ProgressRecorder()
    creator.create_manifest(files, sample_tree, "plain_marker", progress=recorder)

    assert_per_unit_sequence(recorder.events, PHASE_READ, FILE_COUNT)


def test_read_progress_counts_only_completed_source_reads(tmp_path, monkeypatch):
    """The bar must not reach 100% before the final read has returned."""
    from core.writer import BundleCreator

    source = tmp_path / "last.txt"
    source.write_text("last bytes\n", encoding="utf-8")
    creator = BundleCreator(allow_globs=["**/*"], deny_globs=[])
    recorder = ProgressRecorder()
    original = creator._read_file_to_entry

    def observed_read(file_path, relative_path):
        read_events = [
            event for event in recorder.events if event.phase == PHASE_READ]
        assert [event.current for event in read_events] == [0]
        return original(file_path, relative_path)

    monkeypatch.setattr(creator, "_read_file_to_entry", observed_read)
    creator.create_manifest(
        [source], tmp_path, "plain_marker", progress=recorder)

    assert [event.current for event in recorder.events
            if event.phase == PHASE_READ] == [0, 1]


def test_extract_manifest_reports_every_entry(sample_tree, tmp_path):
    from core.parser import BundleParser, ProfileRegistry
    from core.writer import BundleCreator, BundleWriter

    creator = BundleCreator(allow_globs=["**/*"], deny_globs=[])
    manifest = creator.create_manifest(
        creator.discover_files(sample_tree, sample_tree), sample_tree, "plain_marker")
    bundle = tmp_path / "b.txt"
    bundle.write_text(ProfileRegistry().get("plain_marker").format_manifest(manifest),
                      encoding="utf-8")
    parsed = BundleParser().parse_file(bundle, auto_detect=True)

    recorder = ProgressRecorder()
    out = tmp_path / "out"
    BundleWriter(base_path=out, overwrite_policy="overwrite").extract_manifest(
        parsed, out, progress=recorder)

    assert_per_unit_sequence(recorder.events, PHASE_WRITE, FILE_COUNT)
    assert_terminates_once(recorder.events)


# ---------------------------------------------------------------------------
# 2. The service facade - F-06
# ---------------------------------------------------------------------------

def test_service_create_bundle_reports_every_file(sample_tree, tmp_path):
    from core.service import BundleToolService

    recorder = ProgressRecorder()
    BundleToolService().create_bundle(
        [sample_tree], base_path=sample_tree, profile="plain_marker",
        output_path=tmp_path / "b.txt", progress=recorder)

    assert_per_unit_sequence(recorder.events, PHASE_READ, FILE_COUNT)
    assert_terminates_once(recorder.events)


def test_service_extract_bundle_reports_every_entry(sample_tree, tmp_path):
    """F-06 itself. Before the fix this produced `[0, 6]` and nothing between."""
    from core.service import BundleToolService

    service = BundleToolService()
    bundle = tmp_path / "b.txt"
    service.create_bundle([sample_tree], base_path=sample_tree,
                          profile="plain_marker", output_path=bundle)

    recorder = ProgressRecorder()
    service.extract_bundle(bundle, output_dir=tmp_path / "out",
                           overwrite_policy="overwrite", progress=recorder)

    assert_per_unit_sequence(recorder.events, PHASE_WRITE, FILE_COUNT)
    assert_terminates_once(recorder.events)


def test_service_extraction_emits_no_duplicate_terminal_events(sample_tree, tmp_path):
    """Paul's constraint: pass the sink through *without* duplicating events.

    The writer emits its own completion when it is the top-level caller. When
    the service owns the operation, the service owns the terminal event — so
    exactly one must survive.
    """
    from core.service import BundleToolService

    service = BundleToolService()
    bundle = tmp_path / "b.txt"
    service.create_bundle([sample_tree], base_path=sample_tree,
                          profile="plain_marker", output_path=bundle)

    recorder = ProgressRecorder()
    service.extract_bundle(bundle, output_dir=tmp_path / "out",
                           overwrite_policy="overwrite", progress=recorder)

    completes = [e for e in recorder.events if e.phase == PHASE_COMPLETE]
    assert len(completes) == 1, f"duplicated completion events: {len(completes)}"

    writes = [e.current for e in recorder.events if e.phase == PHASE_WRITE]
    assert len(writes) == len(set(writes)), f"duplicated write positions: {writes}"


def _write_sample_bundle(service, sample_tree, path):
    service.create_bundle(
        [sample_tree], base_path=sample_tree,
        profile="plain_marker", output_path=path)
    return path


def test_service_check_manifest_reports_integrity_and_verification(sample_tree):
    from core.service import BundleToolService
    from core.writer import BundleCreator

    manifest = BundleCreator(
        allow_globs=["**/*"], deny_globs=[]).create_manifest(
            sorted(sample_tree.rglob("*.txt")), sample_tree, "plain_marker")
    recorder = ProgressRecorder()

    BundleToolService().check_manifest(manifest, progress=recorder)

    assert {event.operation for event in recorder.events} == {OP_CHECK}
    assert PHASE_INTEGRITY in recorder.phases()
    assert PHASE_VERIFY in recorder.phases()
    assert recorder.last_for(PHASE_VERIFY).current == FILE_COUNT


def test_service_load_checked_bundle_reports_parse_and_completion(
        sample_tree, tmp_path):
    from core.service import BundleToolService

    service = BundleToolService()
    bundle = _write_sample_bundle(service, sample_tree, tmp_path / "loaded.txt")
    recorder = ProgressRecorder()

    loaded = service.load_checked_bundle(bundle, progress=recorder)

    assert loaded.check.file_count == FILE_COUNT
    assert PHASE_PARSE in recorder.phases()
    assert_terminates_once(recorder.events)


def test_service_check_bundle_returns_the_shared_result(sample_tree, tmp_path):
    from core.service import BundleToolService

    service = BundleToolService()
    bundle = _write_sample_bundle(service, sample_tree, tmp_path / "checked.txt")
    recorder = ProgressRecorder()

    result = service.check_bundle(bundle, progress=recorder)

    assert result.valid
    assert result.file_count == FILE_COUNT
    assert_terminates_once(recorder.events)


def test_service_check_selection_reports_one_check_operation(sample_tree):
    from core.service import BundleToolService

    service = BundleToolService()
    plan = service.plan_bundle([sample_tree], preset=[])
    recorder = ProgressRecorder()

    result = service.check_selection(plan, progress=recorder)

    assert result.file_count == FILE_COUNT
    assert {event.operation for event in recorder.events} == {OP_CHECK}
    assert_terminates_once(recorder.events)


# ---------------------------------------------------------------------------
# 3. The CLI surface
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("command", ["bundle", "unbundle"])
def test_cli_renders_a_rising_sequence(sample_tree, tmp_path, command):
    """Rendered output is the only proof a CLI sink is really connected."""
    env = {**os.environ, "PYTHONPATH": str(SRC)}
    bundle = tmp_path / "b.txt"

    subprocess.run(
        [sys.executable, "-m", "cli", "bundle", str(sample_tree),
         "--base-path", str(sample_tree), "--profile", "plain_marker",
         "-o", str(bundle), "--progress", "none"],
        cwd=str(SRC), capture_output=True, text=True, env=env, check=True)

    if command == "bundle":
        argv = ["bundle", str(sample_tree), "--base-path", str(sample_tree),
                "--profile", "plain_marker", "-o", str(tmp_path / "c.txt")]
        phase = "read"
    else:
        argv = ["unbundle", str(bundle), "-o", str(tmp_path / "out"),
                "--overwrite", "overwrite"]
        phase = "write"

    result = subprocess.run(
        [sys.executable, "-m", "cli", *argv, "--progress", "bar"],
        cwd=str(SRC), capture_output=True, text=True, env=env)

    assert result.returncode == 0, result.stderr
    assert phase in result.stderr, f"the {phase} phase drew nothing"
    assert f"/{FILE_COUNT}" in result.stderr, (
        f"no per-unit counter reached {FILE_COUNT}: {result.stderr!r}"
    )


# ---------------------------------------------------------------------------
# 4. The Tkinter surface
# ---------------------------------------------------------------------------

def test_tk_adapter_receives_a_per_unit_sequence(sample_tree):
    """The Tk seam carries the same stream, so it inherits the same contract."""
    pytest.importorskip("pythermx")
    pytest.importorskip("tkinter")
    from pythermx.tk import PhaseSpec

    from ui.tk_progress import TkProgressReporter

    class RecordingChannel:
        def __init__(self):
            self.updates = []
            self.begins = []

        def post_begin(self, spec):
            assert isinstance(spec, PhaseSpec)
            self.begins.append(spec)
            return True

        def post_update(self, value):
            self.updates.append(value)
            return True

        def post_promote(self, total, *, current=0.0, phase=None):
            self.updates.append(current)
            return True

        def post_message(self, text):
            return True

    from core.writer import BundleCreator

    channel = RecordingChannel()
    creator = BundleCreator(allow_globs=["**/*"], deny_globs=[])
    files = creator.discover_files(sample_tree, sample_tree)
    creator.create_manifest(files, sample_tree, "plain_marker",
                            progress=TkProgressReporter(channel))

    assert channel.begins, "no phase was ever begun on the Tk channel"
    assert channel.updates == sorted(channel.updates), "Tk progress went backwards"
    assert channel.updates[-1] == FILE_COUNT
    assert len(channel.updates) >= FILE_COUNT - 1, (
        f"Tk channel saw a bracket rather than a sequence: {channel.updates}"
    )


# ---------------------------------------------------------------------------
# 4b. plan_bundle (Build 114, WP3)
# ---------------------------------------------------------------------------

def test_plan_bundle_reports_discovery_and_closes_determinate(sample_tree):
    """Planning is an operation, so it observes the same contract.

    Planning has no read or write phase - it opens nothing - but it still walks
    a tree, and on a large one that walk is the part the operator waits on. It
    must therefore emit discovery progress and close determinate, or the bar
    would sit at zero for the whole scan and then vanish.
    """
    from core.service import BundleToolService

    recorder = ProgressRecorder()
    result = BundleToolService().plan_bundle([sample_tree], progress=recorder)

    discover = [e for e in recorder.events if e.phase == PHASE_DISCOVER]
    assert discover, "planning emitted no discovery progress at all"

    rising = [e.current for e in discover]
    assert rising == sorted(rising), f"discovery went backwards: {rising}"
    assert discover[-1].current == FILE_COUNT
    assert discover[-1].total == FILE_COUNT, "discovery must close determinate"

    for phase in (PHASE_PLAN, PHASE_VERIFY):
        events = [e for e in recorder.events if e.phase == phase]
        assert events, f"planning emitted no {phase} progress"
        assert [e.current for e in events] == sorted(e.current for e in events)
        assert events[-1].current == FILE_COUNT
        assert events[-1].total == FILE_COUNT

    assert recorder.phases() == [
        PHASE_DISCOVER, PHASE_PLAN, PHASE_VERIFY, PHASE_COMPLETE]

    complete = [e for e in recorder.events if e.phase == PHASE_COMPLETE]
    assert complete, "planning never reported completion"
    assert complete[-1].total == FILE_COUNT
    assert complete[-1].current == FILE_COUNT
    assert complete[-1].percent == 100.0
    assert str(len(result.plan.included())) in complete[-1].message


def test_preset_replan_reports_work_after_discovery_is_already_done(sample_tree):
    """A preset must not silently recompute thousands of decisions on Tk."""
    from core.service import BundleToolService

    service = BundleToolService()
    previous = service.plan_bundle([sample_tree])
    recorder = ProgressRecorder()

    result = service.replan(
        previous, preset=["logs"], progress=recorder)

    assert result.plan.generation == previous.plan.generation + 1
    assert recorder.phases() == [PHASE_PLAN, PHASE_VERIFY, PHASE_COMPLETE]
    assert recorder.last_for(PHASE_PLAN).current == FILE_COUNT
    assert recorder.last_for(PHASE_VERIFY).current == FILE_COUNT
    assert recorder.last_for(PHASE_COMPLETE).current == FILE_COUNT
    assert recorder.last_for(PHASE_COMPLETE).percent == 100.0


def test_planning_emits_progress_without_opening_a_file(sample_tree):
    """The claim that makes the plan cheap, asserted rather than assumed.

    If planning ever starts reading files - to sniff a binary, say, or to hash
    content - a 4,000-file tree stops being re-plannable on a checkbox click and
    the whole workspace design loses its premise. This fails the moment that
    happens.
    """
    import builtins

    from core.service import BundleToolService

    real_open = builtins.open
    opened = []

    def watched_open(file, *args, **kwargs):
        opened.append(str(file))
        return real_open(file, *args, **kwargs)

    recorder = ProgressRecorder()
    builtins.open = watched_open
    try:
        BundleToolService().plan_bundle([sample_tree], progress=recorder)
    finally:
        builtins.open = real_open

    under_tree = [p for p in opened if str(sample_tree) in p]
    assert under_tree == [], f"planning opened source files: {under_tree}"


# ---------------------------------------------------------------------------
# 5. The class-level guard
# ---------------------------------------------------------------------------

def test_every_progress_accepting_entry_point_is_covered_here():
    """A register, so a new sink-accepting method cannot be added untested.

    If this fails, something now takes a `progress` argument and has no entry in
    the covered set. Add a test above rather than extending the list.
    """
    import inspect

    from core.service import BundleToolService
    from core.writer import BundleCreator, BundleWriter

    covered = {
        "BundleCreator.discover_files",
        "BundleCreator.create_manifest",
        "BundleWriter.extract_manifest",
        "BundleToolService.create_bundle",
        "BundleToolService.extract_bundle",
        "BundleToolService.validate_bundle",
        # Build 125 structured check surfaces.
        "BundleToolService.check_manifest",
        "BundleToolService.load_checked_bundle",
        "BundleToolService.check_bundle",
        "BundleToolService.check_selection",
        # Build 114 (WP3) - covered by section 4b above.
        "BundleToolService.plan_bundle",
        # Build 121 responsiveness repair - preset replans are observable too.
        "BundleToolService.replan",
    }

    found = set()
    for cls in (BundleCreator, BundleWriter, BundleToolService):
        for name, member in inspect.getmembers(cls, inspect.isfunction):
            if name.startswith("_"):
                continue
            if "progress" in inspect.signature(member).parameters:
                found.add(f"{cls.__name__}.{name}")

    assert found <= covered, f"untested progress entry points: {sorted(found - covered)}"
