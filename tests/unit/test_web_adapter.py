"""Web adapter parity over the renderer-independent service."""

from __future__ import annotations

from io import BytesIO
import time

import pytest

from core.exceptions import BundleFileToolError
from core.service import BundleToolService
from core.user_state import UserStateStore
from web.adapter import WebAdapter


def _wait(job, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        snapshot = job.snapshot()
        if snapshot["state"] in {"succeeded", "failed", "cancelled"}:
            return snapshot
        time.sleep(0.005)
    raise AssertionError("web adapter job did not finish")


def _adapter(tmp_path):
    return WebAdapter(
        BundleToolService(),
        state=UserStateStore(str(tmp_path / "user-state.json")))


def _project(tmp_path):
    root = tmp_path / "project"
    (root / "src").mkdir(parents=True)
    (root / "src" / "app.py").write_text("print('web')\n", encoding="utf-8")
    (root / "notes.log").write_text("noise\n", encoding="utf-8")
    return root


def test_bootstrap_exposes_service_profiles_and_safe_limits(tmp_path):
    adapter = _adapter(tmp_path)
    try:
        payload = adapter.bootstrap()
        assert payload["schema"] == "bft.web-bootstrap.v1"
        assert payload["local_only"] is True
        assert payload["default_profile"] in payload["profiles"]
        assert payload["limits"]["upload_bytes"] > 0
        assert payload["defaults"]["web_skin"] == "studio"
    finally:
        adapter.close()


def test_web_skin_is_validated_and_persisted(tmp_path):
    state_path = tmp_path / "user-state.json"
    adapter = WebAdapter(
        BundleToolService(), state=UserStateStore(str(state_path)))
    try:
        assert adapter.set_web_skin({"skin": "midnight"}) == {
            "skin": "midnight", "persisted": True}
        assert UserStateStore(str(state_path)).get("web_skin") == "midnight"
        assert adapter.bootstrap()["defaults"]["web_skin"] == "midnight"
        with pytest.raises(BundleFileToolError, match="studio.*midnight"):
            adapter.set_web_skin({"skin": "sepia"})
    finally:
        adapter.close()


def test_plan_and_replan_match_service_decisions(tmp_path):
    root = _project(tmp_path)
    direct = BundleToolService().plan_bundle([root], preset=[])
    adapter = _adapter(tmp_path)
    try:
        planned = _wait(adapter.submit("plan", {
            "source": str(root), "presets": []}))
        assert planned["state"] == "succeeded"
        web_plan = planned["result"]["plan"]
        assert web_plan["order"] == direct.plan.ordered_paths()
        assert web_plan["counts"] == direct.plan.counts()

        replanned = _wait(adapter.submit("replan", {
            "plan_id": web_plan["plan_id"],
            "overrides": [["exclude", "src/app.py"]],
        }))
        assert replanned["state"] == "succeeded"
        assert "src/app.py" not in replanned["result"]["plan"]["order"]
    finally:
        adapter.close()


def test_replan_can_protect_an_output_selected_after_initial_planning(tmp_path):
    root = _project(tmp_path)
    output = root / "existing-bundle.txt"
    output.write_text("old output\n", encoding="utf-8")
    adapter = _adapter(tmp_path)
    try:
        planned = _wait(adapter.submit("plan", {
            "source": str(root), "presets": []}))
        first = planned["result"]["plan"]
        assert first["output_path"] is None
        assert "existing-bundle.txt" in first["order"]

        replanned = _wait(adapter.submit("replan", {
            "plan_id": first["plan_id"],
            "overrides": [],
            "output_path": str(output),
        }))
        second = replanned["result"]["plan"]
        assert second["output_path"] == str(output)
        assert "existing-bundle.txt" not in second["order"]
        decision = next(
            item for item in second["decisions"]
            if item["path"] == "existing-bundle.txt"
        )
        assert decision["code"] == "BLOCKED_ACTIVE_OUTPUT"
    finally:
        adapter.close()


def test_create_checks_published_output_then_upload_check_and_extract(tmp_path):
    root = _project(tmp_path)
    output = tmp_path / "bundle.txt"
    adapter = _adapter(tmp_path)
    try:
        planned = _wait(adapter.submit("plan", {
            "source": str(root), "presets": [], "output_path": str(output)}))
        plan_id = planned["result"]["plan"]["plan_id"]
        created = _wait(adapter.submit("create", {
            "plan_id": plan_id,
            "output_path": str(output),
            "profile": "plain_marker",
        }))
        assert created["state"] == "succeeded"
        assert created["result"]["check"]["valid"] is True
        assert output.is_file()

        raw = output.read_bytes()
        upload = adapter.add_upload("roundtrip.txt", len(raw), BytesIO(raw))
        checked = _wait(adapter.submit("check-bundle", {
            "upload_id": upload.id, "profile": "plain_marker"}))
        assert checked["state"] == "succeeded"
        assert checked["result"]["check"]["valid"] is True
        assert {item["path"] for item in checked["result"]["entries"]} == {
            "src/app.py"}

        extracted_dir = tmp_path / "extracted"
        extracted = _wait(adapter.submit("extract", {
            "upload_id": upload.id,
            "output_dir": str(extracted_dir),
            "profile": "plain_marker",
            "overwrite_policy": "overwrite",
            "add_headers": False,
            "dry_run": False,
        }))
        assert extracted["state"] == "succeeded"
        assert (extracted_dir / "src" / "app.py").read_text(
            encoding="utf-8") == "print('web')\n"
        upload_path = upload.path
        assert adapter.remove_upload(upload.id) is True
        assert not upload_path.exists()
    finally:
        adapter.close()
