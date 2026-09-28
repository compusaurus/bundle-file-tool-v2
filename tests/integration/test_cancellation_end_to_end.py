# BFT_B112_CANCELLATION_END_TO_END
# ============================================================================
# SOURCEFILE: test_cancellation_end_to_end.py
# RELPATH: bundle_file_tool_v2/tests/integration/test_cancellation_end_to_end.py
# PROJECT: Bundle File Tool v2.1
# VERSION: 2.1.112
# LIFECYCLE: Testing
# STATUS: Build 112 - BFT_B112_CANCELLATION_END_TO_END
# ============================================================================
"""Cancellation through the service, the CLI and the Cancel button.

Core owns the seam; these are the three surfaces that drive it. The Tk case is
the one Ringo actually asked for — a real `TkThermometer` with `show_cancel`,
a real `CancellationSource`, and a real worker thread that stops when the
button is pressed.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from core.cancellation import CancelRecorder, OperationCancelled
from core.progress import (
    PHASE_FINALIZE,
    PHASE_FORMAT,
    PHASE_INTEGRITY,
    PHASE_READ,
    PHASE_VERIFY_READ,
    PHASE_VERIFY_SOURCE,
    PHASE_WRITE,
    ProgressRecorder,
)

SRC = Path(__file__).resolve().parents[2] / "src"


@pytest.fixture
def tree(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    for index in range(10):
        (source / f"f{index:02d}.txt").write_text(f"line {index}\n", encoding="utf-8")
    return source


# ---------------------------------------------------------------------------
# 1. The service facade
# ---------------------------------------------------------------------------

def test_service_create_bundle_is_cancellable(tree, tmp_path):
    from core.service import BundleToolService

    with pytest.raises(OperationCancelled) as caught:
        BundleToolService().create_bundle(
            [tree], base_path=tree, profile="plain_marker",
            output_path=tmp_path / "b.txt", cancel=CancelRecorder(after=3))

    assert caught.value.operation in {"bundle"}
    assert not (tmp_path / "b.txt").exists(), (
        "a cancelled bundle must not leave an output file"
    )


def test_service_extract_bundle_is_cancellable(tree, tmp_path):
    from core.service import BundleToolService

    service = BundleToolService()
    bundle = tmp_path / "b.txt"
    service.create_bundle([tree], base_path=tree, profile="plain_marker",
                          output_path=bundle)

    recorder = ProgressRecorder()

    def cancel_after_four_writes():
        writes = [event.current for event in recorder.events
                  if event.phase == PHASE_WRITE]
        return bool(writes and writes[-1] >= 4)

    with pytest.raises(OperationCancelled) as caught:
        service.extract_bundle(bundle, output_dir=tmp_path / "out",
                               overwrite_policy="overwrite",
                               progress=recorder,
                               cancel=cancel_after_four_writes)

    assert caught.value.operation == "extract"
    assert len(caught.value.partial_paths) == 4


def test_service_operations_are_unaffected_without_a_canceller(tree, tmp_path):
    from core.service import BundleToolService

    result = BundleToolService().create_bundle(
        [tree], base_path=tree, profile="plain_marker",
        output_path=tmp_path / "b.txt", cancel=lambda: False)
    assert result.file_count == 10


@pytest.mark.parametrize("phase", [
    PHASE_VERIFY_SOURCE,
    PHASE_READ,
    PHASE_VERIFY_READ,
    PHASE_INTEGRITY,
    PHASE_FORMAT,
    PHASE_WRITE,
    PHASE_FINALIZE,
])
def test_every_long_bundle_phase_is_cancellable_before_publication(
        tree, tmp_path, phase):
    """A 100% sub-phase is never a point of no return."""
    from core.service import BundleToolService

    recorder = ProgressRecorder()
    target = tmp_path / f"cancel-{phase}.txt"

    def cancel_when_phase_is_visible():
        return bool(recorder.events and recorder.events[-1].phase == phase)

    with pytest.raises(OperationCancelled) as caught:
        BundleToolService().create_bundle(
            [tree], base_path=tree, profile="plain_marker",
            output_path=target, progress=recorder,
            cancel=cancel_when_phase_is_visible)

    assert caught.value.phase == phase
    assert not target.exists()


# ---------------------------------------------------------------------------
# 2. The CLI: a cancelled run is a third outcome, not an error
# ---------------------------------------------------------------------------

@pytest.fixture
def forced_cancel(monkeypatch):
    """Replace the CLI's cancellation scope with a deterministic one.

    A real Ctrl+C cannot be delivered reliably inside a test, and the thing
    worth testing is not signal plumbing but what the CLI *does* once
    cancellation is requested: which message, which exit code, which stream.
    """
    from contextlib import contextmanager

    import cli as cli_module

    @contextmanager
    def scope(enabled: bool = True):
        yield CancelRecorder(after=3)

    monkeypatch.setattr(cli_module, "cancellation_scope", scope)
    return scope


def test_cli_bundle_cancels_with_status_130(tree, tmp_path, capsys, forced_cancel):
    import cli as cli_module

    with pytest.raises(SystemExit) as caught:
        cli_module.main(["bundle", str(tree), "--base-path", str(tree),
                         "--profile", "plain_marker",
                         "-o", str(tmp_path / "b.txt"), "--progress", "none"])

    assert caught.value.code == 130, "cancelled-by-request is status 130"

    captured = capsys.readouterr()
    assert "Cancelled" in captured.err
    assert "ERROR:" not in captured.err, (
        "a cancellation must never be reported as an error - it is the "
        "operator's decision, not a failure of the tool"
    )


def test_cli_unbundle_cancels_and_names_the_partial_files(tree, tmp_path, capsys,
                                                          forced_cancel):
    import cli as cli_module

    bundle = tmp_path / "b.txt"
    with pytest.raises(SystemExit) as made:
        cli_module.main(["bundle", str(tree), "--base-path", str(tree),
                         "--profile", "plain_marker", "-o", str(bundle),
                         "--progress", "none"])
    # the bundle itself was cancelled by the fixture; build one for real
    if not bundle.exists():
        from core.parser import ProfileRegistry
        from core.writer import BundleCreator

        creator = BundleCreator(allow_globs=["**/*"], deny_globs=[])
        manifest = creator.create_manifest(
            creator.discover_files(tree, tree), tree, "plain_marker")
        bundle.write_text(
            ProfileRegistry().get("plain_marker").format_manifest(manifest),
            encoding="utf-8")
    capsys.readouterr()

    with pytest.raises(SystemExit) as caught:
        cli_module.main(["unbundle", str(bundle), "-o", str(tmp_path / "out"),
                         "--overwrite", "overwrite", "--progress", "none"])

    assert caught.value.code == 130
    captured = capsys.readouterr()
    assert "Cancelled" in captured.err
    assert "were already written" in captured.err, (
        "the operator must be told what is on their disk"
    )


def test_a_completed_cli_run_is_still_status_zero(tree, tmp_path, capsys):
    """The cancellation path must not disturb the ordinary one."""
    import cli as cli_module

    with pytest.raises(SystemExit) as caught:
        cli_module.main(["bundle", str(tree), "--base-path", str(tree),
                         "--profile", "plain_marker",
                         "-o", str(tmp_path / "b.txt"), "--progress", "none"])

    assert caught.value.code == 0
    assert (tmp_path / "b.txt").is_file()


def test_the_cancellation_scope_degrades_without_pythermx(monkeypatch):
    """No PyThermX means no signal capture, and no canceller - not a crash."""
    import cli_progress

    monkeypatch.setattr(cli_progress, "PYTHERMX_AVAILABLE", False)
    with cli_progress.cancellation_scope() as cancel:
        assert cancel is None


def test_the_cancellation_scope_yields_a_working_predicate():
    """With PyThermX present the scope hands back a live predicate."""
    pytest.importorskip("pythermx")
    import cli_progress

    with cli_progress.cancellation_scope() as cancel:
        assert callable(cancel)
        assert cancel() is False, "nothing has been requested yet"


# ---------------------------------------------------------------------------
# 3. The Cancel button
# ---------------------------------------------------------------------------

def test_the_dialog_offers_a_cancel_button_by_default(tk_root, tree):
    """`show_cancel` is opt-in in PyThermX; BFT opts in for long work."""
    import ui.tk_progress as tk_progress

    captured = {}
    real = tk_progress.TkThermometer

    def spy(master, model, **kwargs):
        captured.update(kwargs)
        return real(master, model, **kwargs)

    tk_progress.TkThermometer = spy
    try:
        tk_progress.run_with_progress(
            tk_root, "Working", lambda progress=None, cancel=None: "done")
    finally:
        tk_progress.TkThermometer = real

    assert captured.get("show_cancel") is True
    assert captured.get("cancellation_source") is not None, (
        "the renderer needs a source; it reports the request, it does not own it"
    )


def test_allow_cancel_false_offers_no_button(tk_root):
    import ui.tk_progress as tk_progress

    captured = {}
    real = tk_progress.TkThermometer

    def spy(master, model, **kwargs):
        captured.update(kwargs)
        return real(master, model, **kwargs)

    tk_progress.TkThermometer = spy
    try:
        tk_progress.run_with_progress(
            tk_root, "Working", lambda progress=None, cancel=None: "done",
            allow_cancel=False)
    finally:
        tk_progress.TkThermometer = real

    assert captured.get("show_cancel") is False
    assert captured.get("cancellation_source") is None


def _find_cancel_control(widget):
    """Locate the Cancel control PyThermX builds inside the thermometer."""
    stack = [widget]
    while stack:
        node = stack.pop()
        try:
            label = str(node.cget("text")).strip().lower()
        except Exception:
            label = ""
        if label == "cancel":
            return node
        stack.extend(node.winfo_children())
    return None


def test_the_cancel_control_is_wired_to_the_cancellation_source(tk_root):
    """Press the actual widget and watch the actual source change state.

    Synchronous and threadless on purpose. `run_with_progress` hands the source
    to the renderer and trusts it to be connected; this is the test that the
    trust is warranted, with no timing in it to be flaky about.
    """
    from pythermx import CancellationSource
    from pythermx.tk import TkThermometer, ThermometerCore

    source = CancellationSource()
    model = ThermometerCore(total=10, label="Working", unit="files")
    widget = TkThermometer(tk_root, model, show_cancel=True,
                           cancellation_source=source)
    widget.pack()
    tk_root.update_idletasks()

    control = _find_cancel_control(widget)
    assert control is not None, "no Cancel control was rendered"
    assert source.is_requested is False

    control.invoke()                      # exactly what a mouse click does
    tk_root.update_idletasks()

    assert source.is_requested is True, "the Cancel control is not wired"

    widget.destroy()
    tk_root.update_idletasks()


def test_no_cancel_control_is_rendered_when_it_is_not_offered(tk_root):
    from pythermx.tk import TkThermometer, ThermometerCore

    model = ThermometerCore(total=10, label="Working", unit="files")
    widget = TkThermometer(tk_root, model, show_cancel=False)
    widget.pack()
    tk_root.update_idletasks()

    assert _find_cancel_control(widget) is None

    widget.destroy()
    tk_root.update_idletasks()


def test_the_worker_receives_a_live_cancel_predicate(tk_root):
    seen = {}

    from ui.tk_progress import run_with_progress

    def work(progress=None, cancel=None):
        seen["callable"] = callable(cancel)
        seen["initially"] = cancel() if callable(cancel) else None
        return "ok"

    assert run_with_progress(tk_root, "Working", work) == "ok"
    assert seen["callable"] is True
    assert seen["initially"] is False


def test_pressing_cancel_stops_a_real_worker(tk_root, tree):
    """The end-to-end button behaviour, with a real source and a real thread.

    The press is programmatic because a test cannot click, but everything on
    the other side of it is real: `CancellationSource.request()` is exactly what
    the button calls, and the worker is the actual discovery code polling the
    actual predicate.
    """
    import ui.tk_progress as tk_progress
    from core.writer import BundleCreator

    sources = []
    real_source = tk_progress.CancellationSource

    def capture():
        source = real_source()
        sources.append(source)
        return source

    tk_progress.CancellationSource = capture

    creator = BundleCreator(allow_globs=["**/*"], deny_globs=[])

    def work(progress=None, cancel=None):
        # request cancellation the moment the worker starts, then do real work
        sources[0].request()
        return creator.create_manifest(
            creator.discover_files(tree, tree), tree, "plain_marker",
            progress=progress, cancel=cancel)

    try:
        with pytest.raises(OperationCancelled) as caught:
            tk_progress.run_with_progress(tk_root, "Scanning", work)
    finally:
        tk_progress.CancellationSource = real_source

    assert caught.value.phase == "read"
    assert sources[0].is_requested is True
    assert sources[0].state.value == "cancelled", (
        "the worker must acknowledge and complete the PyThermX lifecycle"
    )


def test_the_dialog_is_cleaned_up_after_a_cancellation(tk_root):
    """A cancelled run must not leave a modal window behind."""
    from ui.tk_progress import run_with_progress

    before = set(tk_root.winfo_children())

    def work(progress=None, cancel=None):
        raise OperationCancelled(operation="bundle", phase="read", completed=1)

    with pytest.raises(OperationCancelled):
        run_with_progress(tk_root, "Working", work)
    tk_root.update()

    assert set(tk_root.winfo_children()) == before
    assert not tk_root.grab_current()
