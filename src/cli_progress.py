# BFT_B107_PYTHERMX_CLI_ADAPTER - maps OperationProgress onto PyThermX
# ===================================================================================================
# SOURCEFILE: cli_progress.py
# RELPATH: bundle_file_tool_v2/src/cli_progress.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.107
# LIFECYCLE: Testing
# STATUS: Build 107 - BFT_B107_PYTHERMX_CLI_ADAPTER
# DESCRIPTION: The CLI's progress renderer. Lives in the CLI layer, never in core.
# Relative Path: src/cli_progress.py
# Purpose:
# independent_entry_point:
# ===================================================================================================
"""Render Bundle File Tool progress with PyThermX.

Paul's Build 104 review set the shape of this: the service emits
`OperationProgress` events and *the adapter* decides how to draw them.

    CLI maps those events to therm; Tkinter queues them onto the UI thread; Web
    streams or polls the same events. Do not make the shared service return CLI
    renderer objects.

So this module lives beside `cli.py`, not under `core/`. Core has no idea it
exists, and a test asserts that stays true.

Three properties matter:

**PyThermX is optional.** Bundle File Tool must work when it is not installed.
`build_reporter()` returns None in that case and every call site already treats
a missing sink as "no progress".

**Progress goes to stderr.** PyThermX 0.2.0 defaults there, which matches the
Build 105 rule that stdout carries the bundle artifact and nothing else. A
progress bar that corrupted a piped bundle would be a spectacular own goal.

**The discovery handoff is the point.** Discovery reports a rising count with no
total, then a total once it finishes. That is exactly `promote()`, so the bar
turns from a spinner-with-count into a real percentage at the moment the size
becomes known, on the same handle, without the user seeing two widgets.
"""

from __future__ import annotations

import sys
from contextlib import contextmanager
from typing import Any, Optional

from core.cancellation import OperationCancelled
from core.progress import PHASE_COMPLETE, OperationProgress

try:  # pragma: no cover - exercised by the availability tests
    from pythermx import (
        CancellationSource,
        CancellationState,
        CLIThermometer,
        CLIThermometerStyle,
        ThermometerCore,
    )
    from pythermx.thermometer_cli import capture_sigint
    PYTHERMX_AVAILABLE = True
except ImportError:  # pragma: no cover
    CancellationSource = None  # type: ignore[assignment]
    CancellationState = None  # type: ignore[assignment]
    capture_sigint = None  # type: ignore[assignment]
    CLIThermometer = None  # type: ignore[assignment]
    CLIThermometerStyle = None  # type: ignore[assignment]
    ThermometerCore = None  # type: ignore[assignment]
    PYTHERMX_AVAILABLE = False


#: Human-readable phase labels. The event vocabulary is machine-facing; this is
#: what an operator actually reads.
PHASE_LABELS = {
    "discover": "Discovering",
    "plan": "Planning",
    "verify": "Checking safety",
    "verify-source": "Verifying source snapshot",
    "read": "Reading",
    "verify-read": "Reconciling source snapshot",
    "integrity": "Checking bundle integrity",
    "format": "Formatting",
    "parse": "Parsing",
    "write": "Writing",
    "finalize": "Finalizing safely",
    "complete": "Done",
}


class PyThermXReporter:
    """An `OperationProgress` sink that draws with PyThermX.

    One thermometer per phase. Within a phase, an indeterminate run that later
    learns its total is promoted rather than replaced, so the display is
    continuous.
    """

    def __init__(self, stream: Optional[Any] = None,
                 style: Optional[Any] = None) -> None:
        if not PYTHERMX_AVAILABLE:
            raise RuntimeError(
                "PyThermX is not installed. Call build_reporter(), which "
                "returns None instead of raising when it is unavailable."
            )
        self._stream = stream
        from ui.progress_profile import load_progress_profile
        self._style = style if style is not None else load_progress_profile().cli_style()
        self._phase: Optional[str] = None
        self._model: Optional[Any] = None
        self._bar: Optional[Any] = None

    # -----------------------------------------------------------------
    # Sink protocol
    # -----------------------------------------------------------------

    def __call__(self, event: OperationProgress) -> None:
        """Render one event. Never raises - see core.progress.emit."""
        if event.phase == PHASE_COMPLETE:
            self._finish(event)
            return

        if event.phase != self._phase:
            self._start_phase(event)
        else:
            self._advance(event)

        if self._bar is not None:
            self._bar.render(message=event.message or "")

    # -----------------------------------------------------------------
    # Internals
    # -----------------------------------------------------------------

    def _start_phase(self, event: OperationProgress) -> None:
        self._close_bar()
        self._phase = event.phase
        label = PHASE_LABELS.get(event.phase, event.phase)

        self._model = ThermometerCore(
            total=event.total,
            label=label,
            unit=event.unit,
            phase=event.phase,
        )
        if event.current:
            self._model.update(event.current)
        self._bar = CLIThermometer(self._model, style=self._style,
                                   stream=self._stream)
        self._bar.start()

    def _advance(self, event: OperationProgress) -> None:
        if self._model is None:
            return
        # An indeterminate phase that has just learned its size: promote rather
        # than build a second widget, so the display stays continuous.
        #
        # The test is the model's own total, not a mode string. Both packages
        # happen to spell it "indeterminate" today, but PyThermX's vocabulary is
        # its own and comparing across that seam would couple us to a constant
        # nobody has promised to keep.
        if self._model.total is None and event.total is not None:
            self._model.promote(total=event.total, current=event.current)
            return
        self._model.update(event.current)

    def _close_bar(self, ok: bool = True, message: str = "") -> None:
        if self._bar is not None:
            self._bar.finish(ok=ok, message=message)
        self._bar = None
        self._model = None

    def _finish(self, event: OperationProgress) -> None:
        self._close_bar(ok=True, message=event.message or "")
        self._phase = None

    def close(self) -> None:
        """Finalise any bar still open, so the terminal line is restored."""
        self._close_bar()
        self._phase = None

    def failed(self, message: str = "Failed") -> None:
        """Close the bar as FAILED rather than claiming success."""
        try:
            self._close_bar(ok=False, message=message)
        except Exception:
            # Progress is diagnostic. A renderer failure must never replace
            # the operation error that led us here.
            self._bar = None
            self._model = None
        finally:
            self._phase = None

    def cancelled(self, message: str = "Cancelled") -> None:
        """Close the bar as CANCELLED rather than OK or FAILED.

        BFT_B112_CLI_CANCEL_OUTCOME. PyThermX 0.4.0 added this as a third
        terminal outcome for a reason worth repeating: finishing the bar as
        success claims work that was abandoned, and as failure it blames the
        system for the operator's decision.
        """
        try:
            if self._bar is not None:
                self._bar.finish_cancelled(message=message)
        except Exception:
            pass
        finally:
            self._bar = None
            self._model = None
            self._phase = None


def build_reporter(mode: str = "auto",
                   stream: Optional[Any] = None) -> Optional[PyThermXReporter]:
    """Return a reporter, or None when progress should not be drawn.

    Args:
        mode: "auto" draws only on an interactive terminal with PyThermX
            installed; "bar" forces it on; "none" disables it.
        stream: Defaults to stderr, so stdout stays reserved for the artifact.

    A returned None is not an error. Every call site treats a missing sink as
    "no progress", which is also what happens when PyThermX is absent.
    """
    if mode == "none":
        return None
    if not PYTHERMX_AVAILABLE:
        return None

    from ui.progress_profile import progress_enabled
    if not progress_enabled():
        return None

    target = stream if stream is not None else sys.stderr

    if mode == "auto":
        is_tty = bool(getattr(target, "isatty", lambda: False)())
        if not is_tty:
            return None

    return PyThermXReporter(stream=target)


@contextmanager
def cancellation_scope(enabled: bool = True):
    """Yield a cancel predicate, with Ctrl+C routed into a cancellation request.

    BFT_B112_CLI_CANCEL_SCOPE. PyThermX's `capture_sigint` turns the first
    Ctrl+C into a request the operation polls, and escalates the second - so an
    unresponsive worker can never trap the operator at their own terminal.

    Yields None when PyThermX is absent or cancellation is disabled, which is
    the same "no canceller" path core already handles: the work simply runs to
    completion and the default KeyboardInterrupt behaviour applies.
    """
    if not enabled or not PYTHERMX_AVAILABLE:
        yield None
        return

    source = CancellationSource()
    token = source.token
    with capture_sigint(source, stream=sys.stderr):
        try:
            yield lambda: token.is_requested
        except OperationCancelled:
            settle_cancellation(token)
            raise


def settle_cancellation(token: Any) -> bool:
    """Complete PyThermX's worker-owned cancellation lifecycle.

    BFT core deliberately consumes only a boolean predicate, so it cannot own
    the PyThermX acknowledgement. The adapter that created the token bridges
    that smaller seam back to the full protocol when core confirms that it
    stopped cooperatively.
    """
    if token is None or not token.is_requested:
        return False
    if token.state is CancellationState.REQUESTED:
        token.acknowledge()
    if token.state is CancellationState.CANCELLING:
        token.complete()
    return token.state is CancellationState.CANCELLED


def pythermx_version() -> Optional[str]:
    """The installed PyThermX version, or None when it is not available."""
    if not PYTHERMX_AVAILABLE:
        return None
    try:
        import pythermx
        return getattr(pythermx, "__version__", None)
    except Exception:  # pragma: no cover
        return None
