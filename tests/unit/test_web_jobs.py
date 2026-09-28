"""Background job contract for the local web adapter."""

from __future__ import annotations

import time

from core.cancellation import OperationCancelled
from core.exceptions import BundleFileToolError
from core.progress import OperationProgress
from web.jobs import JobManager


def _wait(job, timeout=2.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        snapshot = job.snapshot()
        if snapshot["state"] in {"succeeded", "failed", "cancelled"}:
            return snapshot
        time.sleep(0.005)
    raise AssertionError("web job did not finish")


def test_job_reports_progress_and_structured_result():
    manager = JobManager(max_workers=1)
    try:
        def work(_cancel, progress):
            progress(OperationProgress("bundle", "plan", 1, 2, "files", "one"))
            progress(OperationProgress("bundle", "plan", 2, 2, "files", "two"))
            return {"answer": 42}

        job = manager.submit("plan", work)
        result = _wait(job)

        assert result["schema"] == "bft.web-job.v1"
        assert result["state"] == "succeeded"
        assert result["result"] == {"answer": 42}
        assert [event["sequence"] for event in result["events"]] == [1, 2]
        assert job.snapshot(after=1)["events"][0]["message"] == "two"
    finally:
        manager.close()


def test_domain_failure_is_returned_without_traceback():
    manager = JobManager(max_workers=1)
    try:
        def work(_cancel, _progress):
            raise BundleFileToolError("safe explanation")

        result = _wait(manager.submit("plan", work))
        assert result["state"] == "failed"
        assert result["error"] == {
            "code": "BundleFileToolError", "message": "safe explanation"}
    finally:
        manager.close()


def test_cancel_request_reaches_cooperative_work():
    manager = JobManager(max_workers=1)
    try:
        def work(cancel, _progress):
            deadline = time.monotonic() + 1
            while time.monotonic() < deadline:
                if cancel():
                    raise OperationCancelled(operation="plan", phase="discover")
                time.sleep(0.005)
            return {"unexpected": True}

        job = manager.submit("plan", work)
        assert job.request_cancel() is True
        result = _wait(job)
        assert result["state"] == "cancelled"
        assert result["error"]["code"] == "OPERATION_CANCELLED"
    finally:
        manager.close()


def test_registry_prunes_old_terminal_jobs():
    manager = JobManager(max_workers=1, max_jobs=2)
    try:
        first = manager.submit("one", lambda _cancel, _progress: {"n": 1})
        _wait(first)
        second = manager.submit("two", lambda _cancel, _progress: {"n": 2})
        _wait(second)
        third = manager.submit("three", lambda _cancel, _progress: {"n": 3})
        _wait(third)
        assert manager.get(first.id) is None
        assert manager.get(second.id) is not None
        assert manager.get(third.id) is not None
    finally:
        manager.close()
