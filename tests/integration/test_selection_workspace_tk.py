# BFT_B115_SELECTION_WORKSPACE_TK_TESTS
# ============================================================================
# SOURCEFILE: test_selection_workspace_tk.py
# RELPATH: bundle_file_tool_v2/tests/integration/test_selection_workspace_tk.py
# PROJECT: Bundle File Tool v2.2
# VERSION: 2.1.115
# LIFECYCLE: Testing
# STATUS: Build 115 - WP4 - BFT_B115_SELECTION_WORKSPACE_TK_TESTS
# ============================================================================
"""The workspace against a real Tk root.

Spec §18.3 is blunt about this: *"No skipped Tk tests are counted as UI
acceptance; the established session-scoped Tk root remains in use."* So these
use the `tk_root` fixture from conftest and fail rather than skip - six Tk tests
silently skipped under coverage was a Build 112 defect, and a skipped
acceptance test is worse than an absent one because it reports green.

What is asserted here is the *binding*: that widgets exist, that they show what
the model says, and that events reach the model. The behaviour itself is
covered headlessly in `test_workspace_model.py`, because a Treeview row can
only tell you a string appeared.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from types import SimpleNamespace

import pytest

from core.service import BundleToolService
from ui.selection_workspace import (
    DECISION_EAGER_LIMIT,
    GLYPH,
    SelectionWorkspaceFrame,
    fit_tree_columns,
)
from ui.workspace_model import (
    DecisionRow,
    VIEW_ALL,
    VIEW_BLOCKED,
    VIEW_EXCLUDED,
    VIEW_INCLUDED,
    TriState,
)


@pytest.fixture
def tree(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_bytes(b"print(1)\n")
    (tmp_path / "src" / "util.py").write_bytes(b"x = 2\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guide.md").write_bytes(b"# guide\n")
    (tmp_path / "notes.log").write_bytes(b"noise\n")
    env = tmp_path / ".venv312"
    (env / "Scripts").mkdir(parents=True)
    (env / "pyvenv.cfg").write_bytes(b"home = C\n")
    (env / "Scripts" / "python.exe").write_bytes(b"MZ")
    (env / "junk.py").write_bytes(b"pass\n")
    return tmp_path


def leaf_paths(tree_widget, parent=""):
    """Every file row in the folded decision tree, depth first.

    The decision pane became a tree in Build 116 - a flat list of 1,100 rows
    was unreadable on a real project - so a test has to descend rather than
    read the top level.
    """
    found = []
    for item in tree_widget.get_children(parent):
        if str(item).startswith("dir::"):
            found.extend(leaf_paths(tree_widget, item))
        else:
            found.append(str(item))
    return found


@pytest.fixture
def frame(tk_root, tree):
    """A workspace already showing a plan for `tree`."""
    widget = SelectionWorkspaceFrame(tk_root, service=BundleToolService())
    widget.source_var.set(str(tree))
    widget.rescan()
    tk_root.update_idletasks()
    yield widget
    widget.destroy()


# ---------------------------------------------------------------------------
# The seven regions exist (§7.1)
# ---------------------------------------------------------------------------

def test_every_specified_region_is_present(frame):
    for attribute in ("source_entry", "preset_box", "rescan_btn", "create_btn",
                      "summary_label", "folder_tree", "rules_tree",
                      "search_entry", "decision_tree", "inspector_text",
                      "override_btn", "report_btn"):
        assert hasattr(frame, attribute), f"missing region: {attribute}"


def test_tab_preferences_survive_reopening_without_changing_plan(tk_root, tmp_path):
    from core.user_state import UserStateStore

    state_path = str(tmp_path / "user_state.json")
    widget = SelectionWorkspaceFrame(tk_root, user_state=UserStateStore(state_path))
    try:
        assert [key for key, var in widget.tab_visibility.items() if var.get()] == [
            "selections", "guidance"]
        widget.tab_buttons["rules"].invoke()
        widget.tab_buttons["selections"].invoke()
        assert widget.notebook.tab(widget.workspace_tabs["rules"], "state") == "normal"
        assert widget.notebook.tab(widget.workspace_tabs["selections"], "state") == "hidden"
    finally:
        widget.destroy()
    reopened = SelectionWorkspaceFrame(tk_root, user_state=UserStateStore(state_path))
    try:
        assert reopened.tab_visibility["rules"].get()
        assert not reopened.tab_visibility["selections"].get()
        for key, var in reopened.tab_visibility.items():
            if var.get():
                reopened.tab_buttons[key].invoke()
        reopened.tab_buttons["selections"].invoke()
        assert reopened.notebook.select() == str(reopened.workspace_tabs["selections"])
    finally:
        reopened.destroy()


def test_source_and_actions_fit_minimum_window(tk_root):
    window = tk.Toplevel(tk_root)
    window.geometry("800x600")
    widget = SelectionWorkspaceFrame(window)
    widget.pack(fill="both", expand=True)
    window.update()
    try:
        assert widget.source_entry.winfo_width() > 600
        assert widget.source_entry.winfo_rooty() < widget.preset_box.winfo_rooty()
        assert (widget.create_btn.winfo_rootx() + widget.create_btn.winfo_width()
                <= window.winfo_rootx() + window.winfo_width())
    finally:
        window.destroy()


def test_the_summary_band_shows_the_plan_counts(frame):
    assert "included" in frame.summary_var.get()
    assert "excluded" in frame.summary_var.get()


def test_the_footer_reports_what_the_tool_did(frame):
    assert "without reading content" in frame.status_var.get()


# ---------------------------------------------------------------------------
# The folder tree
# ---------------------------------------------------------------------------

def test_the_folder_tree_is_populated(frame):
    assert frame.folder_tree.get_children(), "the folder tree is empty"


def test_tri_state_is_drawn_as_text_not_colour(frame):
    """§7.2: colour never carries meaning alone."""
    labels = [frame.folder_tree.item(item, "text")
              for item in frame.folder_tree.get_children()]
    assert any(label.startswith(GLYPH[TriState.CHECKED]) for label in labels)
    assert any(label.startswith(GLYPH[TriState.UNCHECKED]) for label in labels)


def test_the_environment_row_shows_its_reason_and_no_file_count(frame):
    for item in frame.folder_tree.get_children():
        if ".venv312" in frame.folder_tree.item(item, "text"):
            count, badge = frame.folder_tree.item(item, "values")
            assert badge == "Python env"
            assert count == "not enumerated"
            return
    pytest.fail(".venv312 was not listed in the folder tree")


def test_no_file_from_the_pruned_environment_is_listed(frame):
    labels = [frame.folder_tree.item(item, "text")
              for item in frame.folder_tree.get_children()]
    assert not any("junk.py" in label for label in labels)


def test_space_on_a_folder_toggles_it(frame, tk_root):
    item = next(i for i in frame.folder_tree.get_children()
                if frame.folder_tree.item(i, "text").endswith("src"))
    frame.folder_tree.selection_set(item)
    frame._on_space()
    tk_root.update_idletasks()
    assert frame.model.overrides == [("exclude", "src/**")]


def test_a_toggle_redraws_the_glyph(frame, tk_root):
    item = next(i for i in frame.folder_tree.get_children()
                if frame.folder_tree.item(i, "text").endswith("src"))
    frame.folder_tree.selection_set(item)
    frame._on_space()
    tk_root.update_idletasks()
    redrawn = next(frame.folder_tree.item(i, "text")
                   for i in frame.folder_tree.get_children()
                   if frame.folder_tree.item(i, "text").endswith("src"))
    assert redrawn.startswith(GLYPH[TriState.UNCHECKED])


def test_single_click_on_a_folder_row_toggles_it(
        frame, monkeypatch, tk_root):
    """The visible tri-state marker must behave like a checkbox."""
    item = next(i for i in frame.folder_tree.get_children()
                if frame.folder_tree.item(i, "text").endswith("src"))
    monkeypatch.setattr(frame.folder_tree, "identify_row", lambda _y: item)
    monkeypatch.setattr(
        frame.folder_tree, "identify_element",
        lambda _x, _y: "Treeitem.text")

    result = frame._on_folder_click(SimpleNamespace(x=60, y=20))
    tk_root.update_idletasks()

    assert result == "break"
    assert frame.model.overrides == [("exclude", "src/**")]
    redrawn = next(frame.folder_tree.item(i, "text")
                   for i in frame.folder_tree.get_children()
                   if frame.folder_tree.item(i, "text").endswith("src"))
    assert redrawn.startswith(GLYPH[TriState.UNCHECKED])


def test_clicking_the_native_expander_does_not_toggle_selection(
        frame, monkeypatch):
    item = next(i for i in frame.folder_tree.get_children()
                if frame.folder_tree.item(i, "text").endswith("src"))
    monkeypatch.setattr(frame.folder_tree, "identify_row", lambda _y: item)
    monkeypatch.setattr(
        frame.folder_tree, "identify_element",
        lambda _x, _y: "Treeitem.indicator")

    result = frame._on_folder_click(SimpleNamespace(x=10, y=20))

    assert result is None
    assert frame.model.overrides == []


def test_native_expander_lazily_renders_nested_children(frame, tk_root):
    tree = frame.folder_tree
    src_item = next(
        item
        for item in tree.get_children()
        if tree.item(item, "text").endswith("src")
    )
    assert tree.get_children(src_item), "src has no placeholder expander child"

    tree.focus(src_item)
    tree.selection_set(src_item)
    tree.item(src_item, open=True)
    tree.event_generate("<<TreeviewOpen>>")
    tk_root.update()

    src_item = next(
        item for item, path in frame._tree_rows.items() if path == "src"
    )
    children = {
        frame.folder_tree.item(item, "text").rsplit(" ", 1)[-1]
        for item in frame.folder_tree.get_children(src_item)
    }
    assert {"app.py", "util.py"}.issubset(children)
    assert frame.model.overrides == []


def test_selecting_a_folder_no_longer_expands_or_collapses_it(frame):
    item = next(i for i in frame.folder_tree.get_children()
                if frame.folder_tree.item(i, "text").endswith("src"))
    frame.folder_tree.selection_set(item)
    frame._expanded.clear()

    frame._on_folder_select()

    assert "src" not in frame._expanded


# ---------------------------------------------------------------------------
# The decision list
# ---------------------------------------------------------------------------

def test_the_decision_list_shows_every_path(frame):
    frame.view_var.set(VIEW_ALL)
    frame.refresh_decisions()
    assert (len(leaf_paths(frame.decision_tree))
            == len(frame.model.result.plan.decisions))


def test_the_decision_list_folds_files_under_their_folders(frame):
    """A flat list of a thousand rows is unusable; folders collapse it."""
    top = [str(i) for i in frame.decision_tree.get_children()]
    assert any(i.startswith("dir::") for i in top), "nothing was folded"
    assert "src/app.py" not in top, "a nested file appeared at the top level"
    assert "src/app.py" in leaf_paths(frame.decision_tree)


def test_folders_start_collapsed(frame):
    """The pane must open on a handful of rows, not the whole project."""
    folders = [i for i in frame.decision_tree.get_children()
               if str(i).startswith("dir::")]
    assert folders
    assert all(not frame.decision_tree.item(i, "open") for i in folders)


def test_expand_and_collapse_all_work(frame, tk_root):
    frame.expand_decisions()
    tk_root.update_idletasks()
    folders = [i for i in frame.decision_tree.get_children()
               if str(i).startswith("dir::")]
    assert all(frame.decision_tree.item(i, "open") for i in folders)
    frame.collapse_decisions()
    tk_root.update_idletasks()
    assert all(not frame.decision_tree.item(i, "open") for i in folders)


def test_each_decision_row_carries_state_and_reason(frame):
    for item in leaf_paths(frame.decision_tree):
        state, reason = frame.decision_tree.item(item, "values")
        assert state and reason


def test_the_view_filter_narrows_the_list(frame, tk_root):
    frame.view_var.set(VIEW_INCLUDED)
    frame.refresh_decisions()
    tk_root.update_idletasks()
    assert len(leaf_paths(frame.decision_tree)) == \
        frame.model.counts_for_views()[VIEW_INCLUDED]


def test_search_narrows_the_list(frame, tk_root):
    frame.search_var.set("util")
    tk_root.update_idletasks()
    assert leaf_paths(frame.decision_tree) == ["src/util.py"]


def test_a_search_expands_so_matches_are_visible(frame, tk_root):
    """A match hidden inside a collapsed folder would look like no match."""
    frame.search_var.set("util")
    tk_root.update_idletasks()
    folders = [i for i in frame.decision_tree.get_children()
               if str(i).startswith("dir::")]
    assert folders and all(frame.decision_tree.item(i, "open") for i in folders)


def test_the_scope_label_states_what_a_bulk_action_would_affect(frame, tk_root):
    frame.search_var.set("util")
    tk_root.update_idletasks()
    assert frame.scope_var.get() == "1 visible file"


# ---------------------------------------------------------------------------
# The inspector
# ---------------------------------------------------------------------------

def test_selecting_a_row_explains_it(frame, tk_root):
    frame.view_var.set(VIEW_EXCLUDED)
    frame.refresh_decisions()
    frame.decision_tree.selection_set("notes.log")
    frame._on_decision_select()
    tk_root.update_idletasks()
    assert frame.inspector_path.cget("text") == "notes.log"
    assert frame.inspector_text.cget("text")


def test_the_override_button_is_offered_for_an_ordinary_exclusion(frame):
    frame.view_var.set(VIEW_EXCLUDED)
    frame.refresh_decisions()
    frame.decision_tree.selection_set("notes.log")
    frame._on_decision_select()
    assert str(frame.override_btn.cget("state")) == "normal"


def test_a_blocked_path_disables_the_override_button(tk_root, tmp_path):
    (tmp_path / "old_src_bundle.txt").write_bytes(b"nested\n")
    (tmp_path / "keep.py").write_bytes(b"x\n")
    widget = SelectionWorkspaceFrame(tk_root, service=BundleToolService())
    widget.source_var.set(str(tmp_path))
    widget.rescan()
    widget.view_var.set(VIEW_BLOCKED)
    widget.refresh_decisions()
    widget.decision_tree.selection_set("old_src_bundle.txt")
    widget._on_decision_select()
    tk_root.update_idletasks()
    assert str(widget.override_btn.cget("state")) == "disabled"
    widget.destroy()


def test_the_environment_folder_explains_itself_when_selected(frame, tk_root):
    frame.show_inspector(".venv312")
    tk_root.update_idletasks()
    assert "Python env" in frame.inspector_text.cget("text")
    assert "never enumerated" in frame.inspector_text.cget("text")


# ---------------------------------------------------------------------------
# Rules panel
# ---------------------------------------------------------------------------

def test_the_rules_panel_lists_the_active_ladder(frame):
    assert frame.rules_tree.get_children()


def test_governed_rules_are_shown_locked(frame):
    labels = [frame.rules_tree.item(i, "text")
              for i in frame.rules_tree.get_children()]
    assert any("locked" in label for label in labels)


# ---------------------------------------------------------------------------
# Keyboard and lifecycle
# ---------------------------------------------------------------------------

def test_undo_and_redo_are_wired_to_the_override_history(frame, tk_root):
    frame.model.set_folder("src", include=False)
    frame.refresh_all()
    frame.undo()
    tk_root.update_idletasks()
    assert frame.model.overrides == []
    frame.redo()
    tk_root.update_idletasks()
    assert frame.model.overrides == [("exclude", "src/**")]


def test_controls_are_disabled_until_a_source_is_planned(tk_root):
    widget = SelectionWorkspaceFrame(tk_root, service=BundleToolService())
    assert str(widget.create_btn.cget("state")) == "disabled"
    assert str(widget.report_btn.cget("state")) == "disabled"
    widget.destroy()


def test_changing_the_preset_replans_in_place(frame, tk_root):
    frame.preset_var.set("logs")
    frame.apply_preset()
    tk_root.update_idletasks()
    assert "notes.log" not in frame.model.result.plan.ordered_paths()
    assert frame.model.result.plan.generation > 1


def test_an_empty_source_rescan_is_a_no_op(tk_root):
    widget = SelectionWorkspaceFrame(tk_root, service=BundleToolService())
    widget.source_var.set("")
    widget.rescan()
    assert widget.model is None
    widget.destroy()


def test_the_workspace_builds_without_a_config_manager(tk_root):
    """It must not require the governed config to exist to render."""
    widget = SelectionWorkspaceFrame(tk_root)
    assert widget.model is None
    widget.destroy()


# ---------------------------------------------------------------------------
# BFT_B115_WORKSPACE_PROGRESS - the bar and the Cancel button must not drift
# ---------------------------------------------------------------------------

def test_the_workspace_runs_long_operations_behind_the_progress_dialog():
    """A register, so a new bundle-mode surface cannot silently drop progress.

    The first draft of this workspace had *no* reference to `run_with_progress`
    at all. Scanning a 4,000-file tree would have frozen the window with no bar
    and no way to stop - quietly undoing Builds 107 through 112 on the surface
    that had just become the default. Ringo spotted it by asking.

    The service-level guard in `test_progress_monotonic_contract.py` cannot
    catch this: the facade dutifully accepts a `progress` sink, and the UI
    simply never passed one.
    """
    import ast
    import pathlib

    source = pathlib.Path("src/ui/selection_workspace.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    long_operations = {"rescan", "apply_preset", "create_bundle"}
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name not in long_operations:
            continue
        called = {ast.unparse(call.func) for call in ast.walk(node)
                  if isinstance(call, ast.Call)}
        assert "run_with_progress" in called, (
            f"{node.name}() does not run behind the progress dialog")
        long_operations.discard(node.name)
    assert not long_operations, f"never found: {sorted(long_operations)}"


def test_both_long_operations_offer_cancellation():
    import pathlib

    source = pathlib.Path("src/ui/selection_workspace.py").read_text(encoding="utf-8")
    assert source.count("allow_cancel=True") >= 2
    assert "except OperationCancelled" in source


def test_a_cancelled_scan_leaves_the_previous_plan_untouched(frame, tk_root,
                                                             monkeypatch):
    """Build 112's rule: a cancelled run is an outcome, not a failure."""
    import ui.selection_workspace as module
    from core.cancellation import OperationCancelled

    before = frame.model.result

    def cancelled(*args, **kwargs):
        raise OperationCancelled(operation="bundle", phase="discover",
                                 completed=3, total=None)

    monkeypatch.setattr(module, "run_with_progress", cancelled)
    frame.rescan()
    tk_root.update_idletasks()

    assert frame.model.result is before, "a cancelled scan replaced the plan"
    assert "cancelled" in frame.status_var.get().lower()
    assert "error" not in frame.status_var.get().lower()


def test_a_cancelled_preset_leaves_the_previous_plan_untouched(
        frame, tk_root, monkeypatch):
    import ui.selection_workspace as module
    from core.cancellation import OperationCancelled

    before = frame.model.result
    frame.preset_var.set("logs")

    def cancelled(*args, **kwargs):
        raise OperationCancelled(operation="bundle", phase="plan",
                                 completed=256, total=4_000)

    monkeypatch.setattr(module, "run_with_progress", cancelled)
    # Force the progress path even though this fixture intentionally stays tiny.
    monkeypatch.setattr(frame, "_progress_enabled", lambda _count=None: True)
    frame.apply_preset()
    tk_root.update_idletasks()

    assert frame.model.result is before
    assert frame.preset_var.get() == "(none)"
    assert "cancelled" in frame.status_var.get().lower()


def test_a_cancelled_bundle_reports_what_was_written(frame, tk_root,
                                                     monkeypatch, tmp_path):
    import ui.selection_workspace as module
    from core.cancellation import OperationCancelled

    def cancelled(*args, **kwargs):
        error = OperationCancelled(operation="bundle", phase="read",
                                   completed=2, total=4)
        error.partial_paths = ["a.py", "b.py"]
        raise error

    monkeypatch.setattr(module, "run_with_progress", cancelled)
    monkeypatch.setattr(module.filedialog, "asksaveasfilename",
                        lambda **k: str(tmp_path / "out.txt"))
    # This assertion is specifically about cancellation after creation starts;
    # Build 125's automatic selection check is covered independently.
    monkeypatch.setattr(frame, "_ensure_selection_checked", lambda: True)
    frame.create_bundle()
    tk_root.update_idletasks()

    status = frame.status_var.get()
    assert "cancelled" in status.lower()
    assert "2 of 4" in status
    assert not (tmp_path / "out.txt").exists()


def test_small_work_stays_inline_below_the_threshold(frame):
    """BFT_B108_PROGRESS_THRESHOLD: no modal dialog for eleven files."""
    class Config:
        @staticmethod
        def get(key, default=None):
            return {"ui.progress.enabled": True,
                    "ui.progress.min_files": 200}.get(key, default)

    frame.config_manager = Config()
    assert frame._progress_enabled(11) is False
    assert frame._progress_enabled(4000) is True
    assert frame._progress_enabled(None) is True, "a scan cannot know its size"


def test_progress_can_be_switched_off_entirely(frame):
    class Config:
        @staticmethod
        def get(key, default=None):
            return False if key == "ui.progress.enabled" else default

    frame.config_manager = Config()
    assert frame._progress_enabled(4000) is False


# ---------------------------------------------------------------------------
# BFT_B116_PANEL_SCROLLBARS - every pane must be reachable
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("pane", ["folder_tree", "rules_tree", "decision_tree"])
def test_every_pane_has_both_scroll_bars(frame, pane):
    """Build 115 shipped all three panes without them.

    On a 1,100-file project that is not cosmetic: rows below the fold are
    unreachable and long paths run off the right edge with no way to read the
    end of them.
    """
    widget = getattr(frame, pane)
    assert hasattr(widget, "scroll_y"), f"{pane} has no vertical scroll bar"
    assert hasattr(widget, "scroll_x"), f"{pane} has no horizontal scroll bar"


@pytest.mark.parametrize("pane", ["folder_tree", "rules_tree", "decision_tree"])
def test_the_scroll_bars_are_wired_to_their_tree(frame, pane):
    """A scroll bar that is present but not connected is worse than none."""
    widget = getattr(frame, pane)
    assert str(widget.cget("yscrollcommand")), f"{pane} does not drive its bar"
    assert str(widget.cget("xscrollcommand")), f"{pane} does not drive its bar"
    assert widget.scroll_y.winfo_manager(), "the vertical bar is not laid out"
    assert widget.scroll_x.winfo_manager(), "the horizontal bar is not laid out"


def test_the_panes_still_expand_with_the_window(frame):
    """Wrapping a tree in a holder must not cost it its weight."""
    for pane in ("folder_tree", "rules_tree", "decision_tree"):
        holder = getattr(frame, pane).holder
        assert holder.grid_info(), f"{pane} holder is not gridded"


def test_long_workspace_content_activates_every_horizontal_view(
    tk_root,
    tmp_path,
):
    import tkinter as tk

    root = tmp_path / ("very_long_workspace_folder_" + "x" * 100)
    root.mkdir()
    source = root / ("very_long_source_filename_" + "y" * 100 + ".txt")
    source.write_bytes(b"content\n")

    window = tk.Toplevel(tk_root)
    window.geometry("700x520")
    widget = SelectionWorkspaceFrame(window, service=BundleToolService())
    widget.pack(fill="both", expand=True)
    widget.source_var.set(str(tmp_path))
    widget.rescan()
    relative = source.relative_to(tmp_path).as_posix()
    widget.model.set_file(relative, include=False)
    widget.view_var.set(VIEW_ALL)
    widget.list_rule_matches_var.set(False)
    widget.refresh_all()
    window.update()

    try:
        for key, pane in (("selections", widget.folder_tree),
                          ("rules", widget.rules_tree),
                          ("result_set", widget.decision_tree)):
            widget.tab_visibility[key].set(True)
            widget._toggle_workspace_tab(key)
            window.update()
            assert pane.xview()[1] - pane.xview()[0] < 1.0
            before = pane.xview()[0]
            pane.xview_moveto(1.0)
            window.update()
            assert pane.xview()[0] > before
    finally:
        window.destroy()


# ---------------------------------------------------------------------------
# BFT_B119_LARGE_PLAN_RENDERING - Tk work is bounded by the viewport
# ---------------------------------------------------------------------------

def test_large_decision_plans_materialize_branches_on_demand(tk_root):
    """4,000 collapsed files must not become 4,000 synchronous Tcl items."""

    rows = [
        DecisionRow(
            path=f"src/pkg{index // 100:02d}/module_{index % 100:03d}.py",
            state="Included",
            included=True,
            rule_label="base action",
            layer="",
            group="",
            reason="base action (include)",
        )
        for index in range(4_000)
    ]

    class LargeModel:
        @staticmethod
        def rows(view="all", search="", limit=0, hide_blocked=False):
            del view, hide_blocked
            selected = [row for row in rows if search.lower() in row.path.lower()]
            return selected[:limit] if limit else selected

        @staticmethod
        def counts_for_views():
            return {VIEW_BLOCKED: 0}

    widget = SelectionWorkspaceFrame(tk_root, service=BundleToolService())
    widget.model = LargeModel()
    widget.refresh_decisions()

    try:
        assert len(rows) > DECISION_EAGER_LIMIT
        assert widget._decision_lazy is True
        assert list(widget.decision_tree.get_children()) == ["dir::src"]
        assert widget.decision_tree.get_children("dir::src") == ("lazy::src",)

        widget.decision_tree.focus("dir::src")
        widget._on_decision_open()
        packages = widget.decision_tree.get_children("dir::src")
        assert len(packages) == 40
        assert all(str(item).startswith("dir::src/pkg") for item in packages)

        widget.decision_tree.focus("dir::src/pkg00")
        widget._on_decision_open()
        assert len(widget.decision_tree.get_children("dir::src/pkg00")) == 100
        assert "folders load on demand" in widget.scope_var.get()
    finally:
        widget.destroy()


def test_column_fitting_measures_only_a_fixed_sample(tk_root, monkeypatch):
    """Regression for Build 118's one Tcl font call per cell per refresh."""

    tree = ttk.Treeview(tk_root, columns=("state",), show="tree headings")
    tree.heading("#0", text="Path")
    tree.heading("state", text="State")
    for index in range(2_000):
        tree.insert("", "end", text=f"module_{index:04d}.py", values=("Included",))

    measured = []

    class Font:
        @staticmethod
        def measure(value):
            measured.append(str(value))
            return len(str(value)) * 8

    monkeypatch.setattr(
        "ui.selection_workspace.tkfont.nametofont", lambda _name: Font())
    fit_tree_columns(tree, sample_limit=32, value_hints={"#0": "long-name.py"})

    # Two headings, one hint and at most 32 samples for each of two columns.
    assert len(measured) <= 67
    tree.destroy()


# ---------------------------------------------------------------------------
# BFT_B116_HIDE_BLOCKED - blocked paths are not actionable
# ---------------------------------------------------------------------------

@pytest.fixture
def noisy(tk_root, tmp_path):
    """A project where blocked paths outnumber the real ones."""
    (tmp_path / "keep.py").write_bytes(b"x = 1\n")
    for index in range(12):
        (tmp_path / f"old_src_bundle_{index}.txt").write_bytes(b"nested\n")
    widget = SelectionWorkspaceFrame(tk_root, service=BundleToolService())
    widget.source_var.set(str(tmp_path))
    widget.rescan()
    tk_root.update_idletasks()
    yield widget
    widget.destroy()


def test_hide_blocked_is_offered(noisy):
    assert hasattr(noisy, "hide_blocked_check")
    assert noisy.hide_blocked_var.get() is False, "hiding must not be the default"


def test_hiding_blocked_removes_them_from_the_list(noisy, tk_root):
    noisy.view_var.set(VIEW_ALL)
    noisy.refresh_decisions()
    before = len(leaf_paths(noisy.decision_tree))
    noisy.hide_blocked_var.set(True)
    noisy.refresh_decisions()
    tk_root.update_idletasks()
    after = leaf_paths(noisy.decision_tree)
    assert len(after) < before
    assert not any("old_src_bundle" in path for path in after)
    assert "keep.py" in after


def test_included_is_the_initial_result_filter(frame):
    assert frame.view_var.get() == VIEW_INCLUDED
    assert len(leaf_paths(frame.decision_tree)) == frame.model.counts_for_views()[VIEW_INCLUDED]
    assert 'notes.log' not in leaf_paths(frame.decision_tree)


def test_rule_matches_are_individual_readable_rows_and_can_be_compact(frame):
    assert frame.list_rule_matches_var.get()
    for item, rule in zip(frame.rules_tree.get_children(), frame.model.rules_in_effect()):
        children = frame.rules_tree.get_children(item)
        assert [frame.rules_tree.item(child, 'values')[0] for child in children] == list(rule.patterns)
        assert frame.rules_tree.item(item, 'open')
    frame.list_rule_matches_check.invoke()
    for item, rule in zip(frame.rules_tree.get_children(), frame.model.rules_in_effect()):
        assert not frame.rules_tree.get_children(item)
        assert frame.rules_tree.item(item, 'values')[0] == rule.pattern_text


def test_the_counts_still_report_hidden_blocked_paths(noisy, tk_root):
    """Hiding is a view filter. Pretending they are gone would be dishonest."""
    noisy.hide_blocked_var.set(True)
    noisy.refresh_decisions()
    tk_root.update_idletasks()
    assert noisy.model.counts_for_views()[VIEW_BLOCKED] == 12
    assert "12 blocked hidden" in noisy.scope_var.get()


def test_the_blocked_view_still_shows_them_while_hiding(noisy, tk_root):
    """Asking for blocked explicitly must override the hide."""
    noisy.hide_blocked_var.set(True)
    noisy.view_var.set(VIEW_BLOCKED)
    noisy.refresh_decisions()
    tk_root.update_idletasks()
    assert len(leaf_paths(noisy.decision_tree)) == 12
