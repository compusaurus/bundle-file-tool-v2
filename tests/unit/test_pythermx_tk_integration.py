# BFT_B108_PYTHERMX_TK_INTEGRATION_TESTS
# ============================================================================
# SOURCEFILE: test_pythermx_tk_integration.py
# RELPATH: bundle_file_tool_v2/tests/unit/test_pythermx_tk_integration.py
# PROJECT: Bundle File Tool v2.1
# VERSION: 2.1.108
# LIFECYCLE: Testing
# STATUS: Build 108 - BFT_B108_PYTHERMX_TK_INTEGRATION_TESTS
# ============================================================================
"""PyThermX as Bundle File Tool's Tkinter progress renderer.

The second half of Paul's Build 104 ruling: one event stream, two adapters.
Build 107 drew it on the CLI; this build draws it in the GUI.

The properties that matter here are different from the CLI's, because the
hazards are different:

1. **The work must leave the UI thread.** The original complaint was not a
   missing widget, it was a frozen window. A bar painted on a blocked event
   loop would show one frame and lie.
2. **The worker must never touch Tk or the model.** `ThermometerCore` is
   deliberately not thread-safe. Only immutable values may cross the channel.
3. **Exceptions must survive the thread boundary.** The call sites are wrapped
   in `try/except` that shows the user a message box; if a worker exception
   were swallowed, a failed operation would look like a successful one.
4. **Small work stays inline.** A modal dialog for eleven files is worse than
   no dialog.
"""

from __future__ import annotations

import ast
import threading
from pathlib import Path

import pytest

pytest.importorskip("pythermx")
pytest.importorskip("tkinter")

from pythermx.tk import PhaseSpec  # noqa: E402

import ui.tk_progress as tk_progress  # noqa: E402
from core.progress import (  # noqa: E402
    OP_BUNDLE,
    OP_EXTRACT,
    PHASE_COMPLETE,
    PHASE_DISCOVER,
    PHASE_READ,
    PHASE_WRITE,
    OperationProgress,
)
from ui.tk_progress import TkProgressReporter, run_with_progress  # noqa: E402

SRC = Path(__file__).resolve().parents[2] / "src"


class RecordingChannel:
    """Stands in for TkThermometerChannel, recording what the worker posts.

    Using a double rather than the real channel is deliberate: these tests are
    about what the *adapter* decides to post, and a real channel would require a
    live widget and pump to observe the same thing indirectly.
    """

    def __init__(self, accept: bool = True) -> None:
        self.calls: list = []
        self._accept = accept

    def _record(self, name, *args, **kwargs):
        self.calls.append((name, args, kwargs))
        return self._accept

    def post_begin(self, spec):
        assert isinstance(spec, PhaseSpec), "a live model must not cross the channel"
        return self._record("begin", spec)

    def post_update(self, value):
        return self._record("update", value)

    def post_increment(self, delta=1.0):
        return self._record("increment", delta)

    def post_promote(self, total, *, current=0.0, phase=None):
        return self._record("promote", total, current=current, phase=phase)

    def post_message(self, text):
        return self._record("message", text)

    def kinds(self):
        return [name for name, _, _ in self.calls]


# ---------------------------------------------------------------------------
# 1. The adapter's posting decisions
# ---------------------------------------------------------------------------

def test_a_new_phase_posts_begin_with_a_phasespec():
    channel = RecordingChannel()
    reporter = TkProgressReporter(channel)

    reporter(OperationProgress(operation=OP_BUNDLE, phase=PHASE_DISCOVER,
                               current=0, total=None, unit="files",
                               message="Scanning"))

    assert channel.kinds() == ["begin", "message"]
    spec = channel.calls[0][1][0]
    assert spec.total is None
    assert spec.phase == PHASE_DISCOVER
    assert spec.unit == "files"
    assert spec.label == "Discovering", "phase labels are shared with the CLI"


def test_discovery_promotes_in_place_exactly_once():
    """The same handoff the CLI performs, expressed as channel commands."""
    channel = RecordingChannel()
    reporter = TkProgressReporter(channel)

    reporter(OperationProgress(operation=OP_BUNDLE, phase=PHASE_DISCOVER,
                               current=0, total=None, unit="files"))
    for count in (1, 2, 3):
        reporter(OperationProgress(operation=OP_BUNDLE, phase=PHASE_DISCOVER,
                                   current=count, total=None, unit="files"))
    reporter(OperationProgress(operation=OP_BUNDLE, phase=PHASE_DISCOVER,
                               current=3, total=3, unit="files"))
    # anything after the promotion is an ordinary update
    reporter(OperationProgress(operation=OP_BUNDLE, phase=PHASE_DISCOVER,
                               current=3, total=3, unit="files"))

    kinds = channel.kinds()
    assert kinds.count("begin") == 1, "promotion must not restart the widget"
    assert kinds.count("promote") == 1, "promote fires once, on the handoff"
    assert kinds == ["begin", "update", "update", "update", "promote", "update"]

    _, args, kwargs = channel.calls[4]
    assert args[0] == 3
    assert kwargs["current"] == 3
    assert kwargs["phase"] == PHASE_DISCOVER


def test_a_determinate_phase_never_promotes():
    """Extraction knows its size up front, so there is no handoff to make."""
    channel = RecordingChannel()
    reporter = TkProgressReporter(channel)

    for index in (1, 2, 3):
        reporter(OperationProgress(operation=OP_EXTRACT, phase=PHASE_WRITE,
                                   current=index, total=3, unit="files"))

    assert channel.kinds() == ["begin", "update", "update"]
    assert "promote" not in channel.kinds()


def test_each_phase_change_begins_a_new_thermometer():
    channel = RecordingChannel()
    reporter = TkProgressReporter(channel)

    reporter(OperationProgress(operation=OP_BUNDLE, phase=PHASE_DISCOVER,
                               current=2, total=2, unit="files"))
    reporter(OperationProgress(operation=OP_BUNDLE, phase=PHASE_READ,
                               current=1, total=2, unit="files"))

    assert channel.kinds().count("begin") == 2
    assert channel.calls[1][1][0].phase == PHASE_READ


def test_complete_posts_only_a_message():
    channel = RecordingChannel()
    reporter = TkProgressReporter(channel)
    reporter(OperationProgress(operation=OP_EXTRACT, phase=PHASE_WRITE,
                               current=1, total=1, unit="files"))
    channel.calls.clear()

    reporter(OperationProgress(operation=OP_EXTRACT, phase=PHASE_COMPLETE,
                               current=1, total=1, unit="files",
                               message="Extracted 1 of 1 files"))

    assert channel.kinds() == ["message"]
    assert reporter.completed is True
    assert reporter.completion_message == "Extracted 1 of 1 files"


def test_a_refusing_channel_does_not_disturb_the_reporter():
    """post_* returns False on a closed or full queue; it never raises.

    A dropped frame must not become an exception on the worker thread, where it
    would abort the operation being reported on.
    """
    channel = RecordingChannel(accept=False)
    reporter = TkProgressReporter(channel)

    for count in range(5):
        reporter(OperationProgress(operation=OP_BUNDLE, phase=PHASE_DISCOVER,
                                   current=count, total=None, unit="files"))

    assert len(channel.calls) == 5


# ---------------------------------------------------------------------------
# 2. run_with_progress - the threading contract
# ---------------------------------------------------------------------------

def test_work_runs_off_the_ui_thread_and_returns_its_value(tk_root):
    """The whole point: the UI thread stays free to repaint."""
    observed = {}
    main_thread = threading.current_thread()

    def work(progress=None, cancel=None):
        observed["thread"] = threading.current_thread()
        observed["sink"] = progress
        for index in range(1, 4):
            progress(OperationProgress(operation=OP_BUNDLE, phase=PHASE_READ,
                                       current=index, total=3, unit="files"))
        return "finished"

    result = run_with_progress(tk_root, "Working", work)

    assert result == "finished"
    assert observed["thread"] is not main_thread, "work must leave the UI thread"
    assert isinstance(observed["sink"], TkProgressReporter)


def test_a_worker_exception_is_reraised_on_the_calling_thread(tk_root):
    """The call sites catch exceptions to show a message box.

    If the thread boundary swallowed them, a failed bundle would report success.
    """
    def work(progress=None, cancel=None):
        raise ValueError("scan failed")

    with pytest.raises(ValueError, match="scan failed"):
        run_with_progress(tk_root, "Working", work)


def test_the_dialog_is_gone_afterwards(tk_root):
    """No orphaned Toplevel, and the grab is released."""
    before = set(tk_root.winfo_children())
    run_with_progress(tk_root, "Working", lambda progress=None, cancel=None: None)
    tk_root.update()
    after = set(tk_root.winfo_children())

    assert after == before, "the progress dialog was not destroyed"
    assert not tk_root.grab_current()


def test_no_cancel_dialog_maps_a_full_progress_canvas(tk_root, monkeypatch):
    """Open/validate operations must not render as a decoration-only sliver."""
    observed = {}
    real_widget = tk_progress.TkThermometer

    class ObservingThermometer(real_widget):
        def finish(self, *, ok=True, message=""):
            self.update_idletasks()
            observed.update(
                canvas_manager=self._canvas.winfo_manager(),
                requested_width=self.winfo_reqwidth(),
                requested_height=self.winfo_reqheight(),
            )
            return super().finish(ok=ok, message=message)

    monkeypatch.setattr(tk_progress, "TkThermometer", ObservingThermometer)

    run_with_progress(
        tk_root,
        "Reading",
        lambda progress=None, cancel=None: None,
        allow_cancel=False,
    )

    assert observed["canvas_manager"] == "grid"
    assert observed["requested_width"] >= 520
    assert observed["requested_height"] >= 56


def test_the_dialog_survives_an_exception_without_leaking(tk_root):
    before = set(tk_root.winfo_children())
    with pytest.raises(RuntimeError):
        run_with_progress(tk_root, "Working",
                          lambda progress=None, cancel=None: (_ for _ in ()).throw(RuntimeError("x")))
    tk_root.update()
    assert set(tk_root.winfo_children()) == before


def test_a_real_discovery_drives_a_real_thermometer(tk_root, tmp_path):
    """End to end: the writer's own event stream, through the real widget.

    This is the test that would catch a break in the seam itself rather than in
    either side of it.
    """
    from core.writer import BundleCreator

    for index in range(12):
        (tmp_path / f"f{index}.txt").write_text(f"line {index}\n", encoding="utf-8")

    creator = BundleCreator(allow_globs=["**/*"], deny_globs=[])
    files = run_with_progress(
        tk_root, "Scanning",
        lambda progress=None, cancel=None: creator.discover_files(tmp_path, tmp_path,
                                                     progress=progress),
    )

    assert len(files) == 12


def test_fast_worker_is_drained_and_finished_at_its_true_final_value(
        tk_root, monkeypatch):
    """A worker can fill the channel before the first 40 ms pump callback."""
    observed = {}
    real_widget = tk_progress.TkThermometer

    class ObservingThermometer(real_widget):
        def finish(self, *, ok=True, message=""):
            snap = self._model.snapshot()
            observed.update(
                ok=ok, message=message, current=snap.current,
                total=snap.total, phase=snap.phase,
            )
            return super().finish(ok=ok, message=message)

    monkeypatch.setattr(tk_progress, "TkThermometer", ObservingThermometer)

    def work(progress=None, cancel=None):
        progress(OperationProgress(
            operation=OP_BUNDLE, phase=PHASE_READ,
            current=0, total=600, unit="files"))
        for value in range(1, 601):
            progress(OperationProgress(
                operation=OP_BUNDLE, phase=PHASE_READ,
                current=value, total=600, unit="files"))
        progress(OperationProgress(
            operation=OP_BUNDLE, phase=PHASE_COMPLETE,
            current=600, total=600, unit="files", message="Read 600 files"))
        return "done"

    assert run_with_progress(tk_root, "Reading", work) == "done"
    assert observed == {
        "ok": True, "message": "Read 600 files", "current": 600.0,
        "total": 600.0, "phase": PHASE_READ,
    }


def test_worker_failure_draws_fail_before_the_dialog_closes(tk_root, monkeypatch):
    observed = {}
    real_widget = tk_progress.TkThermometer

    class ObservingThermometer(real_widget):
        def finish(self, *, ok=True, message=""):
            observed.update(ok=ok, message=message)
            return super().finish(ok=ok, message=message)

    monkeypatch.setattr(tk_progress, "TkThermometer", ObservingThermometer)

    def work(progress=None, cancel=None):
        progress(OperationProgress(
            operation=OP_BUNDLE, phase=PHASE_READ,
            current=1, total=2, unit="files"))
        raise ValueError("scan failed")

    with pytest.raises(ValueError, match="scan failed"):
        run_with_progress(tk_root, "Reading", work)

    assert observed == {"ok": False, "message": "scan failed"}


def test_renderer_failure_keeps_the_worker_error_primary_and_cleans_up(
        tk_root, monkeypatch):
    """Progress diagnostics must not replace the failure they were drawing."""
    real_widget = tk_progress.TkThermometer
    before = set(tk_root.winfo_children())

    class FailingThermometer(real_widget):
        def finish(self, *, ok=True, message=""):
            if not ok:
                raise RuntimeError("renderer failed")
            return super().finish(ok=ok, message=message)

    monkeypatch.setattr(tk_progress, "TkThermometer", FailingThermometer)

    def work(progress=None, cancel=None):
        raise ValueError("scan failed")

    with pytest.raises(ValueError, match="scan failed") as caught:
        run_with_progress(tk_root, "Reading", work)

    assert any("renderer failed" in note
               for note in getattr(caught.value, "__notes__", ()))
    tk_root.update()
    assert set(tk_root.winfo_children()) == before
    assert not tk_root.grab_current()


def test_missing_pythermx_runs_the_work_inline(tk_root, monkeypatch):
    """Graceful degradation, matching the CLI: no renderer, work still runs."""
    monkeypatch.setattr(tk_progress, "PYTHERMX_TK_AVAILABLE", False)
    seen = {}

    def work(progress=None, cancel=None):
        seen["sink"] = progress
        seen["thread"] = threading.current_thread()
        return 42

    assert run_with_progress(tk_root, "Working", work) == 42
    assert seen["sink"] is None
    assert seen["thread"] is threading.current_thread(), "inline means inline"


# ---------------------------------------------------------------------------
# 3. Layering
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("module", sorted((SRC / "core").rglob("*.py")),
                         ids=lambda p: p.name)
def test_core_imports_no_tk_renderer(module):
    """Core emits events. It knows about neither adapter, nor about Tkinter."""
    tree = ast.parse(module.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)

    for banned in ("tkinter", "pythermx", "pythermx.tk", "ui.tk_progress",
                   "cli_progress"):
        assert banned not in imported, f"{module.name} imports {banned}"


def test_the_tk_adapter_is_in_the_ui_layer():
    assert (SRC / "ui" / "tk_progress.py").is_file()
    assert not (SRC / "core" / "tk_progress.py").exists()


# ---------------------------------------------------------------------------
# 4. The size threshold
# ---------------------------------------------------------------------------

class _Config:
    def __init__(self, **values):
        self._values = values

    def get(self, key, default=None):
        return self._values.get(key, default)


def test_threshold_keeps_small_work_inline():
    """A modal dialog for eleven files is worse than no dialog."""
    from ui.bundle_frame import BundleFrame

    frame = BundleFrame.__new__(BundleFrame)          # no Tk needed for this
    frame.config_manager = _Config(**{"ui.progress.enabled": True,
                                      "ui.progress.min_files": 200})

    assert frame._progress_enabled(5) is False
    assert frame._progress_enabled(199) is False
    assert frame._progress_enabled(200) is True
    assert frame._progress_enabled(5000) is True
    # discovery cannot know its size in advance, so it always reports
    assert frame._progress_enabled(None) is True


def test_progress_can_be_switched_off_entirely():
    """Ringo's standing rule: configurable to a high degree."""
    from ui.bundle_frame import BundleFrame

    frame = BundleFrame.__new__(BundleFrame)
    frame.config_manager = _Config(**{"ui.progress.enabled": False,
                                      "ui.progress.min_files": 200})

    assert frame._progress_enabled(None) is False
    assert frame._progress_enabled(10_000) is False


def test_both_frames_apply_the_same_threshold_rule():
    from ui.bundle_frame import BundleFrame
    from ui.unbundle_frame import UnbundleFrame

    config = _Config(**{"ui.progress.enabled": True,
                        "ui.progress.min_files": 50})
    bundle = BundleFrame.__new__(BundleFrame)
    bundle.config_manager = config
    unbundle = UnbundleFrame.__new__(UnbundleFrame)
    unbundle.config_manager = config

    for count in (1, 49, 50, 1000):
        assert bundle._progress_enabled(count) == unbundle._progress_enabled(count)


def test_the_governed_config_ships_the_progress_settings():
    import json

    config = json.loads((SRC.parent / "bundle_config.json").read_text(encoding="utf-8"))
    progress = config["ui"]["progress"]
    assert progress["enabled"] is True
    assert isinstance(progress["min_files"], int)
