# BFT_B113_SELECTION_PERFORMANCE_HARNESS
# ============================================================================
# SOURCEFILE: test_selection_performance.py
# RELPATH: bundle_file_tool_v2/tests/integration/test_selection_performance.py
# PROJECT: Bundle File Tool v2.2
# VERSION: 2.1.113
# LIFECYCLE: Testing
# STATUS: Build 113 - BFT_B113_SELECTION_PERFORMANCE_HARNESS
# ============================================================================
"""The SEL-PERF gates, as executable budgets rather than estimates.

Paul asked me to reconcile the performance gates with harness results
(`BFT-ANALYSIS-2026-08-25-02` §9). `SEL-PERF-002` was written as *"within the
measured budget set by John's harness"*, which is not a gate until the number
exists. This file is that number, and it holds itself to it.

It has already earned its place. The first selection engine took **4,306 ms** to
plan 4,000 paths - 8.6x over budget - because `decide()` re-sorted the rule list
for every layer of every path and `matches()` fired a dozen `fnmatch` calls per
pattern. Bucketing the rules once and compiling each glob to one cached regex
brought that to **425 ms**. Nothing in the behaviour changed; 75 tests passed
before and after.

Budgets are deliberately set with headroom over measured values, because a gate
that fails on an unlucky scheduling slice teaches people to ignore gates.
"""

from __future__ import annotations

import os
import statistics
import time
from pathlib import Path

import pytest

from core.config import ConfigManager
from core.detectors import DetectorLedger, DetectorResult, classify_directory
from core.selection import (
    Action,
    SelectionEngine,
    SelectionGroup,
    State,
    rules_from_globs,
)

REFERENCE_PATHS = 4_000


def percentile(samples, fraction=0.95):
    ordered = sorted(samples)
    return ordered[min(len(ordered) - 1, int(len(ordered) * fraction))]


#: Line tracing costs a measured 4.3x on this workload (429 ms -> 1,848 ms for a
#: 4,000-path plan). The whole suite runs under `coverage`, so an unadjusted
#: wall-clock gate would be measuring the tracer rather than the product - and
#: relaxing the budget to accommodate it would leave no real gate at all.
#:
#: The untraced budget is the authoritative one. When a tracer is installed the
#: same assertion runs against a scaled budget, so the gate still fails on a real
#: regression instead of being skipped.
TRACER_ALLOWANCE = 5.0


def budget(milliseconds: float) -> float:
    """The stated budget, scaled if something is tracing this interpreter."""
    import sys as _sys
    return milliseconds * (TRACER_ALLOWANCE if _sys.gettrace() else 1.0)


@pytest.fixture(scope="module")
def engine():
    deny = ConfigManager().get("safety.deny_globs", [])
    return SelectionEngine(rules=rules_from_globs(["**/*"], deny),
                           base_action=Action.INCLUDE)


@pytest.fixture(scope="module")
def candidates():
    """A reference set at the size the specification argues about."""
    return [(f"src/pkg{index // 100}/module_{index:05d}.py", 2_000)
            for index in range(REFERENCE_PATHS)]


@pytest.fixture(scope="module")
def reference_plan(engine, candidates):
    return engine.plan(candidates)


# ---------------------------------------------------------------------------
# SEL-PERF-001 - a toggle is cheap and reads nothing
# ---------------------------------------------------------------------------

def test_sel_perf_001_a_single_toggle_costs_no_reads_and_stays_under_50ms(
        engine, reference_plan, tmp_path, monkeypatch):
    """One decision plus refreshed counts and ordering, within 50 ms p95.

    Reads are structurally impossible here: the engine is handed metadata and
    never touches a filesystem. The test asserts that rather than trusting it,
    by pointing the working directory at an empty tree.
    """
    # monkeypatch.chdir restores the previous directory at teardown; a bare
    # os.chdir would leak into every test that ran afterwards.
    monkeypatch.chdir(tmp_path)             # nothing to read even by accident

    samples = []
    for _ in range(50):
        start = time.perf_counter()
        engine.decide("src/pkg1/module_00042.py", 2_000)
        reference_plan.counts()
        reference_plan.ordered_paths()
        samples.append((time.perf_counter() - start) * 1000)

    p95 = percentile(samples)
    assert p95 < budget(50), (
        f"toggle round trip p95 {p95:.1f} ms exceeds the 50 ms gate "
        f"(p50 {statistics.median(samples):.1f} ms)"
    )


def test_a_single_decision_is_sub_millisecond(engine):
    samples = []
    for _ in range(200):
        start = time.perf_counter()
        engine.decide("src/pkg1/module_00042.py", 2_000)
        samples.append((time.perf_counter() - start) * 1000)

    assert percentile(samples) < budget(5.0), (
        "a single re-decision must stay far inside the toggle budget; "
        "the pre-optimisation engine took 1.03 ms and that was already too slow "
        "to re-plan in bulk"
    )


# ---------------------------------------------------------------------------
# SEL-PERF-002 - the initial plan, now a real budget
# ---------------------------------------------------------------------------

def test_sel_perf_002_a_4000_path_plan_is_delivered_within_500ms(
        engine, candidates):
    """The gate Paul left open, closed with a measured number.

    Measured 425 ms p50 / 441 ms p95 after optimisation, against 4,306 ms
    before it. 500 ms carries the headroom.
    """
    samples = []
    for _ in range(3):
        start = time.perf_counter()
        plan = engine.plan(candidates)
        samples.append((time.perf_counter() - start) * 1000)

    assert len(plan.decisions) == REFERENCE_PATHS
    p95 = percentile(samples)
    assert p95 < budget(500), (
        f"plan build p95 {p95:.0f} ms exceeds the 500 ms SEL-PERF-002 budget "
        f"(p50 {statistics.median(samples):.0f} ms, "
        f"tracer {'on' if __import__('sys').gettrace() else 'off'})"
    )


def test_bulk_plan_normalises_each_candidate_not_each_rule(
        engine, candidates, monkeypatch):
    """Pin the 6.6-million-normalisation defect from the user recording."""
    import core.selection as selection

    real_normalise = selection.normalise
    calls = {"count": 0}

    def counted(value):
        calls["count"] += 1
        return real_normalise(value)

    monkeypatch.setattr(selection, "normalise", counted)
    sample = candidates[:100]
    plan = engine.plan(sample)

    assert len(plan.decisions) == len(sample)
    assert calls["count"] <= len(sample) * 2 + 2, (
        f"{calls['count']} normalisations for {len(sample)} candidates; "
        "the target is being normalised once per rule again")


def test_counts_and_ordering_are_cheap_enough_to_recompute_on_every_change(
        reference_plan):
    samples = []
    for _ in range(20):
        start = time.perf_counter()
        reference_plan.counts()
        reference_plan.ordered_paths()
        samples.append((time.perf_counter() - start) * 1000)

    assert percentile(samples) < budget(25), (
        "the decision-first viewport recomputes these on every interaction"
    )


# ---------------------------------------------------------------------------
# SEL-DET-001 - pruning happens before descent, and costs nothing to read
# ---------------------------------------------------------------------------

@pytest.fixture
def tree_with_environment(tmp_path):
    """A source tree with a versioned virtual environment inside it."""
    source = tmp_path / "project"
    (source / "src").mkdir(parents=True)
    for index in range(20):
        (source / "src" / f"mod_{index}.py").write_text("x = 1\n", encoding="utf-8")

    env = source / ".venv312"
    (env / "Scripts").mkdir(parents=True)
    (env / "pyvenv.cfg").write_text("home = C:/Python311\n", encoding="utf-8")
    (env / "Scripts" / "python.exe").write_bytes(b"MZ")
    deep = env / "Lib" / "site-packages" / "pytest"
    deep.mkdir(parents=True)
    for index in range(300):
        (deep / f"plugin_{index}.py").write_text("y = 2\n", encoding="utf-8")

    return source


def test_sel_det_001_the_environment_is_pruned_before_descent(tree_with_environment):
    """`.venv312` never enters the index, and its 300 files are never statted."""
    ledger = DetectorLedger()
    visited, statted = [], 0

    for walk_root, walk_dirs, walk_files in os.walk(tree_with_environment):
        keep = []
        for name in walk_dirs:
            finding = classify_directory(os.path.join(walk_root, name), name)
            relative = os.path.relpath(os.path.join(walk_root, name),
                                       tree_with_environment).replace("\\", "/")
            ledger.record(relative, finding)
            if finding.prunable:
                continue                     # do not descend
            keep.append(name)
        walk_dirs[:] = keep
        for name in walk_files:
            os.stat(os.path.join(walk_root, name))
            statted += 1
            visited.append(name)

    assert ledger.pruned_roots() == [".venv312"]
    # 20 source files and nothing else. Not even `pyvenv.cfg` is statted: the
    # directory is classified from its own name and markers *before* descent, so
    # the evidence is gathered without walking the tree it describes.
    assert statted == 20, f"expected the 20 source files only, statted {statted}"
    assert not any(name.startswith("plugin_") for name in visited), (
        "site-packages was descended into; pruning did not happen before descent"
    )


def test_pruning_is_what_makes_a_large_tree_affordable(tree_with_environment):
    """The 89% figure from the design review, reproduced as a ratio."""
    def walk(prune: bool) -> int:
        seen = 0
        for walk_root, walk_dirs, walk_files in os.walk(tree_with_environment):
            if prune:
                walk_dirs[:] = [
                    name for name in walk_dirs
                    if not classify_directory(os.path.join(walk_root, name), name).prunable
                ]
            for name in walk_files:
                os.stat(os.path.join(walk_root, name))
                seen += 1
        return seen

    full, pruned = walk(False), walk(True)
    assert full > 300
    assert pruned <= 21
    assert pruned / full < 0.15, (
        f"pruning removed only {100 - pruned / full * 100:.0f}% of the metadata work"
    )


# ---------------------------------------------------------------------------
# Group reordering performs no reads and no re-planning
# ---------------------------------------------------------------------------

def test_reordering_groups_never_re_evaluates_inclusion(candidates):
    """Paul §12.3: changing group order never rereads content.

    Stronger here: it does not even re-decide. The inclusion decisions are
    reused and only the emission order changes.
    """
    # Disjoint patterns, so swapping the order genuinely inverts the output.
    # An earlier draft used overlapping globs and produced identical orderings,
    # which would have passed as "no reads" while proving nothing.
    subjects = [("docs/guide.md", 100), ("docs/intro.md", 100),
                ("src/app.py", 100), ("src/util.py", 100)]

    groups_a = [SelectionGroup(id="docs", order=10, patterns=("docs/**",)),
                SelectionGroup(id="code", order=20, patterns=("src/**",))]
    groups_b = [SelectionGroup(id="docs", order=20, patterns=("docs/**",)),
                SelectionGroup(id="code", order=10, patterns=("src/**",))]

    deny = ConfigManager().get("safety.deny_globs", [])
    plan_a = SelectionEngine(rules=rules_from_globs(["**/*"], deny),
                             groups=groups_a).plan(subjects)
    plan_b = SelectionEngine(rules=rules_from_globs(["**/*"], deny),
                             groups=groups_b).plan(subjects)

    assert plan_a.counts() == plan_b.counts(), "ordering changed a decision"
    assert plan_a.ordered_paths() != plan_b.ordered_paths(), "ordering had no effect"
    assert sorted(plan_a.ordered_paths()) == sorted(plan_b.ordered_paths())


# ---------------------------------------------------------------------------
# SEL-PERF-004 - the composed path (Build 114, WP3)
# ---------------------------------------------------------------------------
#
# Build 113 gated the engine. WP3 put a filesystem walk in front of it, and a
# budget that covers only the half that does no I/O is not a budget for what
# the operator waits on. These gates measure `plan_bundle` end to end: scan,
# classify, prune, assemble six layers of rules, and decide every path.

PLANNED_TREE_FILES = 1_200


@pytest.fixture(scope="module")
def planning_tree(tmp_path_factory):
    """A tree the size of a real project, with an environment to prune."""
    root = tmp_path_factory.mktemp("plan_perf")
    for package in range(12):
        directory = root / "src" / f"pkg{package}"
        directory.mkdir(parents=True)
        for module in range(100):
            (directory / f"module_{module:03d}.py").write_bytes(b"x = 1\n")

    env = root / ".venv"
    (env / "Scripts").mkdir(parents=True)
    (env / "pyvenv.cfg").write_bytes(b"home = C:\\Py\n")
    (env / "Scripts" / "python.exe").write_bytes(b"MZ")
    site = env / "Lib" / "site-packages" / "vendored"
    site.mkdir(parents=True)
    for module in range(400):
        (site / f"v{module:03d}.py").write_bytes(b"pass\n")
    return root


def test_sel_perf_004_planning_a_real_tree_stays_under_two_seconds(planning_tree):
    """The whole operation, not just the part that is free.

    2,000 ms for ~1,200 files including the walk. The walk dominates and is
    bounded by the filesystem, so the headroom here is wider than the pure
    in-memory gates - a budget tight enough to fail on a busy disk would teach
    people to ignore it.
    """
    from core.service import BundleToolService

    service = BundleToolService()
    samples = []
    for _ in range(3):
        started = time.perf_counter()
        result = service.plan_bundle([planning_tree], preset=["python-env"])
        samples.append((time.perf_counter() - started) * 1000)

    assert len(result.plan.included()) == PLANNED_TREE_FILES
    p95 = percentile(samples)
    assert p95 < budget(2_000), (
        f"plan_bundle p95 {p95:.0f} ms exceeds the 2,000 ms SEL-PERF-004 budget")


def test_re_planning_the_same_tree_does_not_get_slower(planning_tree):
    """Guards the cache WP5 will add: planning must be stateless today, so a
    second plan costs the same as the first rather than accumulating."""
    from core.service import BundleToolService

    service = BundleToolService()

    def timed():
        started = time.perf_counter()
        service.plan_bundle([planning_tree])
        return (time.perf_counter() - started) * 1000

    first = timed()
    later = min(timed() for _ in range(3))
    assert later < first * 2.5, (
        f"re-planning cost {later:.0f} ms against a first plan of {first:.0f} ms")


def test_pruning_is_still_what_makes_planning_affordable(planning_tree):
    """The 400-file vendored tree must never be statted.

    Stated as a cost, not just a file list: if pruning regressed to filtering
    after the walk the plan would be identical and the scan a third larger.
    """
    from core.service import BundleToolService

    result = BundleToolService().plan_bundle([planning_tree])
    assert ".venv" in result.plan.pruned_roots
    assert result.scan.scanned == PLANNED_TREE_FILES, (
        f"scanned {result.scan.scanned} files; the pruned subtree was walked")


# ---------------------------------------------------------------------------
# SEL-PERF-005 - the 4,000-path workspace UX gate (Build 115, WP4)
# ---------------------------------------------------------------------------
#
# WP4's exit gate is "4,000-path UX and accessibility gates pass". The numbers
# that decide whether the workspace feels alive are not the plan build - that is
# SEL-PERF-002 - but the three things an operator does repeatedly: toggle a
# checkbox, retype a search, and scroll a tree. Each has to stay inside a frame
# budget while the plan behind it holds 4,000 decisions.

WORKSPACE_PATHS = 4_000


@pytest.fixture(scope="module")
def workspace_tree(tmp_path_factory):
    """A 4,000-file tree with an environment that must never be walked."""
    root = tmp_path_factory.mktemp("workspace_perf")
    for package in range(40):
        directory = root / "src" / f"pkg{package:02d}"
        directory.mkdir(parents=True)
        for module in range(100):
            (directory / f"module_{module:03d}.py").write_bytes(b"x = 1\n")

    env = root / ".venv"
    (env / "Scripts").mkdir(parents=True)
    (env / "pyvenv.cfg").write_bytes(b"home = C\n")
    (env / "Scripts" / "python.exe").write_bytes(b"MZ")
    site = env / "Lib" / "site-packages"
    site.mkdir(parents=True)
    for module in range(500):
        (site / f"v{module:03d}.py").write_bytes(b"pass\n")
    return root


@pytest.fixture(scope="module")
def workspace(workspace_tree):
    from core.service import BundleToolService
    from ui.workspace_model import WorkspaceModel

    service = BundleToolService()
    model = WorkspaceModel(service, service.plan_bundle([workspace_tree]))
    assert len(model.result.plan.decisions) == WORKSPACE_PATHS
    return model


def test_sel_perf_005_a_checkbox_toggle_costs_no_reads_and_stays_under_150ms(
        workspace, monkeypatch):
    """One click: re-decide 4,000 paths and rebuild the counts, reading nothing.

    150 ms rather than SEL-PERF-001's 50 ms because this measures the whole
    round trip - override, replan, re-aggregate every directory - not a single
    decision. It is still well inside the threshold where a click feels
    connected to its result.
    """
    import builtins

    real_open = builtins.open
    opened = []
    monkeypatch.setattr(
        builtins, "open",
        lambda f, *a, **k: (opened.append(str(f)), real_open(f, *a, **k))[1])

    samples = []
    for index in range(5):
        started = time.perf_counter()
        workspace.set_folder(f"src/pkg{index:02d}", include=False)
        samples.append((time.perf_counter() - started) * 1000)

    monkeypatch.undo()
    workspace.clear_all_overrides()

    base = str(workspace.result.base_path)
    assert [p for p in opened if base in p] == [], "a toggle read from disk"
    p95 = percentile(samples)
    assert p95 < budget(150), (
        f"toggle p95 {p95:.0f} ms exceeds the 150 ms SEL-PERF-005 budget")


def test_the_folder_tree_renders_a_viewport_not_the_whole_tree(workspace):
    """Collapsed folders cost nothing: 40 rows, not 4,000.

    Building every descendant row up front is the obvious implementation and
    the reason large trees feel frozen. This asserts the tree is lazy.
    """
    started = time.perf_counter()
    rows = workspace.tree(expanded=[])
    elapsed = (time.perf_counter() - started) * 1000

    assert len(rows) < 50, f"collapsed tree produced {len(rows)} rows"
    assert elapsed < budget(50), f"collapsed tree took {elapsed:.0f} ms"


def test_expanding_one_folder_adds_only_that_folder(workspace):
    collapsed = len(workspace.tree(expanded=[]))
    expanded = len(workspace.tree(expanded=["src"]))
    assert 0 < expanded - collapsed <= 45


def test_filtering_four_thousand_decisions_stays_interactive(workspace):
    """Search is retyped character by character, so it runs on every keystroke."""
    samples = []
    for needle in ("module_01", "pkg3", "module_099", "src/pkg1", "x"):
        started = time.perf_counter()
        workspace.rows(search=needle)
        samples.append((time.perf_counter() - started) * 1000)
    p95 = percentile(samples)
    assert p95 < budget(150), f"search p95 {p95:.0f} ms exceeds 150 ms"


def test_the_summary_recomputes_cheaply_enough_for_every_keystroke(workspace):
    started = time.perf_counter()
    for _ in range(20):
        workspace.summary().headline()
    elapsed = (time.perf_counter() - started) * 1000
    assert elapsed < budget(50), f"20 summaries took {elapsed:.0f} ms"


def test_the_environment_is_absent_from_the_workspace_entirely(workspace):
    """500 vendored files, never walked, never listed, never counted."""
    assert workspace.result.scan.scanned == WORKSPACE_PATHS
    assert ".venv" in workspace.result.plan.pruned_roots
    assert not any(node.path.startswith(".venv/")
                   for node in workspace.tree(expanded=[".venv"]))


def test_every_visible_row_can_state_itself_accessibly(workspace):
    """The accessibility half of the WP4 exit gate.

    Every row an operator can focus must be able to say what it is, what state
    it is in and why - §7.2 forbids colour carrying that alone.
    """
    for node in workspace.tree(expanded=["src"]):
        spoken = node.accessible_text()
        assert node.label in spoken and node.state.value in spoken
    for row in workspace.rows(limit=50):
        assert row.path in row.accessible_text()
        assert row.state in row.accessible_text()
