"""Real-Tk acceptance for Build 125 integrity controls and dialogs."""

from __future__ import annotations

import tkinter as tk

from core.checking import CheckFinding, CheckResult
from core.models import BundleEntry, BundleManifest
from core.service import BundleToolService
from core.user_state import UserStateStore
from ui.check_preferences import CheckPreferencesDialog
from ui.check_results import CheckResultsDialog, check_result_text
from ui.selection_workspace import SelectionWorkspaceFrame
from ui.unbundle_frame import UnbundleFrame


def _blocked_result():
    return CheckResult(
        subject="selection",
        label="sample",
        valid=False,
        profile="plain_marker",
        file_count=2,
        findings=(CheckFinding(
            code="NESTED_BUNDLE_CONTENT",
            severity="error",
            summary="Confirmed nested bundle artifact",
            path="demo.txt",
            detail="The file opens as a bundle.",
            remediation="Exclude this path.",
            blocking=True,
        ),),
        generation=1,
    )


def test_check_results_are_actionable_and_copyable(tk_root):
    excluded = []
    dialog = CheckResultsDialog(
        tk_root, _blocked_result(), on_exclude=excluded.extend)
    tk_root.update_idletasks()
    try:
        assert len(dialog.tree.get_children()) == 1
        dialog.tree.selection_set("0")
        dialog._show_selected()
        assert "Suggested action" in dialog.detail_var.get()
        dialog._copy()
        assert "NESTED_BUNDLE_CONTENT" in dialog.clipboard_get()
        assert "Status: BLOCKED" in check_result_text(dialog.result)
        dialog._exclude(["demo.txt"])
        assert excluded == ["demo.txt"]
    finally:
        if dialog.winfo_exists():
            dialog.destroy()


def test_passing_check_dialog_has_no_remediation_button(tk_root):
    result = CheckResult(
        subject="bundle", label="clean", valid=True,
        profile="plain_marker", file_count=0)
    dialog = CheckResultsDialog(tk_root, result)
    tk_root.update_idletasks()
    try:
        assert dialog.tree.get_children() == ()
        assert dialog.detail_var.get() == "No findings."
    finally:
        dialog.destroy()


def test_check_preferences_persist_outside_governed_config(tk_root, tmp_path):
    state_path = tmp_path / "state" / "user_state.json"
    store = UserStateStore(str(state_path))
    dialog = CheckPreferencesDialog(tk_root, store)
    tk_root.update_idletasks()
    dialog.variables["check_bundle_on_load"].set(False)
    dialog.variables["verify_output_after_create"].set(False)
    dialog._save()

    reloaded = UserStateStore(str(state_path))
    assert reloaded.get("check_bundle_on_load") is False
    assert reloaded.get("verify_output_after_create") is False
    assert dialog.saved is True


def test_selection_check_is_visible_and_becomes_stale_after_edit(
        tk_root, tmp_path):
    (tmp_path / "a.txt").write_text("hello\n", encoding="utf-8")
    window = tk.Toplevel(tk_root)
    frame = SelectionWorkspaceFrame(window, service=BundleToolService())
    frame.pack(fill="both", expand=True)
    frame.source_var.set(str(tmp_path))
    try:
        frame.rescan()
        assert str(frame.check_btn.cget("state")) == "normal"
        assert frame.check_selection(show_results=False) is True
        assert "passed" in frame.check_status_var.get().lower()

        frame.model.set_file("a.txt", False)
        frame.refresh_all()
        assert frame.check_result is None
        assert "stale" in frame.check_status_var.get().lower()
    finally:
        window.destroy()


def test_unbundle_check_controls_extraction_state(tk_root):
    window = tk.Toplevel(tk_root)
    frame = UnbundleFrame(window, service=BundleToolService())
    frame.pack(fill="both", expand=True)
    try:
        frame.current_manifest = BundleManifest(
            entries=[BundleEntry(path="a.txt", content="a")],
            profile="plain_marker",
        )
        frame._accept_manifest("memory")
        assert frame.check_current_bundle(show_results=False) is True
        assert str(frame.extract_btn.cget("state")) == "normal"
        assert "ready to extract" in str(frame.status_label.cget("text"))

        frame.current_manifest = BundleManifest(
            entries=[BundleEntry(path="old_bundle.txt", content="payload")],
            profile="plain_marker",
        )
        frame.current_check = None
        frame._accept_manifest("blocked memory")
        assert frame.check_current_bundle(show_results=False) is False
        assert str(frame.extract_btn.cget("state")) == "disabled"
        assert "BLOCKED" in str(frame.status_label.cget("text"))
    finally:
        window.destroy()
