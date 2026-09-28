"""Surface producer builds and enough parse-error context for support."""

from core.models import BundleEntry, BundleManifest
from core.profiles.plain_marker import PlainMarkerProfile
from core.version import __version__
from ui.unbundle_frame import UnbundleFrame


def test_opened_build_remains_visible_after_integrity_check(tk_root):
    frame = UnbundleFrame(tk_root)
    try:
        bundle = PlainMarkerProfile().format_manifest(BundleManifest(
            [BundleEntry(path="example.py", content="pass\n")], "plain_marker"))
        frame.load_bundle_text(bundle)
        assert f"Created with BFT {__version__}" in frame.status_label.cget("text")
        assert "ready to extract" in frame.status_label.cget("text")
        assert f"Created with BFT {__version__}" in frame.log_text.get("1.0", "end")
    finally:
        frame.destroy()


def test_failed_open_reports_path_entry_and_size_in_persistent_log(
        tk_root, tmp_path, monkeypatch, capsys):
    import ui.unbundle_frame as module
    target = tmp_path / "damaged.txt"
    text = PlainMarkerProfile().format_manifest(BundleManifest(
        [BundleEntry(path="broken.py", content="abc", file_size_bytes=3)], "plain_marker"))
    target.write_bytes(text.replace("size=3", "size=100").encode())
    dialogs = []
    monkeypatch.setattr(module.filedialog, "askopenfilename", lambda **kw: str(target))
    monkeypatch.setattr(module.messagebox, "showerror", lambda *args, **kw: dialogs.append(args))
    frame = UnbundleFrame(tk_root)
    try:
        frame.open_bundle()
        assert str(target) in dialogs[0][1]
        assert "broken.py" in dialogs[0][1]
        assert "declared 100" in dialogs[0][1]
        assert str(target) in capsys.readouterr().err
        assert frame.current_manifest is None
    finally:
        frame.destroy()
