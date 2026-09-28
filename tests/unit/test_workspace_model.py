# BFT_B115_WORKSPACE_MODEL_TESTS
# ============================================================================
# SOURCEFILE: test_workspace_model.py
# RELPATH: bundle_file_tool_v2/tests/unit/test_workspace_model.py
# PROJECT: Bundle File Tool v2.2
# VERSION: 2.1.115
# LIFECYCLE: Testing
# STATUS: Build 115 - WP4 - BFT_B115_WORKSPACE_MODEL_TESTS
# ============================================================================
"""The desktop workspace's behaviour, asserted without a display.

Every acceptance criterion in spec §18.1 that concerns the UI is checked here
rather than through a widget, because a Tk assertion can only tell you a string
appeared - not that the tri-state was computed correctly, that a folder toggle
produced exactly one override, or that the counts reconcile with the plan.
"""

from __future__ import annotations

import pytest

from core.selection import State
from core.service import BundleToolService
from ui.workspace_model import (
    VIEW_ALL,
    VIEW_BLOCKED,
    VIEW_EXCLUDED,
    VIEW_INCLUDED,
    TriState,
    WorkspaceModel,
    human_bytes,
)


@pytest.fixture
def tree(tmp_path):
    """The developer scenario from spec §8, in miniature."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_bytes(b"print(1)\n")
    (tmp_path / "src" / "util.py").write_bytes(b"x = 2\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_app.py").write_bytes(b"def test(): pass\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guide.md").write_bytes(b"# guide\n")
    (tmp_path / "out").mkdir()
    (tmp_path / "out" / "built.js").write_bytes(b"var x;\n")
    (tmp_path / "notes.log").write_bytes(b"noise\n")

    env = tmp_path / ".venv312"
    (env / "Scripts").mkdir(parents=True)
    (env / "Lib" / "site-packages").mkdir(parents=True)
    (env / "pyvenv.cfg").write_bytes(b"home = C\n")
    (env / "Scripts" / "python.exe").write_bytes(b"MZ")
    for index in range(20):
        (env / "Lib" / "site-packages" / f"v{index}.py").write_bytes(b"pass\n")
    return tmp_path


@pytest.fixture
def service():
    return BundleToolService()


@pytest.fixture
def model(service, tree):
    return WorkspaceModel(
        service, service.plan_bundle([tree], preset=["python-env"]))


# ---------------------------------------------------------------------------
# SEL-F-001 / §8 - the screenshot case, as a workspace
# ---------------------------------------------------------------------------

def test_the_environment_appears_as_one_excluded_root(model):
    """Not thousands of site-package rows. That was the original complaint."""
    nodes = {node.path: node for node in model.tree(expanded=[])}
    assert ".venv312" in nodes
    assert not any(path.startswith(".venv312/") for path in nodes)


def test_the_environment_root_carries_a_readable_reason(model):
    node = model.node_for(".venv312")
    assert node.badge == "Python env"
    assert node.pruned is True


def test_a_pruned_root_never_reports_a_descendant_count(model):
    """§7.4: BFT must not imply it inspected files it did not walk.

    A "0" here would be exactly that implication, and the 20 files really are
    there - they were simply never enumerated.
    """
    node = model.node_for(".venv312")
    assert node.count_text == "not enumerated"
    assert node.enumerated is False
    assert "not enumerated" in node.accessible_text()


def test_the_summary_names_pruned_roots_rather_than_inventing_a_file_count(model):
    assert "1 pruned root" in model.summary().headline()


# ---------------------------------------------------------------------------
# Tri-state (§7.2)
# ---------------------------------------------------------------------------

def test_a_fully_included_folder_is_checked(model):
    assert model.node_for("src").state is TriState.CHECKED


def test_a_partially_included_folder_is_partial(model):
    model.set_file("src/util.py", include=False)
    assert model.node_for("src").state is TriState.PARTIAL


def test_a_wholly_excluded_folder_is_unchecked(model):
    model.set_folder("src", include=False)
    assert model.node_for("src").state is TriState.UNCHECKED


def test_partial_is_a_third_state_not_a_rounded_one(model):
    """The state that makes a folder tree honest about mixed contents."""
    model.set_file("src/util.py", include=False)
    node = model.node_for("src")
    assert node.state is TriState.PARTIAL
    assert (node.included, node.total) == (1, 2)


def test_tree_rows_carry_spoken_text_for_every_state(model):
    for node in model.tree(expanded=["src"]):
        spoken = node.accessible_text()
        assert node.label in spoken
        assert node.state.value in spoken


def test_expandability_is_known_before_children_are_rendered(model):
    assert model.has_children("src") is True
    assert model.has_children("src/app.py") is False
    assert model.has_children(".venv312") is False


# ---------------------------------------------------------------------------
# SEL-F-003 - one scoped override, not per-file mutations
# ---------------------------------------------------------------------------

def test_unchecking_a_folder_creates_exactly_one_override(model):
    model.set_folder("src", include=False)
    assert model.overrides == [("exclude", "src/**")]


def test_one_folder_override_moves_every_descendant(model):
    model.set_folder("src", include=False)
    rows = {row.path: row for row in model.rows(view=VIEW_ALL)}
    assert rows["src/app.py"].state == State.EXCLUDED.value
    assert rows["src/util.py"].state == State.EXCLUDED.value


def test_re_toggling_a_folder_replaces_rather_than_accumulates(model):
    """Otherwise the override count climbs forever and stops meaning anything."""
    model.set_folder("src", include=False)
    model.set_folder("src", include=True)
    assert len(model.overrides) == 1
    assert model.overrides[0][0] == "include"


def test_a_later_click_on_a_child_beats_an_earlier_one_on_its_parent(model):
    """Layer 1 is last-match-wins, so click order has to be preserved.

    Before this was fixed, unchecking a folder and then re-checking a child did
    nothing at all - every include was emitted before every exclude regardless
    of what the operator did last.
    """
    model.set_folder("docs", include=False)
    model.set_file("docs/guide.md", include=True)
    row = {r.path: r for r in model.rows()}["docs/guide.md"]
    assert row.state == State.INCLUDED.value


def test_clearing_an_override_restores_the_rule_result(model):
    """§7.2: clearing restores; it does not blindly invert."""
    before = model.node_for("docs").state
    model.set_folder("docs", include=False)
    model.clear_override("docs/**")
    assert model.overrides == []
    assert model.node_for("docs").state is before


def test_clear_all_overrides_returns_to_the_underlying_plan(model):
    baseline = {row.path: row.state for row in model.rows()}
    model.set_folder("src", include=False)
    model.set_file("docs/guide.md", include=False)
    model.clear_all_overrides()
    assert {row.path: row.state for row in model.rows()} == baseline


def test_an_override_is_visible_on_the_node_it_scopes(model):
    model.set_folder("src", include=False)
    assert model.node_for("src").overridden is True
    assert model.node_for("docs").overridden is False


def test_toggle_uses_the_right_scope_for_files_and_folders(model):
    model.toggle("src")
    assert model.overrides == [("exclude", "src/**")]
    model.clear_all_overrides()
    model.toggle("src/app.py")
    assert model.overrides == [("exclude", "src/app.py")]


def test_toggling_an_unknown_path_is_an_error_not_a_silent_no_op(model):
    with pytest.raises(KeyError):
        model.toggle("does/not/exist.py")


# ---------------------------------------------------------------------------
# SEL-F-004 - views and counts reconcile with the plan
# ---------------------------------------------------------------------------

def test_view_counts_match_the_plan_exactly(model):
    counts = model.counts_for_views()
    plan = model.result.plan.counts()
    assert counts[VIEW_ALL] == len(model.result.plan.decisions)
    assert counts[VIEW_INCLUDED] == plan[State.INCLUDED.value]
    assert counts[VIEW_EXCLUDED] == plan[State.EXCLUDED.value]
    assert counts[VIEW_BLOCKED] == plan[State.BLOCKED.value]


def test_each_view_returns_only_its_own_state(model):
    assert all(r.included for r in model.rows(view=VIEW_INCLUDED))
    assert all(r.state == State.EXCLUDED.value
               for r in model.rows(view=VIEW_EXCLUDED))


def test_the_all_view_returns_every_decision(model):
    assert len(model.rows(view=VIEW_ALL)) == len(model.result.plan.decisions)


def test_an_unknown_view_is_refused(model):
    with pytest.raises(ValueError):
        model.rows(view="sideways")


def test_included_rows_come_back_in_emission_order(model):
    rows = [r.path for r in model.rows(view=VIEW_INCLUDED)]
    assert rows == model.result.plan.ordered_paths()


def test_search_matches_paths(model):
    assert {r.path for r in model.rows(search="util")} == {"src/util.py"}


def test_search_also_matches_reasons(service, tree):
    """"Filter paths or reasons" - so you can find everything one rule touched.

    Searched against the file-pattern half of `logs`, because whole-directory
    exclusions are pruned before descent and therefore do not create file
    decisions. A matching `*.log` is still walked and carries a searchable
    reason.
    """
    model = WorkspaceModel(
        service, service.plan_bundle([tree], preset=["logs"]))
    rows = model.rows(view=VIEW_EXCLUDED, search="logs")
    assert rows, "no row matched the rule name"
    assert all("logs" in r.reason.lower() for r in rows)
    assert "notes.log" in {r.path for r in rows}


def test_search_is_case_insensitive(model):
    assert model.rows(search="UTIL") == model.rows(search="util")


def test_a_search_matching_nothing_returns_nothing_rather_than_everything(model):
    assert model.rows(search="zzz-no-such-path") == []


def test_rows_can_be_limited_for_a_viewport(model):
    assert len(model.rows(limit=2)) == 2


# ---------------------------------------------------------------------------
# SEL-F-002 - no decision is unexplained
# ---------------------------------------------------------------------------

def test_every_row_carries_state_rule_and_layer(model):
    for row in model.rows():
        assert row.state
        assert row.reason
        assert row.rule_label


def test_the_inspector_explains_a_pruned_root_by_signature(model):
    """The §8 sentence, on the row the operator can actually click.

    The files under a pruned root are not in the plan - that is the whole
    point of pruning - so the folder itself must carry the explanation. An
    earlier version of this test asked about a file inside the environment and
    could never have passed for the right reason.
    """
    view = model.inspector(".venv312")
    assert view is not None
    assert "Python env" in view.headline
    assert "regardless of folder name" in view.headline
    assert "never enumerated" in view.headline


def test_the_pruned_root_offers_to_scan_rather_than_to_override(model):
    """Descending is a re-scan, not a rule override, and says so."""
    assert model.inspector(".venv312").override_action == "Scan this folder anyway"


def test_an_ordinary_folder_reports_its_included_share(model):
    view = model.inspector("src")
    assert view.headline == "2 of 2 files included."


def test_the_inspector_offers_an_override_for_an_ordinary_exclusion(model):
    view = model.inspector("notes.log")
    assert view.can_override is True
    assert view.override_action == "Override for session"


def test_an_overridden_path_offers_to_restore_the_rule_result(model):
    model.set_file("notes.log", include=True)
    assert model.inspector("notes.log").override_action == "Restore rule result"


def test_a_blocked_path_cannot_be_overridden_from_the_inspector(tmp_path, service):
    (tmp_path / "old_src_bundle.txt").write_bytes(b"nested\n")
    (tmp_path / "keep.py").write_bytes(b"x\n")
    model = WorkspaceModel(service, service.plan_bundle([tmp_path]))
    view = model.inspector("old_src_bundle.txt")
    assert view.can_override is False
    assert "cannot be overridden" in view.headline.lower()


def test_the_inspector_carries_the_full_chain_not_just_the_winner(model):
    view = model.inspector("notes.log")
    assert view.chain, "the chain was empty"


def test_the_inspector_returns_none_for_a_path_outside_the_plan(model):
    assert model.inspector(".venv312/site-packages/v0.py") is None


# ---------------------------------------------------------------------------
# Rules in effect (§7.1) and governed lock (§7.3)
# ---------------------------------------------------------------------------

def test_rules_in_effect_are_ordered_by_priority(model):
    layers = [rule.layer for rule in model.rules_in_effect()]
    assert layers == sorted(layers, key=lambda d: {"0": 0, "1": 1, "2a": 2,
                                                   "2b": 3, "3": 4, "4": 5,
                                                   "5": 6, "6": 7}[d])


def test_governed_rules_are_marked_locked(model):
    governed = [rule for rule in model.rules_in_effect() if rule.layer == "5"]
    assert governed, "no governed rules were listed"
    assert all(rule.locked for rule in governed)


def test_preset_rules_are_not_locked(model):
    presets = [rule for rule in model.rules_in_effect() if rule.layer == "4"]
    assert presets and not any(rule.locked for rule in presets)


def test_a_rule_row_lists_its_patterns(model):
    assert all(rule.patterns for rule in model.rules_in_effect())


# ---------------------------------------------------------------------------
# Bulk actions (§7.2)
# ---------------------------------------------------------------------------

def test_a_bulk_action_states_its_scope_before_running(model):
    scope = model.bulk_scope("Exclude", view=VIEW_INCLUDED)
    assert scope.describe() == f"Exclude {scope.count} visible files"
    assert scope.count == len(model.rows(view=VIEW_INCLUDED))


def test_bulk_scope_singularises_one_file(model):
    scope = model.bulk_scope("Exclude", search="util")
    assert scope.describe() == "Exclude 1 visible file"


def test_a_bulk_action_applies_only_to_the_visible_set(model):
    model.apply_bulk(False, view=VIEW_ALL, search="src/")
    rows = {row.path: row.state for row in model.rows()}
    assert rows["src/app.py"] == State.EXCLUDED.value
    assert rows["docs/guide.md"] == State.INCLUDED.value


def test_a_bulk_action_over_an_empty_view_changes_nothing(model):
    before = {row.path: row.state for row in model.rows()}
    model.apply_bulk(False, search="zzz-nothing")
    assert {row.path: row.state for row in model.rows()} == before


# ---------------------------------------------------------------------------
# Undo / redo (§7.2)
# ---------------------------------------------------------------------------

def test_undo_reverses_the_last_override(model):
    model.set_folder("src", include=False)
    model.undo()
    assert model.overrides == []
    assert model.node_for("src").state is TriState.CHECKED


def test_redo_reapplies_it(model):
    model.set_folder("src", include=False)
    model.undo()
    model.redo()
    assert model.overrides == [("exclude", "src/**")]


def test_undo_walks_back_through_several_actions(model):
    model.set_folder("src", include=False)
    model.set_folder("docs", include=False)
    model.undo()
    assert model.overrides == [("exclude", "src/**")]
    model.undo()
    assert model.overrides == []


def test_undo_at_the_beginning_is_a_no_op_not_an_error(model):
    assert model.can_undo is False
    model.undo()
    assert model.overrides == []


def test_redo_at_the_end_is_a_no_op_not_an_error(model):
    assert model.can_redo is False
    model.redo()
    assert model.overrides == []


def test_a_new_action_discards_the_redo_branch(model):
    model.set_folder("src", include=False)
    model.undo()
    model.set_folder("docs", include=False)
    assert model.can_redo is False


# ---------------------------------------------------------------------------
# Presets, groups and pruned-root descent
# ---------------------------------------------------------------------------

def test_changing_the_preset_recomputes_without_reading(model, tree):
    import builtins

    real_open = builtins.open
    opened = []
    builtins.open = lambda f, *a, **k: (opened.append(str(f)),
                                        real_open(f, *a, **k))[1]
    try:
        model.set_presets(["python-env", "logs"])
    finally:
        builtins.open = real_open
    assert [p for p in opened if str(tree) in p] == []
    assert "notes.log" not in model.result.plan.ordered_paths()


def test_groups_change_emission_order_only(model):
    before = set(model.result.plan.ordered_paths())
    model.set_groups(["docs=docs/**", "code=src/**"])
    after = model.result.plan.ordered_paths()
    assert set(after) == before
    assert after.index("docs/guide.md") < after.index("src/app.py")


def test_include_root_brings_a_pruned_subtree_into_the_plan(model):
    model.include_root(".venv312")
    assert any(p.startswith(".venv312/")
               for p in (d.path for d in model.result.plan.decisions))


def test_include_root_is_a_new_generation_not_a_mutation(model):
    before = model.result.plan.generation
    model.include_root(".venv312")
    assert model.result.plan.generation != before or model.result.scan.scanned > 0


# ---------------------------------------------------------------------------
# Review gate (§7.2) and footer honesty
# ---------------------------------------------------------------------------

def test_a_clean_selection_needs_no_review(model):
    assert model.needs_review() == []


def test_a_blocked_path_forces_a_review(tmp_path, service):
    (tmp_path / "old_src_bundle.txt").write_bytes(b"nested\n")
    (tmp_path / "keep.py").write_bytes(b"x\n")
    model = WorkspaceModel(service, service.plan_bundle([tmp_path]))
    assert any("blocked" in reason for reason in model.needs_review())


def test_a_confirmable_override_forces_a_review(tmp_path, service):
    (tmp_path / "vendor.whl").write_bytes(b"PK\x03\x04")
    (tmp_path / "keep.py").write_bytes(b"x\n")
    model = WorkspaceModel(
        service, service.plan_bundle([tmp_path], preset=["archives"]))
    model.set_file("vendor.whl", include=True)
    assert any("confirmation" in reason for reason in model.needs_review())


def test_the_footer_claims_only_what_this_build_does(model):
    """WP5 adds cache figures. Until then the footer must not imply one."""
    status = model.status_text()
    assert "without reading content" in status
    assert "cache" not in status.lower()


# ---------------------------------------------------------------------------
# Layering
# ---------------------------------------------------------------------------

def test_the_view_model_imports_no_toolkit():
    """SEL-X-002's structural half: the model must stay testable headless."""
    import ast
    import pathlib

    source = pathlib.Path("src/ui/workspace_model.py").read_text(encoding="utf-8")
    imported = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert "tkinter" not in imported
    assert "pythermx" not in imported


@pytest.mark.parametrize("count,expected", [
    (0, "0 B"), (2048, "2.0 KB"), (5 * 1024 ** 2, "5.0 MB"),
])
def test_byte_counts_read_naturally(count, expected):
    assert human_bytes(count) == expected
