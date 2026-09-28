"""Exercise the real X11 chooser, including the dialogs that precede it.

Windows and macOS use OS-owned panels, which need native host acceptance.
X11's chooser is a Tk window, so its actual entry and buttons can be driven
without replacing asksaveasfilename or returning a fabricated filename.
"""

from __future__ import annotations

import time
import tkinter as tk

import pytest

from core.config import ConfigManager
from core.service import BundleToolService
from core.user_state import UserStateStore
from ui.rule_editor import ReviewSelectionDialog
from ui.selection_workspace import SelectionWorkspaceFrame


@pytest.mark.parametrize("count,review,cancel,aliases", [
    (1, False, False, False), (466, False, False, False),
    (3, True, False, False), (1, False, True, False),
    (466, False, False, True),
])
def test_create_uses_real_linux_save_dialog(
        tk_root, tmp_path, count, review, cancel, aliases):
    if tk_root.tk.call("tk", "windowingsystem") != "x11":
        pytest.skip("Real OS-owned save panels require native host acceptance")

    source = tmp_path / "source"
    source.mkdir()
    for index in range(count):
        (source / f"file_{index}.py").write_bytes(b"value = 1\n" * 10)
    if aliases:
        (source / "file_alias.py").symlink_to("file_0.py")
    if review:
        (source / "old_src_bundle.txt").write_bytes(b"previous bundle\n")
    destination = tmp_path / "destination"
    destination.mkdir()
    target = destination / "chosen bundle.txt"
    state = UserStateStore(str(tmp_path / "user_state.json"))
    state.set_and_save("last_bundle_save_dir", str(destination))
    config = ConfigManager()
    owner = tk.Toplevel(tk_root)
    owner.geometry("1000x700")
    frame = SelectionWorkspaceFrame(
        owner, service=BundleToolService(config), config_manager=config,
        user_state=state)
    frame.pack(fill="both", expand=True)
    owner.update()
    frame.source_var.set(str(source))
    frame.rescan()
    observed, failures = [], []
    deadline = time.monotonic() + 20
    timer = None
    chooser = f"{owner}.__tk_filedialog"

    def answer():
        nonlocal timer
        timer = None
        try:
            for widget in frame.winfo_children():
                if isinstance(widget, ReviewSelectionDialog):
                    assert widget.winfo_viewable()
                    observed.append("review")
                    widget.continue_btn.invoke()
            if (owner.tk.call("winfo", "exists", chooser)
                    and owner.tk.call("winfo", "ismapped", chooser)):
                observed.append("save")
                if cancel:
                    owner.tk.call(chooser + ".contents.f2.cancel", "invoke")
                else:
                    entry = chooser + ".contents.f2.ent"
                    owner.tk.call(entry, "delete", 0, "end")
                    owner.tk.call(entry, "insert", 0, str(target))
                    owner.tk.call(chooser + ".contents.f2.ok", "invoke")
                return
            if time.monotonic() >= deadline:
                raise TimeoutError("Create Bundle did not present a usable chooser")
            timer = owner.after(50, answer)
        except Exception as error:
            failures.append(error)
            # Break a modal wait so a failed check cannot hang the test runner.
            if owner.tk.call("winfo", "exists", chooser):
                owner.tk.call("::tk::dialog::file::CancelCmd", chooser)
            for widget in frame.winfo_children():
                if isinstance(widget, ReviewSelectionDialog):
                    widget.cancel_btn.invoke()

    try:
        timer = owner.after(50, answer)
        frame.create_bundle()
        assert not failures, failures
        assert observed == (["review", "save"] if review else ["save"])
        assert frame.check_result.valid
        assert target.exists() is not cancel
        assert not owner.grab_current()
        if not cancel:
            checked = frame.service.check_bundle(target)
            assert checked.valid
            assert checked.file_count == count + int(aliases)
            assert "output verified" in frame.status_var.get()
        else:
            assert not list(destination.iterdir())
            assert UserStateStore(str(state.state_file)).get(
                "last_bundle_save_dir") == str(destination)
    finally:
        if timer:
            owner.after_cancel(timer)
        owner.destroy()
