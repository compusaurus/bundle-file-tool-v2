# BFT_B115_WORKSPACE_DIALOGS_TK_TESTS
# ============================================================================
# SOURCEFILE: test_workspace_dialogs_tk.py
# RELPATH: bundle_file_tool_v2/tests/integration/test_workspace_dialogs_tk.py
# PROJECT: Bundle File Tool v2.2
# VERSION: 2.1.115
# LIFECYCLE: Testing
# STATUS: Build 115 - WP4 - BFT_B115_WORKSPACE_DIALOGS_TK_TESTS
# ============================================================================
"""The command flows: rule editor, review export, bulk actions, create bundle.

These are the paths a user actually drives, and the ones least likely to be
exercised by accident. They all end in a modal - a file chooser or a
confirmation - so these tests replace each modal with a stub that records
what it was asked and answers deterministically. The companion
test_native_save_dialog_tk.py also drives the real X11 chooser.

Two things are asserted throughout: that a cancelled dialog changes nothing,
and that a confirmation is genuinely required before anything destructive or
irreversible happens.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.service import BundleToolService
from core.user_state import UserStateStore
from ui.rule_editor import ReviewReportDialog, ReviewSelectionDialog, RuleEditorDialog
from ui.selection_workspace import SelectionWorkspaceFrame
from ui.workspace_model import VIEW_INCLUDED, WorkspaceModel


@pytest.fixture
def project(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_bytes(b"print(1)\n")
    (tmp_path / "src" / "util.py").write_bytes(b"x = 2\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guide.md").write_bytes(b"# guide\n")
    (tmp_path / "notes.log").write_bytes(b"noise\n")
    return tmp_path


@pytest.fixture
def frame(tk_root, project):
    widget = SelectionWorkspaceFrame(tk_root, service=BundleToolService())
    widget.source_var.set(str(project))
    widget.rescan()
    tk_root.update_idletasks()
    yield widget
    widget.destroy()


@pytest.fixture
def answers(monkeypatch):
    """Stubs for every modal, recording what was asked."""
    state = {
        "asked": [],
        "yes": True,
        "save": "",
        "info": [],
        "save_kwargs": [],
        "directory_kwargs": [],
    }

    import ui.rule_editor as editor_module
    import ui.selection_workspace as workspace_module

    def ask(title, message, **options):
        state["asked"].append((title, message))
        state.setdefault("dialog_options", []).append(options)
        return state["yes"]

    def save(**kwargs):
        state["save_kwargs"].append(kwargs)
        return state["save"]

    def directory(**kwargs):
        state["directory_kwargs"].append(kwargs)
        return state["save"]

    def info(title, message, **options):
        state["info"].append((title, message))
        state.setdefault("dialog_options", []).append(options)

    for module in (workspace_module, editor_module):
        monkeypatch.setattr(module.messagebox, "askyesno", ask, raising=False)
        monkeypatch.setattr(module.messagebox, "showinfo", info, raising=False)
        monkeypatch.setattr(module.messagebox, "showerror", info, raising=False)
        monkeypatch.setattr(module.filedialog, "asksaveasfilename", save,
                            raising=False)
        monkeypatch.setattr(module.filedialog, "askdirectory", directory,
                            raising=False)
    return state


# ---------------------------------------------------------------------------
# Bulk actions must be confirmed
# ---------------------------------------------------------------------------

def test_a_bulk_action_asks_before_it_acts(frame, answers, tk_root):
    frame.apply_bulk(False)
    tk_root.update_idletasks()
    assert answers["asked"], "the bulk action ran without asking"
    assert "visible" in answers["asked"][0][1]


def test_declining_a_bulk_action_changes_nothing(frame, answers, tk_root):
    answers["yes"] = False
    frame.apply_bulk(False)
    tk_root.update_idletasks()
    assert frame.model.overrides == []


def test_accepting_a_bulk_action_applies_it(frame, answers, tk_root):
    frame.search_var.set("util")
    tk_root.update_idletasks()
    frame.apply_bulk(False)
    tk_root.update_idletasks()
    assert ("exclude", "src/util.py") in frame.model.overrides


def test_a_bulk_action_over_nothing_does_not_even_ask(frame, answers, tk_root):
    frame.search_var.set("zzz-nothing")
    tk_root.update_idletasks()
    frame.apply_bulk(False)
    assert answers["asked"] == []


def test_clear_overrides_restores_the_plan(frame, answers, tk_root):
    frame.model.set_folder("src", include=False)
    frame.refresh_all()
    frame.clear_overrides()
    tk_root.update_idletasks()
    assert frame.model.overrides == []


# ---------------------------------------------------------------------------
# Inspector override flow
# ---------------------------------------------------------------------------

def test_overriding_from_the_inspector_changes_the_decision(frame, answers,
                                                            tk_root):
    frame.view_var.set("all")
    frame.refresh_decisions()
    frame.decision_tree.selection_set("notes.log")
    frame._on_decision_select()
    frame.override_selected()
    tk_root.update_idletasks()
    assert ("include", "notes.log") in frame.model.overrides


def test_a_confirmable_override_asks_first(tk_root, tmp_path, answers):
    """A wheel behind the archives default: allowed, but deliberately."""
    (tmp_path / "vendor.whl").write_bytes(b"PK\x03\x04")
    (tmp_path / "keep.py").write_bytes(b"x\n")
    widget = SelectionWorkspaceFrame(tk_root, service=BundleToolService())
    widget.source_var.set(str(tmp_path))
    widget.preset_var.set("archives")
    widget.rescan()
    widget.model.set_presets(["archives"])
    widget.refresh_all()

    widget._selected_path = "vendor.whl"
    answers["yes"] = False
    widget.override_selected()
    tk_root.update_idletasks()
    assert widget.model.overrides == [], "an unconfirmed override was applied"

    answers["yes"] = True
    widget.override_selected()
    tk_root.update_idletasks()
    assert ("include", "vendor.whl") in widget.model.overrides
    widget.destroy()


def test_overriding_with_nothing_selected_is_harmless(frame, answers):
    frame._selected_path = ""
    frame.override_selected()
    assert frame.model.overrides == []


def test_a_folder_override_uses_folder_scope(frame, answers, tk_root):
    frame._selected_path = "src"
    frame.override_selected()
    tk_root.update_idletasks()
    assert frame.model.overrides == [("exclude", "src/**")]


# ---------------------------------------------------------------------------
# Remembered dialog locations and Create bundle
# ---------------------------------------------------------------------------

def test_source_browse_uses_and_persists_its_last_folder(
        tk_root, tmp_path, answers, monkeypatch):
    remembered = tmp_path / "previous-source"
    chosen = tmp_path / "chosen-source"
    remembered.mkdir()
    chosen.mkdir()
    state_file = tmp_path / "state" / "user_state.json"
    state = UserStateStore(str(state_file))
    state.set_and_save("last_source_dir", str(remembered))

    widget = SelectionWorkspaceFrame(
        tk_root, service=BundleToolService(), user_state=state)
    rescans = []
    monkeypatch.setattr(widget, "rescan", lambda: rescans.append(True))
    answers["save"] = str(chosen)

    widget.select_source()

    assert answers["directory_kwargs"][-1]["initialdir"] == str(remembered)
    assert widget.source_var.get() == str(chosen)
    assert rescans == [True]
    assert UserStateStore(str(state_file)).get("last_source_dir") == str(chosen)
    widget.destroy()


def test_create_dialog_uses_output_folder_and_suggests_bundle_name(
        frame, answers, tmp_path, project, tk_root):
    remembered = tmp_path / "previous-bundles"
    destination_dir = tmp_path / "new-bundles"
    remembered.mkdir()
    destination_dir.mkdir()
    state_file = tmp_path / "state" / "user_state.json"
    state = UserStateStore(str(state_file))
    state.set_and_save("last_bundle_save_dir", str(remembered))
    frame.user_state = state
    target = destination_dir / "chosen-name.txt"
    answers["save"] = str(target)

    frame.create_bundle()
    tk_root.update_idletasks()

    dialog = answers["save_kwargs"][-1]
    assert dialog["initialdir"] == str(remembered)
    assert dialog["initialfile"] == f"{project.name}_bundle.txt"
    assert target.exists()
    assert UserStateStore(str(state_file)).get(
        "last_bundle_save_dir") == str(destination_dir)


def test_cancelling_create_keeps_the_remembered_output_folder(
        frame, answers, tmp_path, tk_root):
    remembered = tmp_path / "remembered-bundles"
    remembered.mkdir()
    state_file = tmp_path / "state" / "user_state.json"
    state = UserStateStore(str(state_file))
    state.set_and_save("last_bundle_save_dir", str(remembered))
    frame.user_state = state
    answers["save"] = ""

    frame.create_bundle()
    tk_root.update_idletasks()

    assert answers["save_kwargs"][-1]["initialdir"] == str(remembered)
    assert UserStateStore(str(state_file)).get(
        "last_bundle_save_dir") == str(remembered)


def test_create_bundle_writes_what_the_workspace_showed(frame, answers,
                                                        tmp_path, tk_root):
    target = tmp_path / "bundle.txt"
    answers["save"] = str(target)
    shown = [row.path for row in frame.model.rows(view=VIEW_INCLUDED)]

    frame.create_bundle()
    tk_root.update_idletasks()

    assert target.exists()
    text = target.read_text(encoding="utf-8")
    for path in shown:
        assert path in text
    assert "Bundle created" in frame.status_var.get()


def test_cancelling_the_save_dialog_writes_nothing(frame, answers, tmp_path,
                                                   tk_root):
    answers["save"] = ""
    frame.create_bundle()
    tk_root.update_idletasks()
    assert list(tmp_path.glob("*.txt")) == []


def test_copy_to_clipboard_uses_the_reconciled_workspace_plan(
        frame, answers, monkeypatch, tk_root):
    copied = []
    monkeypatch.setattr(frame, "clipboard_clear", lambda: copied.clear())
    monkeypatch.setattr(frame, "clipboard_append", copied.append)
    monkeypatch.setattr(frame, "update", lambda: None)

    shown = [row.path for row in frame.model.rows(view=VIEW_INCLUDED)]
    frame.copy_to_clipboard()
    tk_root.update_idletasks()

    assert len(copied) == 1
    for path in shown:
        assert path in copied[0]
    assert "Copied reconciled bundle" in frame.status_var.get()


def test_create_bundle_reviews_open_items_first(tk_root, tmp_path, monkeypatch):
    """§7.2: a final review when warnings or blocked candidates remain.

    The review is a real dialog driven by `wait_window`, so a test has to
    answer it. Leaving it unanswered blocks the entire run - which is exactly
    what happened when this test still assumed the old Yes/No messagebox and
    the suite sat for ten minutes on an invisible window.
    """
    (tmp_path / "old_src_bundle.txt").write_bytes(b"nested\n")
    (tmp_path / "keep.py").write_bytes(b"x\n")
    widget = SelectionWorkspaceFrame(tk_root, service=BundleToolService())
    widget.source_var.set(str(tmp_path))
    widget.rescan()

    shown = {}

    class Answered:
        def __init__(self, parent, reasons, blocked=()):
            shown["reasons"] = list(reasons)
            shown["blocked"] = list(blocked)
            self.choice = "cancel"

    import ui.rule_editor as editor_module
    monkeypatch.setattr(editor_module, "ReviewSelectionDialog", Answered)
    monkeypatch.setattr(widget, "wait_window", lambda _dialog: None)

    widget.create_bundle()
    tk_root.update_idletasks()

    assert shown, "no review was offered"
    assert any("blocked" in reason for reason in shown["reasons"])
    assert shown["blocked"], "the blocked paths were not offered for exclusion"
    widget.destroy()


def test_create_bundle_before_planning_is_harmless(tk_root, answers):
    widget = SelectionWorkspaceFrame(tk_root, service=BundleToolService())
    widget.create_bundle()
    assert answers["asked"] == []
    widget.destroy()


def test_review_selection_is_placed_relative_to_its_invoking_window(
        tk_root, monkeypatch):
    import ui.rule_editor as editor_module

    placements = []
    monkeypatch.setattr(
        editor_module,
        "place_toplevel_on_parent_monitor",
        lambda window, parent: placements.append((window, parent)) or True,
    )

    dialog = ReviewSelectionDialog(tk_root, ["1 path is blocked"])
    try:
        assert placements == [(dialog, tk_root)]
    finally:
        dialog.destroy()


# ---------------------------------------------------------------------------
# The rule editor dialog
# ---------------------------------------------------------------------------

@pytest.fixture
def editor(frame, tk_root):
    dialog = RuleEditorDialog(frame, frame.model)
    tk_root.update_idletasks()
    yield dialog
    dialog.destroy()


def test_the_editor_lists_the_active_ladder(editor):
    assert editor.rules.get_children()


def test_the_editor_marks_governed_rules_locked(editor):
    labels = [editor.rules.item(item, "text")
              for item in editor.rules.get_children()]
    assert any("locked" in label for label in labels)


def test_the_preview_updates_as_a_pattern_is_typed(editor, tk_root):
    editor.pattern_var.set("src/**")
    tk_root.update_idletasks()
    assert "matches 2 paths" in editor.preview_var.get()


def test_apply_is_disabled_until_a_pattern_matches(editor, tk_root):
    editor.pattern_var.set("nothing-here/**")
    tk_root.update_idletasks()
    assert str(editor.apply_btn.cget("state")) == "disabled"
    editor.pattern_var.set("src/**")
    tk_root.update_idletasks()
    assert str(editor.apply_btn.cget("state")) == "normal"


def test_applying_a_rule_adds_a_session_override(editor, tk_root):
    editor.pattern_var.set("docs/**")
    editor.action_var.set("exclude")
    tk_root.update_idletasks()
    editor.apply_rule()
    tk_root.update_idletasks()
    assert ("exclude", "docs/**") in editor.model.overrides
    assert editor.pattern_var.get() == "", "the field was not cleared"


def test_applying_an_empty_pattern_does_nothing(editor):
    editor.pattern_var.set("   ")
    editor.apply_rule()
    assert editor.model.overrides == []


def test_the_editor_can_clear_every_override(editor, tk_root):
    editor.model.set_folder("src", include=False)
    editor.clear_overrides()
    tk_root.update_idletasks()
    assert editor.model.overrides == []


def test_exporting_a_rule_file_writes_valid_json(editor, answers, tmp_path,
                                                 tk_root):
    editor.model.set_folder("docs", include=False)
    target = tmp_path / "team.json"
    answers["save"] = str(target)
    editor.export_rules()
    tk_root.update_idletasks()

    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["version"] == 1
    assert payload["rules"] == [{"action": "exclude", "pattern": "docs/**"}]
    assert answers["info"], "the export was not acknowledged"


def test_an_exported_rule_file_is_accepted_by_the_loader(editor, answers,
                                                         tmp_path, project):
    """The export must be readable by --rules, or it is a dead artifact."""
    from core.rule_sources import load_rules_file

    editor.model.set_folder("docs", include=False)
    target = tmp_path / "team.json"
    answers["save"] = str(target)
    editor.export_rules()

    stack = load_rules_file(target)
    assert [rule.pattern for rule in stack.rules] == ["docs/**"]


def test_cancelling_the_export_writes_nothing(editor, answers, tmp_path):
    answers["save"] = ""
    editor.export_rules()
    assert list(tmp_path.glob("*.json")) == []


# ---------------------------------------------------------------------------
# The review dialog
# ---------------------------------------------------------------------------

@pytest.fixture
def review(frame, tk_root):
    dialog = ReviewReportDialog(frame, frame.model)
    tk_root.update_idletasks()
    yield dialog
    dialog.destroy()


def test_the_review_dialog_renders_the_report(review):
    body = review.text.get("1.0", "end")
    assert "SELECTION REPORT" in body
    assert "COUNTS BY STATE" in body


def test_the_review_text_is_read_only(review):
    assert str(review.text.cget("state")) == "disabled"


def test_exporting_the_review_as_json_matches_the_plan(review, answers,
                                                       tmp_path):
    target = tmp_path / "report.json"
    answers["save"] = str(target)
    review.export_json()
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["decisions"]
    assert payload["counts"] == review.model.result.plan.counts()


def test_exporting_the_review_as_text_matches_what_is_shown(review, answers,
                                                            tmp_path):
    target = tmp_path / "report.txt"
    answers["save"] = str(target)
    review.export_text()
    assert target.read_text(encoding="utf-8") == review.render()


def test_cancelling_a_review_export_writes_nothing(review, answers, tmp_path):
    """`tmp_path` is also the project fixture's directory, so look for the
    export specifically rather than asserting the directory is empty."""
    answers["save"] = ""
    before = sorted(p.name for p in tmp_path.iterdir())
    review.export_json()
    review.export_text()
    assert sorted(p.name for p in tmp_path.iterdir()) == before


# ---------------------------------------------------------------------------
# Wiring from the frame
# ---------------------------------------------------------------------------

def test_the_frame_opens_the_rule_editor(frame, tk_root):
    frame.edit_rules()
    tk_root.update_idletasks()
    dialogs = [child for child in frame.rules_tree.winfo_children()
               if isinstance(child, RuleEditorDialog)]
    assert dialogs
    dialogs[0].destroy()


def test_the_frame_opens_the_review_report(frame, tk_root):
    frame.review_report()
    tk_root.update_idletasks()
    dialogs = [child for child in frame.winfo_children()
               if isinstance(child, ReviewReportDialog)]
    assert dialogs
    dialogs[0].destroy()


def test_selecting_a_source_folder_plans_it(tk_root, project, answers):
    answers["save"] = str(project)
    widget = SelectionWorkspaceFrame(tk_root, service=BundleToolService())
    widget.select_source()
    tk_root.update_idletasks()
    assert widget.model is not None
    assert widget.source_var.get() == str(project)
    widget.destroy()


def test_a_planning_failure_is_reported_rather_than_raised(tk_root, answers,
                                                           tmp_path):
    widget = SelectionWorkspaceFrame(tk_root, service=BundleToolService())
    widget.source_var.set(str(tmp_path / "absent"))
    widget.rescan()
    assert widget.model is None
    assert answers["info"], "the failure was not surfaced"
    widget.destroy()


# ---------------------------------------------------------------------------
# The final selection review (§7.2) - three outcomes, not two
# ---------------------------------------------------------------------------

@pytest.fixture
def blocked_frame(tk_root, tmp_path):
    """A tree carrying recursion hazards, so the review has something to say."""
    for index in range(3):
        (tmp_path / f"proj_src_bundle_{index}.txt").write_bytes(b"nested\n")
    (tmp_path / "keep.py").write_bytes(b"x = 1\n")
    widget = SelectionWorkspaceFrame(tk_root, service=BundleToolService())
    widget.source_var.set(str(tmp_path))
    widget.rescan()
    tk_root.update_idletasks()
    yield widget
    widget.destroy()


def test_blocked_paths_raise_a_review(blocked_frame):
    reasons = blocked_frame.model.needs_review()
    assert any("blocked" in reason for reason in reasons)


def test_the_review_says_blocked_paths_will_simply_be_left_out(blocked_frame):
    """The old wording - "Create the bundle anyway?" - implied a risk.

    Blocked paths are held at Priority 0 and were never going into the bundle,
    so there is no "anyway" about it. The review now says what will happen.
    """
    reason = next(r for r in blocked_frame.model.needs_review() if "blocked" in r)
    assert "cannot be included" in reason
    assert "left out" in reason


def test_the_review_dialog_offers_three_outcomes(blocked_frame, tk_root):
    from ui.rule_editor import ReviewSelectionDialog

    dialog = ReviewSelectionDialog(blocked_frame,
                                   blocked_frame.model.needs_review(),
                                   blocked_frame.model.unacknowledged_blocked())
    tk_root.update_idletasks()
    assert hasattr(dialog, "exclude_btn"), "no way to settle the blocked items"
    assert hasattr(dialog, "continue_btn")
    assert hasattr(dialog, "cancel_btn")
    assert dialog.choice == "cancel", "the safe default is not cancel"
    dialog.destroy()


def test_no_exclude_button_when_nothing_is_blocked(frame, tk_root):
    from ui.rule_editor import ReviewSelectionDialog

    dialog = ReviewSelectionDialog(frame, ["1 scan warning"], [])
    tk_root.update_idletasks()
    assert not hasattr(dialog, "exclude_btn")
    dialog.destroy()


def test_excluding_blocked_settles_the_warning(blocked_frame, tk_root):
    """The point of the third button: the same dialog must not return forever."""
    assert blocked_frame.model.needs_review()
    blocked_frame.model.acknowledge_blocked()
    tk_root.update_idletasks()
    assert blocked_frame.model.needs_review() == []


def test_acknowledging_records_the_choice_in_the_report(blocked_frame):
    from ui.rule_editor import render_review

    blocked_frame.model.acknowledge_blocked()
    report = render_review(blocked_frame.model)
    assert "MANUAL OVERRIDES (3)" in report
    assert "proj_src_bundle_0.txt" in report


def test_acknowledging_changes_no_decision(blocked_frame):
    """Blocked stays blocked - an acknowledgement is not an override."""
    before = {d.path: d.state for d in blocked_frame.model.result.plan.decisions}
    blocked_frame.model.acknowledge_blocked()
    after = {d.path: d.state for d in blocked_frame.model.result.plan.decisions}
    assert before == after


def test_acknowledging_twice_is_idempotent(blocked_frame):
    blocked_frame.model.acknowledge_blocked()
    once = blocked_frame.model.overrides
    blocked_frame.model.acknowledge_blocked()
    assert blocked_frame.model.overrides == once


def test_cancelling_the_review_stops_the_bundle(blocked_frame, answers,
                                                 monkeypatch, tmp_path, tk_root):
    monkeypatch.setattr(blocked_frame, "confirm_review", lambda: False)
    answers["save"] = str(tmp_path / "out.txt")
    blocked_frame.create_bundle()
    tk_root.update_idletasks()
    assert not (tmp_path / "out.txt").exists()


def test_continuing_past_the_review_creates_the_bundle(blocked_frame, answers,
                                                        monkeypatch, tmp_path,
                                                        tk_root):
    monkeypatch.setattr(blocked_frame, "confirm_review", lambda: True)
    target = tmp_path / "out.txt"
    answers["save"] = str(target)
    blocked_frame.create_bundle()
    tk_root.update_idletasks()
    assert target.exists()
    assert "proj_src_bundle_0.txt" not in target.read_text(encoding="utf-8")


def test_a_clean_selection_shows_no_review_at_all(frame, monkeypatch):
    """No dialog when there is nothing to say."""
    from ui import rule_editor

    built = []
    monkeypatch.setattr(rule_editor, "ReviewSelectionDialog",
                        lambda *a, **k: built.append(a))
    assert frame.confirm_review() is True
    assert built == []
