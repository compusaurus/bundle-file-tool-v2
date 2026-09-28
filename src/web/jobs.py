"""Cancellable background jobs for the local web adapter."""

from __future__ import annotations

import logging
import threading
import uuid
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from core.cancellation import OperationCancelled
from core.exceptions import BundleFileToolError
from core.progress import OperationProgress


LOGGER = logging.getLogger(__name__)
TERMINAL_STATES = {"succeeded", "failed", "cancelled"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class JobRecord:
    """Thread-safe state for one web-triggered service operation."""

    def __init__(self, action: str, *, max_events: int = 2048) -> None:
        self.id = uuid.uuid4().hex
        self.action = action
        self.state = "queued"
        self.created_at = _now()
        self.started_at: Optional[str] = None
        self.finished_at: Optional[str] = None
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[Dict[str, Any]] = None
        self._events: list[Dict[str, Any]] = []
        self._event_sequence = 0
        self._max_events = max_events
        self._cancel = threading.Event()
        self._lock = threading.RLock()

    def cancel_requested(self) -> bool:
        return self._cancel.is_set()

    def request_cancel(self) -> bool:
        with self._lock:
            if self.state in TERMINAL_STATES:
                return False
            self._cancel.set()
            return True

    def progress(self, event: OperationProgress) -> None:
        payload = event.to_dict()
        with self._lock:
            self._event_sequence += 1
            payload["sequence"] = self._event_sequence
            self._events.append(payload)
            if len(self._events) > self._max_events:
                del self._events[:len(self._events) - self._max_events]

    def mark_running(self) -> None:
        with self._lock:
            self.state = "running"
            self.started_at = _now()

    def mark_succeeded(self, result: Dict[str, Any]) -> None:
        with self._lock:
            self.result = result
            self.state = "succeeded"
            self.finished_at = _now()

    def mark_cancelled(self, error: OperationCancelled) -> None:
        with self._lock:
            self.error = {
                "code": "OPERATION_CANCELLED",
                "message": str(error),
                "operation": error.operation,
                "phase": error.phase,
                "completed": error.completed,
                "total": error.total,
                "partial_paths": list(error.partial_paths),
            }
            self.state = "cancelled"
            self.finished_at = _now()

    def mark_failed(self, code: str, message: str) -> None:
        with self._lock:
            self.error = {"code": code, "message": message}
            self.state = "failed"
            self.finished_at = _now()

    def snapshot(self, *, after: int = 0) -> Dict[str, Any]:
        with self._lock:
            events = [event for event in self._events
                      if int(event["sequence"]) > after]
            return {
                "schema": "bft.web-job.v1",
                "id": self.id,
                "action": self.action,
                "state": self.state,
                "cancel_requested": self._cancel.is_set(),
                "created_at": self.created_at,
                "started_at": self.started_at,
                "finished_at": self.finished_at,
                "next_after": self._event_sequence,
                "events": events,
                "result": self.result,
                "error": self.error,
            }


Work = Callable[[Callable[[], bool], Callable[[OperationProgress], None]], Dict[str, Any]]


class JobManager:
    """Bounded executor and process-local job registry."""

    def __init__(self, *, max_workers: int = 2, max_jobs: int = 64) -> None:
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="bft-web")
        self._max_jobs = max_jobs
        self._jobs: "OrderedDict[str, JobRecord]" = OrderedDict()
        self._lock = threading.RLock()
        self._closed = False

    def submit(self, action: str, work: Work) -> JobRecord:
        with self._lock:
            if self._closed:
                raise RuntimeError("web job manager is closed")
            self._prune_locked()
            job = JobRecord(action)
            self._jobs[job.id] = job
            self._executor.submit(self._run, job, work)
            return job

    @staticmethod
    def _run(job: JobRecord, work: Work) -> None:
        job.mark_running()
        try:
            result = work(job.cancel_requested, job.progress)
            if job.cancel_requested():
                raise OperationCancelled(operation=job.action)
            job.mark_succeeded(result)
        except OperationCancelled as error:
            job.mark_cancelled(error)
        except BundleFileToolError as error:
            job.mark_failed(type(error).__name__, str(error))
        except Exception:
            LOGGER.exception("Unexpected BFT web job failure")
            job.mark_failed("INTERNAL_OPERATION_ERROR",
                            "The operation failed unexpectedly. Review the BFT session log.")

    def get(self, job_id: str) -> Optional[JobRecord]:
        with self._lock:
            return self._jobs.get(job_id)

    def cancel(self, job_id: str) -> bool:
        job = self.get(job_id)
        return job.request_cancel() if job is not None else False

    def _prune_locked(self) -> None:
        while len(self._jobs) >= self._max_jobs:
            removable = next((job_id for job_id, job in self._jobs.items()
                              if job.state in TERMINAL_STATES), None)
            if removable is None:
                raise BundleFileToolError(
                    "Too many web operations are still active; wait or cancel one first.")
            self._jobs.pop(removable, None)

    def close(self) -> None:
        with self._lock:
            self._closed = True
            for job in self._jobs.values():
                job.request_cancel()
        self._executor.shutdown(wait=False, cancel_futures=True)
