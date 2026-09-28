"""Real-Tk acceptance coverage for Unbundle contents and scrollability."""

from __future__ import annotations

import base64
import tkinter as tk

from core.models import BundleEntry, BundleManifest
from core.profiles.plain_marker import PlainMarkerProfile
from core.user_state import UserStateStore
from ui.unbundle_frame import UnbundleFrame


def _window_and_frame(tk_root, geometry="700x520"):
    window = tk.Toplevel(tk_root)
    window.geometry(geometry)
    frame = UnbundleFrame(window)
    frame.pack(fill="both", expand=True)
    window.update_idletasks()
    return window, frame


def test_unbundle_displays_recorded_zero_and_infers_legacy_sizes(tk_root):
    window, frame = _window_and_frame(tk_root)
    try:
        frame.current_manifest = BundleManifest(
            entries=[
                BundleEntry(
                    path="empty.txt", content="", file_size_bytes=0),
                BundleEntry(
                    path="legacy.txt", content="café", encoding="utf-8"),
                BundleEntry(
                    path="legacy.bin",
                    content=base64.b64encode(b"1234567").decode("ascii"),
                    is_binary=True,
                    encoding="base64",
                    eol_style="n/a",
                ),
            ],
            profile="plain_marker",
        )

        frame._populate_file_list()

        sizes = {
            frame.file_tree.item(item, "text"):
                frame.file_tree.item(item, "values")[0]
            for item in frame.file_tree.get_children()
        }
        assert sizes == {
            "empty.txt": "0",
            "legacy.txt": "5",
            "legacy.bin": "7",
        }
    finally:
        window.destroy()


def test_every_unbundle_scrollbar_activates_under_real_overflow(tk_root):
    window, frame = _window_and_frame(tk_root, "1000x600")
    try:
        prefix = "deeply_nested_project_folder/" * 12
        frame.current_manifest = BundleManifest(
            entries=[
                BundleEntry(path=f"{prefix}file_{index:03}.txt", content="x")
                for index in range(180)
            ],
            profile="plain_marker",
        )
        frame._populate_file_list()
        for index in range(100):
            frame._log(f"log {index:03}: " + "long diagnostic detail " * 20)
        window.update_idletasks()
        window.update()

        assert frame.file_tree.yview()[1] - frame.file_tree.yview()[0] < 1.0
        assert frame.file_tree.xview()[1] - frame.file_tree.xview()[0] < 1.0
        assert frame.log_text.yview()[1] - frame.log_text.yview()[0] < 1.0
        assert frame.log_text.xview()[1] - frame.log_text.xview()[0] < 1.0

        for scrollbar in (
                frame.file_vscroll, frame.file_hscroll,
                frame.log_vscroll, frame.log_hscroll):
            assert str(scrollbar.cget("command")), "scrollbar has no command"
            assert scrollbar.winfo_manager(), "scrollbar is not laid out"
    finally:
        window.destroy()


def test_open_bundle_remembers_its_folder_across_frames(
    tk_root,
    tmp_path,
    monkeypatch,
):
    import ui.unbundle_frame as module

    bundle_dir = tmp_path / "bundles"
    bundle_dir.mkdir()
    bundle_path = bundle_dir / "sample.txt"
    manifest = BundleManifest(
        entries=[BundleEntry(path="a.txt", content="a\n")],
        profile="plain_marker",
    )
    bundle_path.write_text(
        PlainMarkerProfile().format_manifest(manifest),
        encoding="utf-8",
        newline="",
    )
    state_path = tmp_path / "state" / "user_state.json"
    answers = iter((str(bundle_path), ""))
    calls = []

    def choose(**kwargs):
        calls.append(kwargs)
        return next(answers)

    monkeypatch.setattr(module.filedialog, "askopenfilename", choose)

    first_window = tk.Toplevel(tk_root)
    first = UnbundleFrame(
        first_window,
        user_state=UserStateStore(str(state_path)),
    )
    first.pack(fill="both", expand=True)
    first.open_bundle()
    first_window.destroy()

    second_window = tk.Toplevel(tk_root)
    second = UnbundleFrame(
        second_window,
        user_state=UserStateStore(str(state_path)),
    )
    second.pack(fill="both", expand=True)
    second.open_bundle()
    second_window.destroy()

    assert UserStateStore(str(state_path)).get("last_bundle_open_dir") == str(bundle_dir)
    assert calls[1]["initialdir"] == str(bundle_dir)
