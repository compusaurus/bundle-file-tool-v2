# BFT_B106_PROGRESS_EVENT_CONTRACT - serializable, renderer-agnostic progress
# ===================================================================================================
# SOURCEFILE: progress.py
# RELPATH: bundle_file_tool_v2/src/core/progress.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.106
# LIFECYCLE: Testing
# STATUS: Build 106 - BFT_B106_PROGRESS_EVENT_CONTRACT
# DESCRIPTION: The progress event every operation emits and every adapter renders.
# Relative Path: src/core/progress.py
# Purpose:
# independent_entry_point:
# ===================================================================================================
"""A serializable progress event owned by Bundle File Tool.

Paul's Build 104 review, "Put progress at the future service boundary":

    Add a serializable BFT-owned OperationProgress event/DTO - operation, phase,
    mode, current, total, unit, message - and an optional callback/event sink on
    service requests. CLI maps those events to therm; Tkinter queues them onto
    the UI thread; Web streams or polls the same events. Do not make the shared
    service return CLI renderer objects.

Two rules follow from that, and both are load-bearing:

1. **This module imports no renderer and no toolkit.** It knows nothing about
   therm, Tkinter or Flask. An event is data; drawing it is an adapter's job.
   That is what lets one operation feed three interfaces without the service
   growing a dependency on any of them.
2. **A progress sink can never break the operation it observes.** Reporting is
   strictly secondary to the work. `emit()` swallows sink failures for the same
   reason the Build 105 drift reporter does: a diagnostic that takes down the
   command it is diagnosing is worse than no diagnostic.

Discovery is the motivating case. It has no total until it finishes, so it
reports `mode="indeterminate"` with a rising `current` and `total=None`. Every
other phase knows its size and reports `mode="determinate"`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from time import monotonic as _monotonic
from typing import Any, Callable, Dict, Optional

# Operation names. An adapter may key presentation off these.
OP_BUNDLE = "bundle"
OP_EXTRACT = "extract"
OP_VALIDATE = "validate"
OP_CHECK = "check"

# Phase names within an operation.
PHASE_DISCOVER = "discover"
PHASE_PLAN = "plan"
PHASE_VERIFY = "verify"
PHASE_VERIFY_SOURCE = "verify-source"
PHASE_READ = "read"
PHASE_VERIFY_READ = "verify-read"
PHASE_INTEGRITY = "integrity"
PHASE_FORMAT = "format"
PHASE_PARSE = "parse"
PHASE_WRITE = "write"
PHASE_FINALIZE = "finalize"
PHASE_COMPLETE = "complete"

MODE_DETERMINATE = "determinate"
MODE_INDETERMINATE = "indeterminate"


@dataclass(frozen=True)
class OperationProgress:
    """One immutable progress observation.

    Attributes:
        operation: Which operation is running - OP_BUNDLE, OP_EXTRACT, OP_VALIDATE.
        phase: Which stage within it - PHASE_DISCOVER, PHASE_WRITE, and so on.
        mode: MODE_DETERMINATE when `total` is known, MODE_INDETERMINATE otherwise.
        current: Work completed so far. Rises monotonically within a phase.
        total: Total work, or None when it cannot be known yet.
        unit: Noun for the count - "files", "entries", "bytes".
        message: Optional human-readable detail.
    """

    operation: str
    phase: str
    current: float = 0.0
    total: Optional[float] = None
    unit: str = "items"
    message: Optional[str] = None

    @property
    def mode(self) -> str:
        return MODE_DETERMINATE if self.total is not None else MODE_INDETERMINATE

    @property
    def percent(self) -> Optional[float]:
        """Completion as a percentage, or None when it cannot be known.

        None rather than 0.0, deliberately. A renderer handed 0.0 will draw an
        empty bar and tell the user nothing has happened, when the truth is that
        we cannot know. None forces a deliberate choice.
        """
        if self.total is None or self.total <= 0:
            return None
        return min(100.0, (self.current / self.total) * 100.0)

    def to_dict(self) -> Dict[str, Any]:
        """Serializable form, for a web adapter or a log.

        `mode` and `percent` are derived, but they are included because a
        consumer on the far side of a socket cannot call a property.
        """
        return {
            "operation": self.operation,
            "phase": self.phase,
            "mode": self.mode,
            "current": self.current,
            "total": self.total,
            "unit": self.unit,
            "message": self.message,
            "percent": self.percent,
        }


#: What a caller supplies to observe an operation.
ProgressSink = Callable[[OperationProgress], None]


def emit(sink: Optional[ProgressSink], event: OperationProgress) -> None:
    """Deliver an event to a sink, if there is one, without ever raising.

    A failing or badly behaved sink must not abort the operation being reported
    on. Progress is an observation, not a step of the work.
    """
    if sink is None:
        return
    try:
        sink(event)
    except Exception:
        return


#: Default reporting interval for tight loops. Well inside the window at which
#: a progress bar still reads as live, and cheap enough to test per iteration.
EMIT_INTERVAL_S = 0.10


class ThrottledReporter:
    """Rate-limited progress for a tight loop.

    Build 111. A loop over a million lines must not call the sink a million
    times - `emit()` delivers synchronously, so an unthrottled tick saturates
    the consumer. Equally it must not report only on "interesting" iterations,
    because a stretch with nothing interesting in it is exactly when a user
    needs to see the operation is alive. That was the Build 110 discovery
    defect. This reports on a clock instead of on events.

    The first `tick()` always reports, so a loop that finishes inside one
    interval still produces an observation.

    Args:
        sink: Where to deliver, or None to disable entirely.
        operation: OP_BUNDLE, OP_EXTRACT, OP_VALIDATE.
        phase: PHASE_PARSE, PHASE_READ, and so on.
        unit: Noun for the count - "lines", "bytes", "files".
        total: Total work when known, else None for an indeterminate phase.
        interval_s: Minimum seconds between reports.

    Example:
        >>> r = ThrottledReporter(None, OP_EXTRACT, PHASE_PARSE, "lines", total=3)
        >>> r.tick(1, message="working")   # no sink: silently does nothing
        >>> r.close(3)
    """

    __slots__ = ("_sink", "_operation", "_phase", "_unit", "_total",
                 "_interval", "_last", "_emitted")

    def __init__(self,
                 sink: Optional[ProgressSink],
                 operation: str,
                 phase: str,
                 unit: str,
                 total: Optional[int] = None,
                 interval_s: float = EMIT_INTERVAL_S) -> None:
        self._sink = sink
        self._operation = operation
        self._phase = phase
        self._unit = unit
        self._total = total
        self._interval = interval_s
        # None rather than a primed timestamp: monotonic() returns a large
        # float, so priming by subtraction loses the comparison to rounding
        # and the first tick never fires.
        self._last: Optional[float] = None
        self._emitted = 0

    @property
    def emitted(self) -> int:
        """How many events actually reached the sink."""
        return self._emitted

    def tick(self, current: int, message: Optional[str] = None) -> None:
        """Report `current` if the interval has elapsed, otherwise do nothing.

        Called once per loop iteration - hundreds of thousands of times on a
        large bundle - so the body stays deliberately cheap. `monotonic` is
        bound at module import; importing it here instead cost 20% of parse
        time in a sys.modules lookup per line.
        """
        if self._sink is None:
            return
        now = _monotonic()
        if self._last is not None and now - self._last < self._interval:
            return
        self._last = now
        self._emitted += 1
        emit(self._sink, OperationProgress(
            operation=self._operation, phase=self._phase,
            current=current, total=self._total, unit=self._unit,
            message=message,
        ))

    def close(self, current: int, total: Optional[int] = None,
              message: Optional[str] = None) -> None:
        """Report the final, determinate state. Always emits."""
        if self._sink is None:
            return
        final_total = total if total is not None else (
            self._total if self._total is not None else current)
        self._emitted += 1
        emit(self._sink, OperationProgress(
            operation=self._operation, phase=self._phase,
            current=current, total=final_total, unit=self._unit,
            message=message,
        ))


@dataclass
class ProgressRecorder:
    """A sink that keeps every event. Useful for tests and for adapters that
    want to replay or inspect an operation after it completes."""

    events: list = field(default_factory=list)

    def __call__(self, event: OperationProgress) -> None:
        self.events.append(event)

    def phases(self) -> list:
        """Phase names in the order they first appeared."""
        seen, ordered = set(), []
        for event in self.events:
            if event.phase not in seen:
                seen.add(event.phase)
                ordered.append(event.phase)
        return ordered

    def last_for(self, phase: str) -> Optional[OperationProgress]:
        for event in reversed(self.events):
            if event.phase == phase:
                return event
        return None
