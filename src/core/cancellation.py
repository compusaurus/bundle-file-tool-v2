# BFT_B112_CANCELLATION_CONTRACT - cooperative cancellation, renderer-agnostic
# ===================================================================================================
# SOURCEFILE: cancellation.py
# RELPATH: bundle_file_tool_v2/src/core/cancellation.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.112
# LIFECYCLE: Testing
# STATUS: Build 112 - BFT_B112_CANCELLATION_CONTRACT
# ===================================================================================================
"""Cooperative cancellation, owned by Bundle File Tool.

PyThermX 0.4.0 supplies a full cancellation protocol - `CancellationSource`,
`CancellationToken`, four states and three terminal outcomes - and Build 112 is
built on it. But **core must not import PyThermX**, and an AST test enforces
that, for the same reason it holds for progress: one operation feeds a CLI, a
Tkinter GUI and eventually a Web adapter, and the moment core depends on one
renderer's library that stops being true.

So core owns the seam and the adapters bridge to it, exactly as
`OperationProgress` does for progress. What core needs from a canceller is a
single question - *has cancellation been requested?* - so the contract is one
callable returning a bool. `ui/tk_progress.py` and `cli_progress.py` supply
`lambda: token.is_requested` over a real PyThermX token.

Two properties are deliberate.

**Cancellation is cooperative, never forced.** Nothing here interrupts a
thread. Operations poll between units of work, so a cancel takes effect at the
next file rather than immediately - and PyThermX models that honestly, which is
why `requested` and `cancelled` are different states there.

**Checking never raises on the caller's behalf.** `is_cancelled()` swallows a
misbehaving predicate and reports False, on the same reasoning as `emit()`: a
broken canceller must not abort work the user did not ask to stop. Only the
explicit `raise_if_cancelled()` raises, and only when cancellation really was
requested.
"""

from __future__ import annotations

from typing import Callable, Optional

from core.exceptions import BundleFileToolError

#: What core polls. True means the operator has asked for the work to stop.
CancelCheck = Callable[[], bool]


class OperationCancelled(BundleFileToolError):
    """Raised when an operation stops because cancellation was requested.

    Deliberately not a subclass of any error condition that means "something
    went wrong". A cancelled operation is neither a success nor a failure - it
    is a third outcome, and reporting it as either misdescribes what happened:
    as success it claims work that was abandoned, as failure it blames the
    system for the operator's decision. PyThermX draws the same distinction
    with `TerminalOutcome.CANCELLED`.

    Attributes:
        operation: Which operation stopped - OP_BUNDLE, OP_EXTRACT, OP_VALIDATE.
        phase: The phase it was in when it noticed.
        completed: Units finished before stopping. Real work, not an estimate.
        total: Units planned, when that was known.
        partial_paths: Files already written, for callers that must report or
            clean up. Empty for operations that write nothing.
    """

    def __init__(self,
                 operation: str = "operation",
                 phase: str = "",
                 completed: float = 0,
                 total: Optional[float] = None,
                 partial_paths: Optional[list] = None) -> None:
        self.operation = operation
        self.phase = phase
        self.completed = completed
        self.total = total
        self.partial_paths = list(partial_paths or [])

        scope = f"{completed:g} of {total:g}" if total is not None else f"{completed:g}"
        detail = f" during {phase}" if phase else ""
        super().__init__(
            f"{operation} cancelled by request{detail} after {scope} units"
        )


def is_cancelled(cancel: Optional[CancelCheck]) -> bool:
    """Whether cancellation has been requested. Never raises.

    Args:
        cancel: The predicate, or None when the caller offered no way to cancel.

    Returns:
        True only when a working predicate says so. A None canceller, or one
        that raises, reports False - work continues rather than stopping for a
        reason nobody chose.
    """
    if cancel is None:
        return False
    try:
        return bool(cancel())
    except Exception:
        return False


def raise_if_cancelled(cancel: Optional[CancelCheck],
                       *,
                       operation: str = "operation",
                       phase: str = "",
                       completed: float = 0,
                       total: Optional[float] = None,
                       partial_paths: Optional[list] = None) -> None:
    """Stop the operation if cancellation has been requested.

    Call between units of work, never inside one. Stopping mid-file would leave
    a half-written artifact, which is a worse outcome than the extra moment
    spent finishing the unit in hand.

    Raises:
        OperationCancelled: carrying what had been completed when it stopped.
    """
    if is_cancelled(cancel):
        raise OperationCancelled(
            operation=operation, phase=phase, completed=completed,
            total=total, partial_paths=partial_paths,
        )


class CancelRecorder:
    """A test double that reports cancellation after N questions.

    Real cancellation arrives from a human at an unpredictable moment, which is
    exactly what a test cannot reproduce by hand. This makes the moment precise:
    `CancelRecorder(after=3)` cancels on the fourth poll, so a test can assert
    that work stopped at a known unit and that partial state is what it should
    be.
    """

    def __init__(self, after: int = 0) -> None:
        self.after = after
        self.calls = 0

    def __call__(self) -> bool:
        self.calls += 1
        return self.calls > self.after
