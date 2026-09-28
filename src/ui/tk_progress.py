# BFT_B108_PYTHERMX_TK_ADAPTER - maps OperationProgress onto pythermx.tk
# ===================================================================================================
# SOURCEFILE: tk_progress.py
# RELPATH: bundle_file_tool_v2/src/ui/tk_progress.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.108
# LIFECYCLE: Testing
# STATUS: Build 108 - BFT_B108_PYTHERMX_TK_ADAPTER
# DESCRIPTION: The Tkinter progress adapter. Lives in the UI layer, never in core.
# Relative Path: src/ui/tk_progress.py
# Purpose:
# independent_entry_point:
# ===================================================================================================
"""Show Bundle File Tool progress in the Tkinter UI, using PyThermX.

This is the second half of Paul's Build 104 ruling. The first half shipped in
Build 107:

    CLI maps those events to therm; Tkinter queues them onto the UI thread; Web
    streams or polls the same events. Do not make the shared service return CLI
    renderer objects.

Same `OperationProgress` stream, different adapter. `src/cli_progress.py` draws
it with `CLIThermometer`; this module draws it with `pythermx.tk`.

Why a worker thread is unavoidable
----------------------------------
Until now the UI called `discover_files()` straight from the button handler, so
Tk could not repaint until the whole walk finished. That is precisely the
"no feedback on large folder operations" complaint: not a missing widget, a
blocked event loop. A progress bar on the UI thread would freeze at its first
frame and prove nothing.

So the work moves to a worker thread and the display stays on the UI thread.
PyThermX 0.3.0 supplies the seam for exactly this and states the rule plainly:

    Only immutable values cross the channel, so a worker cannot reach the
    deliberately non-thread-safe model; the pump constructs and mutates models
    on the UI thread. The adapter creates no threads of its own.

**We** create the thread, because PyThermX deliberately does not. The worker
touches nothing but the channel; `ThermometerCore` and every Tk widget are
touched only by the pump and by the loop in `run_with_progress`.
"""

from __future__ import annotations

import threading
from typing import Any, Callable, Optional

from core.cancellation import OperationCancelled
from core.progress import PHASE_COMPLETE, OperationProgress
from ui.window_placement import place_toplevel_on_parent_monitor

try:  # pragma: no cover - exercised by the availability tests
    from pythermx import CancellationSource
    from pythermx.tk import (
        PhaseSpec,
        ThermometerCore,
        TkThermometer,
        TkThermometerStyle,
    )
    PYTHERMX_TK_AVAILABLE = True
except ImportError:  # pragma: no cover
    CancellationSource = None  # type: ignore[assignment]
    PhaseSpec = None  # type: ignore[assignment]
    ThermometerCore = None  # type: ignore[assignment]
    TkThermometer = None  # type: ignore[assignment]
    TkThermometerStyle = None  # type: ignore[assignment]
    PYTHERMX_TK_AVAILABLE = False

#: Shared with the CLI adapter so both surfaces name a phase the same way.
from cli_progress import PHASE_LABELS, settle_cancellation  # noqa: E402


class TkProgressReporter:
    """An `OperationProgress` sink that posts to a `TkThermometerChannel`.

    **Called on the worker thread.** It therefore touches the channel and
    nothing else - no widget, no model, no Tk call of any kind.

    The phase logic is deliberately identical to the CLI adapter's, because the
    semantics belong to the event stream rather than to either renderer: a new
    phase begins a thermometer, and an indeterminate phase that learns its total
    is promoted in place rather than replaced.
    """

    def __init__(self, channel: Any) -> None:
        self._channel = channel
        self._phase: Optional[str] = None
        self._total_known = False
        self._completed = False
        self._completion_message = ""

    @property
    def completed(self) -> bool:
        """Whether the worker emitted the operation's complete event."""
        return self._completed

    @property
    def completion_message(self) -> str:
        """The service-supplied terminal detail, retained for final render."""
        return self._completion_message

    def __call__(self, event: OperationProgress) -> None:
        """Render one event. Never raises - see core.progress.emit.

        Every `post_*` returns False rather than raising when the channel has
        closed or filled, which is the right shape here: a dropped frame is not
        a reason to disturb the operation being reported on.
        """
        if event.phase == PHASE_COMPLETE:
            self._completed = True
            self._completion_message = event.message or ""
            if event.message:
                self._channel.post_message(event.message)
            return

        if event.phase != self._phase:
            self._begin(event)
            return

        if not self._total_known and event.total is not None:
            # The discovery handoff: same thermometer, now with a real total.
            self._channel.post_promote(
                event.total, current=event.current, phase=event.phase)
            self._total_known = True
        else:
            self._channel.post_update(event.current)

        if event.message:
            self._channel.post_message(event.message)

    def _begin(self, event: OperationProgress) -> None:
        self._phase = event.phase
        self._total_known = event.total is not None
        self._channel.post_begin(PhaseSpec(
            total=event.total,
            label=PHASE_LABELS.get(event.phase, event.phase),
            unit=event.unit,
            phase=event.phase,
            current=event.current,
        ))
        if event.message:
            self._channel.post_message(event.message)


def default_style() -> Any:
    """The house style for progress dialogs.

    Kept as a function rather than a constant so a caller can build one, adjust
    a field with `dataclasses.replace`, and pass it back in - configurability
    without a mutable global that one window could change for every other.
    """
    from ui.progress_profile import load_progress_profile
    return load_progress_profile().tk_style()


def run_with_progress(parent: Any,
                      title: str,
                      work: Callable[..., Any],
                      *,
                      style: Optional[Any] = None,
                      poll_interval_s: float = 0.01,
                      allow_cancel: bool = True) -> Any:
    """Run `work(progress=sink)` on a worker thread behind a progress dialog.

    Args:
        parent: The owning widget; the dialog is transient and modal over it.
        title: Dialog caption.
        work: Callable taking a `progress` keyword. Runs on a worker thread, so
            it must not touch Tk - it may only report through the sink it is
            given.
        style: Optional `TkThermometerStyle`. Defaults to `default_style()`.
        poll_interval_s: How often the UI loop checks for completion.

    Returns:
        Whatever `work` returned.

    Raises:
        Whatever `work` raised, re-raised on the calling thread so existing
        `try/except` around these call sites keeps working unchanged.

    When PyThermX is unavailable this runs `work(progress=None)` inline and
    shows no dialog, which is the same graceful degradation the CLI takes.
    """
    if not PYTHERMX_TK_AVAILABLE:
        return work(progress=None, cancel=None)

    from ui.progress_profile import progress_enabled
    if not progress_enabled():
        return work(progress=None, cancel=None)

    import tkinter as tk

    selected_style = style or default_style()
    dialog = tk.Toplevel(parent)
    dialog.title(title)
    dialog.resizable(bool(selected_style.stretch), False)
    dialog.transient(parent.winfo_toplevel())
    # With a Cancel button present the window button can finally mean
    # something; without one it would still be a control that does nothing.
    dialog.protocol("WM_DELETE_WINDOW",
                    (lambda: source.request()) if allow_cancel else (lambda: None))

    # BFT_B112_TK_CANCEL_BUTTON. show_cancel is opt-in in PyThermX because the
    # button changes the widget's geometry, and the source is required because
    # the renderer does not own workflow control - it reports the request; the
    # worker decides when to honour it.
    source = CancellationSource() if allow_cancel else None
    token = source.token if source else None
    model = ThermometerCore(total=None, label=title, unit="files")
    widget = TkThermometer(dialog, model, style=selected_style,
                           show_cancel=bool(source),
                           cancellation_source=source)
    widget.pack(padx=14, pady=14, fill='x' if selected_style.stretch else 'none', expand=bool(selected_style.stretch))

    dialog.update_idletasks()
    _centre_over(dialog, parent)
    try:
        dialog.grab_set()
    except tk.TclError:
        # A grab can fail if another modal already owns the pointer. The dialog
        # is still shown and the work still runs; only modality is lost.
        pass

    done = threading.Event()
    outcome: dict = {}

    adapter_error: Optional[BaseException] = None
    try:
        with widget.live() as channel:
            reporter = TkProgressReporter(channel)

            def runner() -> None:
                try:
                    outcome["value"] = work(
                        progress=reporter,
                        cancel=(lambda: token.is_requested) if token else None,
                    )
                except OperationCancelled as error:
                    settle_cancellation(token)
                    outcome["error"] = error
                except BaseException as error:  # noqa: BLE001 - re-raised below
                    outcome["error"] = error
                finally:
                    done.set()

            thread = threading.Thread(
                target=runner, name="bft-progress", daemon=True)
            thread.start()

            # A nested UI loop: `update()` services the pump's after() callbacks,
            # so the bar redraws while the worker runs. Everything in this loop
            # is on the UI thread; the worker only ever posts to the channel.
            # Completion of the producer does not mean completion of the
            # consumer: a fast worker can finish before the first 40 ms pump
            # callback. Keep servicing Tk until every accepted semantic mutation
            # is applied.
            while not done.is_set() or channel.qsize() > 0:
                try:
                    dialog.update()
                except tk.TclError:
                    break                        # dialog destroyed underneath us
                done.wait(poll_interval_s)

            thread.join(timeout=5.0)
            if thread.is_alive():
                raise RuntimeError(
                    "progress worker did not stop after the dialog closed")

            # Draw the true terminal outcome while the widget and live
            # generation still exist. finish*() stops the pump only after the
            # queue is drained.
            error = outcome.get("error")
            if isinstance(error, OperationCancelled):
                widget.finish_cancelled(message="Cancelled")
            elif error is not None:
                widget.finish(
                    ok=False, message=str(error) or type(error).__name__)
            else:
                widget.finish(
                    ok=True,
                    message=reporter.completion_message or "Complete",
                )
            try:
                dialog.update_idletasks()
            except tk.TclError:
                pass
    except BaseException as error:              # renderer/pump/UI failure
        adapter_error = error
    finally:
        # The dialog owns a grab. Release it on worker, renderer and pump
        # failures alike so an optional diagnostic can never strand the app.
        try:
            dialog.grab_release()
            dialog.destroy()
        except tk.TclError:
            pass

    if "error" in outcome:
        if adapter_error is not None and adapter_error is not outcome["error"]:
            try:
                outcome["error"].add_note(
                    f"Progress renderer also failed: {adapter_error}")
            except (AttributeError, TypeError):
                pass
        raise outcome["error"]
    if adapter_error is not None:
        raise adapter_error
    return outcome.get("value")


def _centre_over(dialog: Any, parent: Any) -> None:
    """Centre the dialog on the display containing its parent."""
    place_toplevel_on_parent_monitor(dialog, parent)
