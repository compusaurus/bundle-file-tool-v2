"""Early GUI diagnostics for no-console desktop launchers."""

from __future__ import annotations

import os
import platform
import sys
import tempfile
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, TextIO

from core.user_state import UserStateStore

DIAGNOSTIC_ENV_VAR = "BFT_DIAGNOSTIC"


def startup_log_directory() -> Path:
    """Return the per-user startup-log directory with a temp fallback."""
    try:
        return UserStateStore.resolve_path().parent / "logs"
    except Exception:
        return Path(tempfile.gettempdir()) / "bundle_file_tool_logs"


class _Tee:
    """Small text stream that mirrors diagnostic output to valid targets."""

    def __init__(self, *targets: Optional[TextIO]) -> None:
        self.targets = tuple(target for target in targets if target is not None)
        self.encoding = "utf-8"

    def write(self, text: str) -> int:
        for target in self.targets:
            try:
                target.write(text)
            except Exception:
                pass
        return len(text)

    def flush(self) -> None:
        for target in self.targets:
            try:
                target.flush()
            except Exception:
                pass

    def isatty(self) -> bool:
        return False


class StartupSession:
    """Own redirected GUI streams for exactly one application process."""

    def __init__(self, log_path: Path, handle: TextIO, *, diagnostic: bool) -> None:
        self.log_path = log_path
        self._handle = handle
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        self.stdout = _Tee(
            self._original_stdout if diagnostic else None, handle)
        self.stderr = _Tee(
            self._original_stderr if diagnostic else None, handle)
        sys.stdout = self.stdout  # type: ignore[assignment]
        sys.stderr = self.stderr  # type: ignore[assignment]

    @property
    def original_stderr(self) -> Optional[TextIO]:
        return self._original_stderr

    def record_header(self) -> None:
        print("Bundle File Tool GUI startup")
        print(f"time_utc={datetime.now(timezone.utc).isoformat()}")
        print(f"python={sys.version.replace(chr(10), ' ')}")
        print(f"platform={platform.platform()}")
        print(f"executable={sys.executable}")
        print(f"working_directory={_safe_cwd()}")
        print(f"startup_log={self.log_path}")
        print("status=starting")
        self.stderr.flush()

    def record_ready(self) -> None:
        print("status=gui-created")
        self.stderr.flush()

    def record_exception(self, error: BaseException) -> None:
        print(
            f"status=startup-failed type={type(error).__name__} error={error}",
            file=sys.stderr)
        traceback.print_exception(
            type(error), error, error.__traceback__, file=sys.stderr)
        self.stderr.flush()

    def close(self) -> None:
        self.stderr.flush()
        if sys.stdout is self.stdout:
            sys.stdout = self._original_stdout
        if sys.stderr is self.stderr:
            sys.stderr = self._original_stderr
        try:
            self._handle.close()
        except Exception:
            pass


def begin_gui_startup(*, diagnostic: Optional[bool] = None) -> StartupSession:
    """Create the session log before importing or constructing Tk widgets."""
    if diagnostic is None:
        diagnostic = os.environ.get(DIAGNOSTIC_ENV_VAR) == "1"
    candidates = (startup_log_directory(),
                  Path(tempfile.gettempdir()) / "bundle_file_tool_logs")
    error: Optional[Exception] = None
    for directory in candidates:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            path = directory / f"startup_{stamp}_{os.getpid()}.log"
            handle = path.open("x", encoding="utf-8", newline="")
            session = StartupSession(path, handle, diagnostic=bool(diagnostic))
            session.record_header()
            return session
        except Exception as caught:
            error = caught
    raise RuntimeError(f"No writable startup log location is available: {error}")


def _safe_cwd() -> str:
    try:
        return str(Path.cwd())
    except Exception:
        return "<unavailable>"


__all__ = [
    "DIAGNOSTIC_ENV_VAR",
    "StartupSession",
    "begin_gui_startup",
    "startup_log_directory",
]
