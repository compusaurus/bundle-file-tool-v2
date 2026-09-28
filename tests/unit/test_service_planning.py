# BFT_B114_SERVICE_PLANNING_TESTS
# ============================================================================
# SOURCEFILE: test_service_planning.py
# RELPATH: bundle_file_tool_v2/tests/unit/test_service_planning.py
# PROJECT: Bundle File Tool v2.2
# VERSION: 2.1.114
# LIFECYCLE: Testing
# STATUS: Build 114 - WP3 - BFT_B114_SERVICE_PLANNING_TESTS
# ============================================================================
"""The facade contract: plan, explain, preview, then bundle what was planned.

Build 113 proved the ladder in isolation. These tests prove it through the
service, on a real tree, with real configuration - because the composition is
where Build 114's one genuine defect lived: every layer was correct and the
base action was still resolved from the union of their allow-lists.
"""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest

from core.cancellation import OperationCancelled
from core.exceptions import BundleFileToolError, PlanDriftError
from core.rule_sources import RuleSourceError
from core.selection import State
from core.service import BundleToolService, PlanResult


@pytest.fixture
def project(tmp_path):
    """A tree with source, docs, noise, an archive and an environment."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_bytes(b"print(1)\n")
    (tmp_path / "src" / "util.py").write_bytes(b"x = 2\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guide.md").write_bytes(b"# guide\n")
    (tmp_path / "notes.log").write_bytes(b"noise\n")
    (tmp_path / "vendor.whl").write_bytes(b"PK\x03\x04")

    env = tmp_path / ".venv"
    (env / "Scripts").mkdir(parents=True)
    (env / "pyvenv.cfg").write_bytes(b"home = C:\\Py\n")
    (env / "Scripts" / "python.exe").write_bytes(b"MZ")
    (env / "junk.py").write_bytes(b"pass\n")
    return tmp_path


@pytest.fixture
def service():
    return BundleToolService()


# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------

def test_a_plan_includes_source_and_prunes_the_environment(service, project):
    result = service.plan_bundle([project])
    included = result.plan.ordered_paths()
    assert "src/app.py" in included
    assert ".venv" in result.plan.pruned_roots
    assert not any(p.startswith(".venv/") for p in included)


def test_bft_source_root_gets_the_self_bundle_preset_before_descent(
        service, tmp_path):
    """Self-bundling must never recurse through BFT's generated work trees."""
    for relative in (
            "pyproject.toml", "bundle_config.json", "src/core/service.py",
            "src/ui/main_window.py"):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("marker\n", encoding="utf-8")
    (tmp_path / "tmp").mkdir()
    (tmp_path / "tmp" / "generated.txt").write_text(
        "generated\n", encoding="utf-8")

    automatic = service.plan_bundle([tmp_path])
    explicit_opt_out = service.plan_bundle([tmp_path], preset=[])

    assert automatic.presets_applied == ["bft-source"]
    assert any("automatically" in notice for notice in automatic.notices)
    assert "tmp" in automatic.plan.pruned_roots
    assert "tmp/generated.txt" not in automatic.plan.ordered_paths()
    assert explicit_opt_out.presets_applied == []
    assert "tmp/generated.txt" in explicit_opt_out.plan.ordered_paths()


def test_capacity_estimate_requires_confirmation_for_large_raw_input(
        service, project):
    planned = service.plan_bundle([project], include=["**/*.py"])
    enlarged = tuple(
        replace(decision, size=129 * 1024 * 1024)
        if decision.state is State.INCLUDED else decision
        for decision in planned.plan.decisions)
    estimate = replace(
        planned, plan=replace(planned.plan, decisions=enlarged)).estimate()

    assert estimate.level == "large"
    assert estimate.requires_confirmation is True
    assert estimate.output_bytes >= estimate.raw_bytes
    assert estimate.temporary_bytes >= estimate.output_bytes


def test_a_plan_opens_no_file(service, project):
    import builtins

    real_open = builtins.open
    opened = []
    builtins.open = lambda f, *a, **k: (opened.append(str(f)), real_open(f, *a, **k))[1]
    try:
        service.plan_bundle([project])
    finally:
        builtins.open = real_open
    assert [p for p in opened if str(project) in p] == []


def test_planning_twice_gives_the_same_answer(service, project):
    """Determinism is the precondition for a report anyone can diff."""
    first = service.plan_bundle([project], preset=["logs"])
    second = service.plan_bundle([project], preset=["logs"])
    assert first.plan.ordered_paths() == second.plan.ordered_paths()
    assert first.plan.rule_stack_digest == second.plan.rule_stack_digest


def test_a_different_rule_stack_gives_a_different_digest(service, project):
    plain = service.plan_bundle([project])
    presets = service.plan_bundle([project], preset=["logs"])
    assert plain.plan.rule_stack_digest != presets.plan.rule_stack_digest


def test_no_sources_is_refused(service):
    with pytest.raises(BundleFileToolError):
        service.plan_bundle([])


def test_the_base_path_of_a_single_directory_is_itself(service, project):
    assert service.plan_bundle([project]).base_path == project


def test_the_base_path_of_a_single_file_is_its_parent(service, project):
    result = service.plan_bundle([project / "src" / "app.py"])
    assert result.base_path == project / "src"


def test_multiple_sources_share_their_common_root(service, project):
    result = service.plan_bundle([project / "src", project / "docs"])
    assert result.base_path.resolve() == project.resolve()
    assert set(result.plan.ordered_paths()) == {
        "src/app.py", "src/util.py", "docs/guide.md"}


def test_overlapping_sources_do_not_duplicate_a_path(service, project):
    """Scanning a tree and its own subdirectory must index each file once."""
    result = service.plan_bundle([project, project / "src"])
    paths = result.plan.ordered_paths()
    assert len(paths) == len(set(paths))


# ---------------------------------------------------------------------------
# The ladder, through the facade
# ---------------------------------------------------------------------------

def test_include_narrows_the_bundle_rather_than_widening_it(service, project):
    """The Build 114 composition defect, pinned.

    The governed allow-list is `**/*`. If the base action were taken over the
    union of allow-lists it would always contain that catch-all, and --include
    would add a rule that changed nothing while appearing to filter.
    """
    result = service.plan_bundle([project], include=["src/**"])
    assert result.base_action == "exclude"
    assert result.plan.ordered_paths() == ["src/app.py", "src/util.py"]


def test_exclude_adds_to_the_defaults_instead_of_replacing_them(service, project):
    """Paul's ruling. Under the old behaviour one --exclude re-admitted every
    default exclusion, which is how a .git directory ends up in a bundle."""
    result = service.plan_bundle([project], exclude=["docs/**"])
    included = result.plan.ordered_paths()
    assert "docs/guide.md" not in included
    assert not any(p.startswith(".venv/") for p in included), (
        "one --exclude must not disable environment pruning")


def test_the_exclude_migration_notice_is_carried_on_the_result(service, project):
    result = service.plan_bundle([project], exclude=["docs/**"])
    assert any("--no-default-rules" in notice for notice in result.notices)


def test_no_default_rules_drops_the_governed_deny_list(service, project):
    with_defaults = service.plan_bundle([project])
    without = service.plan_bundle([project], no_default_rules=True)
    assert len(without.plan.included()) >= len(with_defaults.plan.included())
    assert any("Priority 0" in notice for notice in without.notices)


def test_priority_zero_survives_no_default_rules(service, tmp_path):
    """Disabling defaults must never disable the recursion blocks."""
    (tmp_path / "old_src_bundle.txt").write_bytes(b"nested\n")
    (tmp_path / "keep.py").write_bytes(b"x\n")
    result = service.plan_bundle([tmp_path], no_default_rules=True,
                                 force_include=["**/*"])
    decision = result.plan.explain("old_src_bundle.txt")
    assert decision.state is State.BLOCKED


def test_a_session_force_include_beats_a_preset(service, project):
    """A wheel can be carried through the archives preset, with confirmation."""
    result = service.plan_bundle([project], preset=["archives"],
                                 force_include=["**/*.whl"])
    decision = result.plan.explain("vendor.whl")
    assert decision.state is State.INCLUDED
    assert decision.confirm_required is True


def test_a_session_force_exclude_beats_everything_below_it(service, project):
    result = service.plan_bundle([project], include=["src/**"],
                                 force_exclude=["**/util.py"])
    assert result.plan.ordered_paths() == ["src/app.py"]


def test_a_preset_narrows_and_names_itself_on_the_result(service, project):
    result = service.plan_bundle([project], preset=["logs"])
    assert "notes.log" not in result.plan.ordered_paths()
    assert result.presets_applied == ["logs"]


def test_an_allow_list_preset_switches_the_base_action(service, project):
    result = service.plan_bundle([project], preset=["source-only"])
    assert result.base_action == "exclude"
    assert set(result.plan.ordered_paths()) == {"src/app.py", "src/util.py"}


def test_an_unknown_preset_fails_the_plan(service, project):
    with pytest.raises(RuleSourceError):
        service.plan_bundle([project], preset=["nope"])


def test_a_rules_file_is_applied_at_priority_two_a(service, project, tmp_path):
    rules = tmp_path / "team.json"
    rules.write_text(json.dumps({"version": 1, "deny": ["docs/**"]}),
                     encoding="utf-8")
    result = service.plan_bundle([project], rules=rules)
    assert "docs/guide.md" not in result.plan.ordered_paths()


def test_project_rules_outrank_the_command_line(service, project, tmp_path):
    """2a beats 2b, so a team's rule survives an individual's flag.

    Precedence is only exercised by a *conflict*. An earlier version of this
    test gave the two layers disjoint patterns and asserted a union - which
    both orderings satisfy, so it would have passed while proving nothing.
    That is the same defect the Build 113 group-order test had, and it is easy
    to write twice.
    """
    rules = tmp_path / "team.json"
    rules.write_text(json.dumps(
        {"version": 1, "rules": [{"action": "exclude", "pattern": "docs/**"}]}),
        encoding="utf-8")
    result = service.plan_bundle([project], rules=rules, include=["docs/**"])

    decision = result.plan.explain("docs/guide.md")
    assert decision.state is State.EXCLUDED, (
        "the project rule must beat the command-line include")
    assert decision.winning_layer.display == "2a"


def test_include_root_brings_a_pruned_subtree_back_into_the_plan(service, project):
    result = service.plan_bundle([project], include_roots=[".venv"],
                                 no_default_rules=True)
    assert ".venv/junk.py" in [d.path for d in result.plan.decisions]


def test_groups_reorder_emission_without_changing_inclusion(service, project):
    plain = service.plan_bundle([project])
    grouped = service.plan_bundle([project], groups=["docs=docs/**", "code=src/**"])
    assert set(plain.plan.ordered_paths()) == set(grouped.plan.ordered_paths())
    ordered = grouped.plan.ordered_paths()
    assert ordered.index("docs/guide.md") < ordered.index("src/app.py")


def test_reversing_group_order_reverses_emission(service, project):
    first = service.plan_bundle([project], groups=["docs=docs/**", "code=src/**"])
    second = service.plan_bundle([project], groups=["code=src/**", "docs=docs/**"])
    assert first.plan.ordered_paths() != second.plan.ordered_paths()
    assert set(first.plan.ordered_paths()) == set(second.plan.ordered_paths())


def test_a_malformed_group_fails_the_plan(service, project):
    with pytest.raises(RuleSourceError):
        service.plan_bundle([project], groups=["nodelimiter"])


# ---------------------------------------------------------------------------
# Explain
# ---------------------------------------------------------------------------

def test_explain_returns_the_chain_for_one_path(service, project):
    result = service.plan_bundle([project], preset=["logs"])
    text = service.explain_selection(result, "notes.log")
    assert "notes.log" in text
    assert "Excluded" in text


def test_explain_json_returns_data_not_text(service, project):
    result = service.plan_bundle([project])
    payload = service.explain_selection(result, "src/app.py", fmt="json")
    assert isinstance(payload, dict)
    assert payload["path"] == "src/app.py"
    assert payload["state"] == State.INCLUDED.value


def test_explain_without_a_path_covers_every_decision(service, project):
    result = service.plan_bundle([project])
    text = service.explain_selection(result)
    for decision in result.plan.decisions:
        assert decision.path in text


def test_explain_all_as_json_is_the_full_report(service, project):
    result = service.plan_bundle([project])
    payload = service.explain_selection(result, fmt="json")
    assert payload["decisions"] and "rule_stack_digest" in payload


def test_explaining_an_unknown_path_says_how_to_reach_it(service, project):
    """The pruned-subtree case: the answer is not 'no such file'."""
    result = service.plan_bundle([project])
    with pytest.raises(BundleFileToolError) as error:
        service.explain_selection(result, ".venv/junk.py")
    assert "--include-root" in str(error.value)


def test_an_unknown_explain_format_is_refused(service, project):
    result = service.plan_bundle([project])
    with pytest.raises(BundleFileToolError):
        service.explain_selection(result, "src/app.py", fmt="yaml")


# ---------------------------------------------------------------------------
# Preview and report
# ---------------------------------------------------------------------------

def test_preview_summarises_without_reading(service, project):
    result = service.plan_bundle([project])
    preview = service.preview_bundle(result)
    assert preview["file_count"] == len(result.plan.included())
    assert preview["estimated_bytes"] > 0
    assert preview["counts"][State.INCLUDED.value] == preview["file_count"]


def test_preview_truncates_and_says_so(service, project):
    result = service.plan_bundle([project])
    preview = service.preview_bundle(result, limit=1)
    assert len(preview["paths"]) == 1
    assert preview["truncated"] is True


def test_preview_without_a_limit_is_not_truncated(service, project):
    preview = service.preview_bundle(service.plan_bundle([project]))
    assert preview["truncated"] is False


def test_the_report_is_json_serialisable(service, project):
    result = service.plan_bundle([project], preset=["logs"])
    text = json.dumps(result.to_dict())
    assert json.loads(text)["base_action"] == "include"


def test_the_report_carries_no_absolute_path(service, project):
    """Paul's Build 131 note: no one's sibling paths in a shared artifact."""
    result = service.plan_bundle([project])
    assert str(project) not in json.dumps(result.to_dict())


def test_the_report_records_what_was_pruned_and_why(service, project):
    result = service.plan_bundle([project])
    detectors = result.to_dict()["detectors"]
    pruned = [row for row in detectors if row["path"] == ".venv"]
    assert pruned and pruned[0]["family"] == "python-venv"
    assert pruned[0]["evidence"]


def test_presets_are_listed_from_the_service(service):
    catalogue = service.presets()
    assert "python-env" in catalogue and "archives" in catalogue


# ---------------------------------------------------------------------------
# Executing a plan
# ---------------------------------------------------------------------------

def test_create_bundle_from_a_plan_writes_exactly_what_was_planned(
        service, project, tmp_path):
    result = service.plan_bundle([project], include=["src/**"])
    output = tmp_path / "out.txt"
    bundle = service.create_bundle(sources=[project], base_path=project,
                                   output_path=output, plan=result)
    assert bundle.file_count == len(result.plan.included())
    written = {entry.path.replace("\\", "/")
               for entry in bundle.manifest.entries}
    assert written == set(result.plan.ordered_paths())


def test_a_planned_bundle_does_not_re_decide(service, project, tmp_path):
    """A file appearing between plan and write must not sneak into the output."""
    result = service.plan_bundle([project], include=["src/**"])
    (project / "src" / "late.py").write_bytes(b"late\n")
    bundle = service.create_bundle(sources=[project], base_path=project,
                                   output_path=tmp_path / "o.txt", plan=result)
    written = {e.path.replace("\\", "/") for e in bundle.manifest.entries}
    assert "src/late.py" not in written


def test_a_plan_result_resolves_paths_back_to_disk(service, project):
    result = service.plan_bundle([project], include=["src/**"])
    for path in result.absolute_paths():
        assert path.exists()


def test_deleting_a_planned_file_aborts_without_publishing(
        service, project, tmp_path):
    """P0: a successful artifact may never silently omit an approved path."""
    result = service.plan_bundle([project], include=["src/**"])
    (project / "src" / "app.py").unlink()
    output = tmp_path / "must-not-exist.txt"

    with pytest.raises(PlanDriftError, match="re-plan"):
        service.create_bundle(
            sources=[project], base_path=project, output_path=output,
            plan=result)

    assert not output.exists()


def test_changing_a_planned_file_aborts_without_publishing(
        service, project, tmp_path):
    result = service.plan_bundle([project], include=["src/**"])
    (project / "src" / "app.py").write_text(
        "print('changed after review')\n", encoding="utf-8")
    output = tmp_path / "must-not-exist.txt"

    with pytest.raises(PlanDriftError, match="changed after review"):
        service.create_bundle(
            sources=[project], base_path=project, output_path=output,
            plan=result)

    assert not output.exists()


def test_writer_omission_is_rejected_before_publication(
        service, project, tmp_path, monkeypatch):
    """Even a downstream writer bug cannot weaken an approved plan."""
    import core.service as service_module

    result = service.plan_bundle([project], include=["src/**"])
    original = service_module.BundleCreator.create_manifest

    def omit_one(creator, *args, **kwargs):
        manifest = original(creator, *args, **kwargs)
        manifest.entries.pop()
        return manifest

    monkeypatch.setattr(service_module.BundleCreator, "create_manifest", omit_one)
    output = tmp_path / "must-not-exist.txt"

    with pytest.raises(PlanDriftError, match="manifest"):
        service.create_bundle(
            sources=[project], base_path=project, output_path=output,
            plan=result)
    assert not output.exists()


def test_atomic_publication_preserves_an_existing_artifact_on_failure(
        service, project, tmp_path, monkeypatch):
    import core.service as service_module

    result = service.plan_bundle([project], include=["src/**"])
    output = tmp_path / "existing.txt"
    output.write_text("previous artifact\n", encoding="utf-8")

    def fail_replace(_source, _target):
        raise OSError("simulated atomic replace failure")

    monkeypatch.setattr(service_module.os, "replace", fail_replace)
    with pytest.raises(BundleFileToolError, match="simulated atomic"):
        service.create_bundle(
            sources=[project], base_path=project, output_path=output,
            plan=result)

    assert output.read_text(encoding="utf-8") == "previous artifact\n"
    assert not list(tmp_path.glob(".existing.txt.*.tmp"))


def test_oversize_is_a_visible_plan_state_not_a_writer_surprise(
        service, tmp_path):
    root = tmp_path / "oversize"
    root.mkdir()
    (root / "small.txt").write_bytes(b"ok")
    (root / "large.bin").write_bytes(b"x" * 2048)

    result = service.plan_bundle([root], max_file_mb=0.001)

    skipped = result.plan.explain("large.bin")
    assert skipped is not None
    assert skipped.state is State.SKIPPED
    assert skipped.code == "SKIPPED_OVERSIZE"
    assert result.plan.ordered_paths() == ["small.txt"]

    bundle = service.create_bundle(
        sources=[root], base_path=root, max_file_mb=0.001, plan=result)
    assert [entry.path for entry in bundle.manifest.entries] == ["small.txt"]
    assert bundle.manifest.skipped_entries == []


def test_a_source_outside_the_base_is_blocked_during_planning(
        service, tmp_path):
    base = tmp_path / "base"
    source = tmp_path / "source"
    base.mkdir()
    source.mkdir()
    (source / "outside.txt").write_text("outside\n", encoding="utf-8")

    result = service.plan_bundle([source], base_path=base)
    decision = result.plan.decisions[0]

    assert decision.path == "../source/outside.txt"
    assert decision.state is State.BLOCKED
    assert decision.code == "BLOCKED_OUTSIDE_BASE"
    assert result.plan.ordered_paths() == []


def test_an_existing_active_output_is_blocked_in_the_plan(service, tmp_path):
    root = tmp_path / "active-output"
    root.mkdir()
    (root / "app.py").write_text("print(1)\n", encoding="utf-8")
    output = root / "result.txt"
    output.write_text("old artifact\n", encoding="utf-8")

    result = service.plan_bundle([root], output_path=output)
    decision = result.plan.explain("result.txt")

    assert decision is not None
    assert decision.state is State.BLOCKED
    assert decision.code == "BLOCKED_ACTIVE_OUTPUT"
    assert result.plan.ordered_paths() == ["app.py"]


def test_plan_result_convenience_accessors_agree(service, project):
    result = service.plan_bundle([project])
    assert result.file_count == len(result.included_paths)
    assert isinstance(result, PlanResult)


# ---------------------------------------------------------------------------
# The incremental re-decide must be indistinguishable from the full one
# ---------------------------------------------------------------------------

def full_replan(service, previous, overrides):
    """A full re-decide of the same inputs, bypassing the fast path."""
    inputs = dict(previous.inputs)
    inputs["overrides"] = [tuple(o) for o in overrides]
    return service._decide(previous.scan, previous.sources, previous.base_path,
                           inputs, generation=previous.plan.generation + 1)


def same_answer(left, right):
    return ([(d.path, d.state, d.winning_rule, d.group, d.confirm_required,
              tuple(e.to_dict()["rule"] for e in d.chain))
             for d in left.plan.decisions]
            == [(d.path, d.state, d.winning_rule, d.group, d.confirm_required,
                 tuple(e.to_dict()["rule"] for e in d.chain))
                for d in right.plan.decisions])


@pytest.mark.parametrize("sequence", [
    [("exclude", "docs/**")],
    [("include", "notes.log")],
    [("exclude", "src/**"), ("include", "src/app.py")],
    [("exclude", "**/*")],
    [("include", "**/*")],
    [("exclude", "docs/**"), ("exclude", "src/**"), ("include", "docs/**")],
    [("include", "vendor.whl")],
    [("exclude", "nothing-matches/**")],
    [],
])
def test_incremental_and_full_replans_agree(service, project, sequence):
    """The claim the fast path rests on, checked against the slow path.

    If the reasoning about which paths a Layer 1 change can reach is ever
    wrong, this fails - rather than a user's bundle quietly gaining or losing
    a file that the preview said nothing about.
    """
    base = service.plan_bundle([project])
    incremental = service.replan(base, overrides=sequence)
    full = full_replan(service, base, sequence)
    assert same_answer(incremental, full)


def test_the_two_paths_produce_the_same_digest_and_order(service, project):
    base = service.plan_bundle([project])
    sequence = [("exclude", "docs/**"), ("include", "docs/guide.md")]
    incremental = service.replan(base, overrides=sequence)
    full = full_replan(service, base, sequence)
    assert incremental.plan.rule_stack_digest == full.plan.rule_stack_digest
    assert incremental.plan.ordered_paths() == full.plan.ordered_paths()
    assert incremental.base_action == full.base_action


def test_a_chain_of_toggles_matches_replanning_from_scratch(service, project):
    """Twenty clicks in a row must not drift from a cold plan of the result."""
    result = service.plan_bundle([project])
    sequence = []
    for index in range(20):
        action = "exclude" if index % 2 else "include"
        pattern = ["docs/**", "src/**", "notes.log", "vendor.whl"][index % 4]
        sequence = [(a, p) for a, p in sequence if p != pattern]
        sequence.append((action, pattern))
        result = service.replan(result, overrides=sequence)

    cold = service.plan_bundle([project], overrides=sequence)
    assert result.plan.ordered_paths() == cold.plan.ordered_paths()


def test_changing_anything_but_overrides_still_takes_the_full_path(service, project):
    """The fast path is only valid when Layer 1 alone moved."""
    base = service.plan_bundle([project])
    with_preset = service.replan(base, preset=["logs"])
    assert "notes.log" not in with_preset.plan.ordered_paths()

    both = service.replan(base, preset=["logs"],
                          overrides=[("include", "notes.log")])
    assert "notes.log" in both.plan.ordered_paths()


def test_the_fast_path_still_increments_the_generation(service, project):
    base = service.plan_bundle([project])
    assert service.replan(base, overrides=[("exclude", "docs/**")]
                          ).plan.generation == base.plan.generation + 1


def test_preset_replan_reuses_safety_evidence_without_resolving_paths(
        service, project, monkeypatch):
    """Preset changes cannot repeat the Windows final-path walk."""
    base = service.plan_bundle([project])

    def forbidden(*_args, **_kwargs):
        raise AssertionError("preset replan repeated filesystem path resolution")

    monkeypatch.setattr(Path, "resolve", forbidden)
    changed = service.replan(base, preset=["logs"])

    assert "notes.log" not in changed.plan.ordered_paths()


def test_preset_replan_honours_cancel_during_rule_evaluation(service, project):
    base = service.plan_bundle([project])

    with pytest.raises(OperationCancelled) as caught:
        service.replan(base, preset=["logs"], cancel=lambda: True)

    assert caught.value.phase == "plan"
    assert caught.value.total == len(base.plan.decisions)
