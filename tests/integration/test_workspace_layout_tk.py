"""Live view identity, even layouts, window lifetimes and monitor recovery."""
import tkinter as tk
from tkinter import ttk
from types import SimpleNamespace

import pytest

from core.user_state import UserStateStore
from railgun_display import DisplayInfo, DisplayRect, DisplayTopology
from ui import workspace_layout as module
from ui.workspace_layout import WorkspaceLayout


LEFT = DisplayInfo("left", DisplayRect(-1920, 0, 0, 1080), DisplayRect(-1920, 0, 0, 1040))
RIGHT = DisplayInfo("right", DisplayRect(0, 0, 1920, 1080), DisplayRect(0, 0, 1920, 1040), True)


@pytest.fixture
def layout(tk_root, tmp_path):
    window = tk.Toplevel(tk_root)
    window.geometry("1200x850+20+20")
    driver = SimpleNamespace(topology=lambda: DisplayTopology((LEFT, RIGHT)))
    messages = []
    widget = WorkspaceLayout(window, driver=driver, report=messages.append,
                             user_state=UserStateStore(str(tmp_path / "state.json")))
    widget.pack(fill="both", expand=True)
    widget.messages = messages
    window.update()
    yield widget
    window.destroy()


def choose(layout, *keys, mode="Side by side"):
    for key, var in layout.visible.items():
        var.set(key in keys)
    layout.layout_var.set(mode)
    layout.change_layout()
    layout.update()


@pytest.mark.parametrize("mode", ["Side by side", "Stacked", "Grid"])
def test_two_comparison_views_share_space_evenly_and_resize(layout, mode):
    choose(layout, "selections", "result_set", mode=mode)
    a, b = layout.pages["selections"], layout.pages["result_set"]
    for size in ("1200x850", "1000x700"):
        layout.winfo_toplevel().geometry(size)
        layout.update()
        assert abs(a.winfo_width() - b.winfo_width()) <= 1
        assert abs(a.winfo_height() - b.winfo_height()) <= 1
        if mode == "Stacked":
            assert b.winfo_y() > a.winfo_y()
        else:
            assert b.winfo_x() > a.winfo_x()


def test_show_all_grid_then_single_view_then_tabs(layout):
    layout.show_all()
    layout.update()
    sizes = [(p.winfo_width(), p.winfo_height()) for p in layout.pages.values()]
    assert max(w for w, h in sizes) - min(w for w, h in sizes) <= 1
    assert max(h for w, h in sizes) - min(h for w, h in sizes) <= 1
    assert layout.pages["result_set"].winfo_y() > layout.pages["selections"].winfo_y()
    choose(layout, "rules")
    assert layout.pages["rules"].winfo_width() >= layout.winfo_width() - 10
    layout.layout_var.set("Tabs")
    layout.change_layout()
    assert layout.notebook.tab(layout.pages["rules"], "state") == "normal"
    assert layout.notebook.tab(layout.pages["selections"], "state") == "hidden"
    layout.visible["result_set"].set(True)
    layout.toggle_view("result_set")
    assert layout.notebook.select() == str(layout.pages["result_set"])
    for key in layout.visible:
        layout.visible[key].set(False)
        layout.toggle_view(key)
    layout.update()
    assert layout.empty.winfo_ismapped()


def test_content_and_selection_survive_detach_close_redock_and_layout_changes(layout):
    tree = ttk.Treeview(layout.content["result_set"])
    tree.pack(fill="both", expand=True)
    tree.insert("", "end", iid="keep", text="Keep this selection")
    tree.selection_set("keep")
    choose(layout, "selections", "result_set")
    original = str(tree)
    assert layout.detach("result_set")
    assert layout.detach("result_set")  # Opening it twice must preserve one window.
    page = layout.pages["result_set"]
    assert tree.winfo_toplevel() == page
    tree.item("keep", text="Changed while detached")
    # Closing a separate view returns it, without destroying its children.
    layout.tk.call(page.protocol("WM_DELETE_WINDOW"))
    assert "result_set" not in layout.detached
    assert str(tree) == original and tree.selection() == ("keep",)
    assert tree.item("keep", "text") == "Changed while detached"
    layout.toggle_window("rules")
    layout.toggle_window("guidance")
    layout.toggle_window("rules")
    layout.dock_all()
    layout.dock("rules")
    assert not layout.detached


def test_hidden_or_inactive_separate_views_restore_without_losing_content(layout):
    layout.detach("guidance")
    page = layout.pages["guidance"]
    layout.visible["guidance"].set(False)
    layout.toggle_view("guidance")
    assert page.state() == "withdrawn"
    layout.visible["guidance"].set(True)
    layout.toggle_view("guidance")
    layout.set_active(False)
    assert page.state() == "withdrawn"
    layout.set_active(True)
    assert page.state() == "normal"


def test_monitor_buttons_follow_topology_and_move_relative_to_view(layout, monkeypatch):
    moves = []
    monkeypatch.setattr(layout, "_place", lambda window, display: moves.append((window, display)))
    monkeypatch.setattr(layout, "_rect", lambda window: DisplayRect(100, 100, 700, 600))
    assert layout.move_view("guidance")
    assert moves[-1] == (layout.pages["guidance"], LEFT)
    # A detached view on the left returns right even if the main window stays right.
    monkeypatch.setattr(layout, "_rect", lambda window: DisplayRect(-1000, 100, -400, 600))
    assert layout.move_view("guidance")
    assert moves[-1][1] == RIGHT
    layout.move_workspace()
    assert moves[-1] == (layout.winfo_toplevel(), RIGHT)
    layout.dock_all()
    layout.driver.topology = lambda: DisplayTopology((RIGHT,))
    layout.refresh_displays()
    assert not layout.display_buttons["guidance"].winfo_manager()
    assert not layout.move_workspace_button.winfo_manager()
    assert not layout.move_view("guidance")
    layout.move_workspace()


def test_monitor_disconnect_rescues_separate_hidden_view(layout, monkeypatch):
    layout.detach("guidance")
    layout.set_active(False)
    monkeypatch.setattr(layout, "_rect", lambda window: DisplayRect(-1000, 100, -400, 600))
    moved = []
    monkeypatch.setattr(layout, "_place", lambda window, display: moved.append(display))
    layout.driver.topology = lambda: DisplayTopology((RIGHT,))
    layout.refresh_displays()
    assert moved == [RIGHT]
    assert layout.pages["guidance"].state() == "withdrawn"
    assert "brought back" in layout.messages[-1]


def test_failed_rescue_returns_view_to_workspace(layout, monkeypatch):
    layout.detach("guidance")
    monkeypatch.setattr(layout, "_rect", lambda window: DisplayRect(-1000, 100, -400, 600))
    def fail(*args):
        raise OSError("Monitor removed")
    monkeypatch.setattr(layout, "_place", fail)
    layout.driver.topology = lambda: DisplayTopology((RIGHT,))
    layout.refresh_displays()
    assert "guidance" not in layout.detached


def test_transient_topology_failure_does_not_move_views(layout):
    previous = layout.topology
    def fail():
        raise OSError("Temporary enumeration failure")
    layout.driver.topology = fail
    layout.refresh_displays()
    assert layout.topology == previous


def test_failed_move_keeps_view_available_and_reports_error(layout, monkeypatch):
    def fail(*args):
        raise OSError("Move failed")
    monkeypatch.setattr(layout, "_place", fail)
    assert not layout.move_view("rules")
    assert "rules" in layout.detached
    assert "remains available" in layout.messages[-1]
    layout.move_workspace()
    assert "Could not move the workspace" in layout.messages[-1]
    layout.dock_all()
    monkeypatch.setattr(layout, "detach", lambda key: False)
    assert not layout.move_view("rules")


def test_unsupported_window_manager_leaves_tab_usable(layout, monkeypatch):
    real = layout.tk
    class RefuseManage:
        def call(self, *args):
            if args[:2] == ("wm", "manage"):
                raise tk.TclError("Not supported")
            return real.call(*args)
    monkeypatch.setattr(layout, "tk", RefuseManage())
    assert not layout.detach("selections")
    assert not layout.detached
    assert layout.notebook.tab(layout.pages["selections"], "state") == "normal"
    monkeypatch.setattr(layout, "tk", real)


def test_place_fits_work_area_and_preserves_signed_position(tk_root, monkeypatch):
    window = tk.Toplevel(tk_root)
    try:
        window.geometry("2500x1500")
        window.update()
        moved = []
        monkeypatch.setattr(module, "_move_tk_window", lambda win, x, y: moved.append((x, y)) or True)
        WorkspaceLayout._place(window, LEFT)
        window.update()
        assert moved[-1][0] < 0
        assert window.winfo_width() <= LEFT.work_area.width - 24
        assert window.winfo_height() <= LEFT.work_area.height - 60
        monkeypatch.setattr(module, "_move_tk_window", lambda *args: False)
        with pytest.raises(OSError):
            WorkspaceLayout._place(window, RIGHT)
    finally:
        window.destroy()


def test_layout_preference_survives_reopen_and_invalid_values_fall_back(layout):
    layout.layout_var.set("Stacked")
    layout.change_layout()
    state = UserStateStore(str(layout.user_state.state_file))
    assert state.get("workspace_layout") == "Stacked"
    state.set("workspace_layout", "broken")
    state.set("workspace_show_guidance", "broken")
    replacement = WorkspaceLayout(layout.master, user_state=state, driver=layout.driver)
    try:
        assert replacement.layout_var.get() == "Tabs"
        assert replacement.visible["guidance"].get()
        replacement.layout_var.set("broken")
        replacement.change_layout()
        assert replacement.layout_var.get() == "Tabs"
        replacement.after_cancel(replacement._poll_id)
        replacement._poll_displays()
        assert replacement._poll_id is not None
    finally:
        replacement.destroy()
    assert replacement._poll_id is None


def test_live_workspace_model_updates_detached_result_view(tk_root, tmp_path):
    from ui.selection_workspace import SelectionWorkspaceFrame
    (tmp_path / "keep.py").write_text("pass\n", encoding="utf-8")
    widget = SelectionWorkspaceFrame(tk_root)
    try:
        widget.source_var.set(str(tmp_path))
        widget.rescan()
        model = widget.model
        tree = widget.decision_tree
        widget.workspace_layout.detach("result_set")
        assert tree.exists("keep.py")
        model.set_file("keep.py", False)
        widget.refresh_all()
        assert not tree.exists("keep.py")  # Included remains the active filter.
        widget.workspace_layout.dock("result_set")
        widget.undo()
        assert tree.exists("keep.py")
        assert widget.model is model and widget.decision_tree is tree
    finally:
        widget.destroy()


def test_four_views_leave_result_rows_readable_on_normal_sized_window(tk_root, tmp_path):
    from ui.selection_workspace import SelectionWorkspaceFrame
    (tmp_path / "keep.py").write_text("pass\n", encoding="utf-8")
    window = tk.Toplevel(tk_root)
    window.geometry("1000x720")
    widget = SelectionWorkspaceFrame(window)
    widget.pack(fill="both", expand=True)
    try:
        widget.source_var.set(str(tmp_path))
        widget.rescan()
        widget.workspace_layout.show_all()
        window.update()
        assert widget.decision_tree.bbox("keep.py"), "First result must remain visible"
        assert not widget.show_explanation_var.get()
        widget.explanation_check.invoke()
        window.update()
        assert widget.inspector_text.winfo_ismapped()
        choose(widget.workspace_layout, "selections", "result_set")
        window.update()
        assert widget.show_explanation_var.get()
        assert widget.decision_tree.bbox("keep.py")
        choose(widget.workspace_layout, *widget.workspace_layout.pages, mode="Side by side")
        window.update()
        content = widget.workspace_layout.content["result_set"]
        right_edge = content.winfo_rootx() + content.winfo_width()
        for button in (*widget.view_buttons.values(), widget.hide_blocked_check,
                       widget.include_visible_btn, widget.exclude_visible_btn, widget.clear_btn,
                       widget.expand_btn, widget.collapse_btn):
            assert button.winfo_rootx() + button.winfo_width() <= right_edge
    finally:
        window.destroy()


def test_keyboard_tab_traversal_works_from_live_page_contents(layout):
    choose(layout, "selections", "result_set", "guidance", mode="Tabs")
    entry = ttk.Entry(layout.content["selections"])
    entry.pack()
    layout.notebook.select(layout.pages["selections"])
    entry.focus_force()
    layout.update()
    entry.event_generate("<Control-Tab>")
    layout.update()
    assert layout.notebook.select() == str(layout.pages["result_set"])
    layout.pages["result_set"].event_generate("<Control-Shift-Tab>")
    layout.update()
    assert layout.notebook.select() == str(layout.pages["selections"])
    assert layout._cycle_tab(SimpleNamespace(widget=layout), 1) is None
    layout.layout_var.set("Grid")
    layout.change_layout()
    assert layout._cycle_tab(SimpleNamespace(widget=entry), 1) is None


def test_keyboard_cleanup_preserves_tks_notebook_binding(tk_root):
    window = tk.Toplevel(tk_root)
    try:
        layout = WorkspaceLayout(window)
        own = [command for sequence, command in layout._traversal_bindings]
        layout.destroy()
        script = window.bind("<Control-Tab>")
        assert all(command not in script for command in own)
        # enable_traversal installs Tk's standard notebook handler; keep it.
        assert "TLCycleTab" in script
    finally:
        window.destroy()


def test_compact_result_menu_preserves_actions_and_disabled_states(tk_root, tmp_path, monkeypatch):
    from ui.selection_workspace import SelectionWorkspaceFrame
    from ui import selection_workspace
    window = tk.Toplevel(tk_root)
    window.geometry("1000x600")
    widget = SelectionWorkspaceFrame(window)
    widget.pack(fill="both", expand=True)
    try:
        widget.workspace_layout.show_all()
        window.update()
        assert widget.result_actions_button.winfo_ismapped()
        menu = widget.result_actions_menu
        menu.tk.call(menu.cget("postcommand"))
        assert menu.entrycget(0, "state") == "disabled"
        (tmp_path / "keep.py").write_text("pass\n", encoding="utf-8")
        widget.source_var.set(str(tmp_path))
        widget.rescan()
        window.update()
        assert widget.decision_tree.bbox("keep.py")
        menu.tk.call(menu.cget("postcommand"))
        assert menu.entrycget(1, "state") == "normal"
        monkeypatch.setattr(selection_workspace.messagebox, "askyesno", lambda *a, **k: True)
        menu.invoke(1)
        assert not widget.decision_tree.exists("keep.py")
        menu.tk.call(menu.cget("postcommand"))
        menu.invoke(2)
        assert widget.decision_tree.exists("keep.py")
    finally:
        window.destroy()
