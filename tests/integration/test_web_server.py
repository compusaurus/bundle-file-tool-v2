"""HTTP, session security, and service wiring for the BFT web surface."""

from __future__ import annotations

import http.client
import json
import threading
import time

import pytest

from core.service import BundleToolService
from core.user_state import UserStateStore
from web.adapter import WebAdapter
from web.server import create_server


TOKEN = "test-session-token-0123456789abcdef"


@pytest.fixture
def web_server(tmp_path):
    adapter = WebAdapter(
        BundleToolService(),
        state=UserStateStore(str(tmp_path / "state.json")))
    server = create_server(token=TOKEN, adapter=adapter)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        thread.join(timeout=3)
        server.server_close()


def _call(server, method, relative, *, payload=None, token=TOKEN,
          origin=None, mutation=True):
    connection = http.client.HTTPConnection("127.0.0.1", server.port, timeout=20)
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {}
    if mutation:
        headers["X-BFT-Session"] = token
    if origin is not None:
        headers["Origin"] = origin
    if body is not None:
        headers["Content-Type"] = "application/json"
        headers["Content-Length"] = str(len(body))
    connection.request(method, f"/session/{token}/{relative}", body=body, headers=headers)
    response = connection.getresponse()
    raw = response.read()
    result = json.loads(raw) if raw else None
    headers_out = dict(response.getheaders())
    connection.close()
    return response.status, result, headers_out


def _job(server, job_id):
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        status, result, _headers = _call(
            server, "GET", f"api/jobs/{job_id}", mutation=False)
        assert status == 200
        if result["state"] in {"succeeded", "failed", "cancelled"}:
            return result
        time.sleep(0.01)
    raise AssertionError("HTTP job did not finish")


def test_browser_file_chooser_requires_authorized_session(web_server, tmp_path):
    (tmp_path / "Source folder").mkdir()
    status, result, _ = _call(web_server, "POST", "api/filesystem", payload={"path": str(tmp_path)})
    assert status == 200
    assert any(entry["name"] == "Source folder" and entry["directory"] for entry in result["entries"])
    status, _, _ = _call(web_server, "POST", "api/filesystem", payload={"path": str(tmp_path)}, mutation=False)
    assert status == 403
    status, _, _ = _call(web_server, "POST", "api/filesystem", payload={"path": str(tmp_path)}, origin="https://example.com")
    assert status == 403


def test_browser_file_chooser_reports_invalid_path(web_server, tmp_path):
    status, result, _ = _call(web_server, "POST", "api/filesystem", payload={"path": str(tmp_path / "missing")})
    assert status == 400
    assert "does not exist" in result["message"]


def test_static_shell_has_strict_headers_and_bootstrap(web_server):
    status, _result, headers = _call(
        web_server, "GET", "api/bootstrap", mutation=False)
    assert status == 200
    assert headers["Cache-Control"] == "no-store"
    assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]
    assert "media-src 'self'" in headers["Content-Security-Policy"]
    assert headers["X-Content-Type-Options"] == "nosniff"


def test_session_route_and_mutation_header_are_both_required(web_server):
    connection = http.client.HTTPConnection("127.0.0.1", web_server.port, timeout=20)
    connection.request("GET", "/session/wrong-token/api/bootstrap")
    assert connection.getresponse().status == 404
    connection.close()

    status, _result, _headers = _call(
        web_server, "POST", "api/jobs/plan",
        payload={"source": "missing"}, mutation=False)
    assert status == 403

    status, _result, _headers = _call(
        web_server, "POST", "api/jobs/plan",
        payload={"source": "missing"}, origin="http://attacker.invalid")
    assert status == 403


def test_http_plan_check_and_create_use_shared_service(web_server, tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "app.py").write_text("print(126)\n", encoding="utf-8")
    output = tmp_path / "created.txt"

    status, submitted, _headers = _call(web_server, "POST", "api/jobs/plan", payload={
        "source": str(root), "presets": [], "output_path": str(output)})
    assert status == 202
    planned = _job(web_server, submitted["id"])
    assert planned["state"] == "succeeded"
    plan = planned["result"]["plan"]
    assert plan["order"] == ["app.py"]

    status, submitted, _headers = _call(
        web_server, "POST", "api/jobs/check-selection",
        payload={"plan_id": plan["plan_id"], "profile": "plain_marker"})
    assert status == 202
    checked = _job(web_server, submitted["id"])
    assert checked["result"]["check"]["valid"] is True

    status, submitted, _headers = _call(
        web_server, "POST", "api/jobs/create", payload={
            "plan_id": plan["plan_id"], "output_path": str(output),
            "profile": "plain_marker"})
    assert status == 202
    created = _job(web_server, submitted["id"])
    assert created["state"] == "succeeded"
    assert created["result"]["check"]["subject"] == "output"
    assert output.is_file()


def test_native_chooser_response_is_structured(monkeypatch):
    class Completed:
        returncode = 0
        stdout = json.dumps({"path": "C:/chosen/project"})

    monkeypatch.setattr("web.server.subprocess.run", lambda *args, **kwargs: Completed())
    from web.server import BFTRequestHandler

    assert BFTRequestHandler._choose_path({
        "kind": "folder", "title": "Choose source"}) == {
            "path": "C:/chosen/project"}


def test_static_assets_head_missing_routes_and_job_errors(web_server):
    for asset in (
            "app.js", "nodethermx-web.js", "nodethermx-web.css",
            "bft-web-mark.png", "bft-web-icon.png", "pysplashx-splash.mjs",
            "pysplashx-splash.css",
            "crex_splash.mp4"):
        connection = http.client.HTTPConnection("127.0.0.1", web_server.port, timeout=20)
        connection.request("HEAD", f"/session/{TOKEN}/assets/{asset}")
        response = connection.getresponse()
        assert response.status == 200
        assert int(response.getheader("Content-Length")) > 0
        assert response.read() == b""
        connection.close()

    for relative in ("assets/missing.js", "api/jobs/not-a-job", "unknown"):
        status, result, _headers = _call(
            web_server, "GET", relative, mutation=False)
        assert status == 404
        assert result["error"] in {"not found", "job not found"}

    status, result, _headers = _call(
        web_server, "POST", "api/jobs/not-an-action", payload={})
    assert status == 400
    assert "Unknown web operation" in result["message"]

    status, result, _headers = _call(
        web_server, "POST", "api/jobs/no-job/cancel", payload={})
    assert status == 404
    assert result["error"] == "job not found"


def test_crex_video_supports_browser_byte_ranges(web_server):
    connection = http.client.HTTPConnection("127.0.0.1", web_server.port, timeout=20)
    connection.request(
        "GET", f"/session/{TOKEN}/assets/crex_splash.mp4",
        headers={"Range": "bytes=0-31"},
    )
    response = connection.getresponse()
    payload = response.read()
    assert response.status == 206
    assert response.getheader("Accept-Ranges") == "bytes"
    assert response.getheader("Content-Range") == "bytes 0-31/1892621"
    assert response.getheader("Content-Type") == "video/mp4"
    assert len(payload) == 32 and b"ftyp" in payload
    connection.close()

    connection = http.client.HTTPConnection("127.0.0.1", web_server.port, timeout=20)
    connection.request(
        "GET", f"/session/{TOKEN}/assets/crex_splash.mp4",
        headers={"Range": "bytes=9999999-"},
    )
    response = connection.getresponse()
    assert response.status == 416
    assert response.getheader("Content-Range") == "bytes */1892621"
    assert response.read() == b""
    connection.close()

def test_web_skin_preference_requires_session_and_persists(web_server):
    status, result, _headers = _call(
        web_server, "POST", "api/preferences/skin", payload={"skin": "midnight"})
    assert status == 200
    assert result == {"skin": "midnight", "persisted": True}

    status, bootstrap, _headers = _call(
        web_server, "GET", "api/bootstrap", mutation=False)
    assert status == 200
    assert bootstrap["defaults"]["web_skin"] == "midnight"

    status, _result, _headers = _call(
        web_server, "POST", "api/preferences/skin",
        payload={"skin": "studio"}, mutation=False)
    assert status == 403


def test_unexpected_host_and_invalid_json_fail_closed(web_server):
    connection = http.client.HTTPConnection("127.0.0.1", web_server.port, timeout=20)
    connection.putrequest("GET", f"/session/{TOKEN}/api/bootstrap", skip_host=True)
    connection.putheader("Host", "attacker.invalid")
    connection.endheaders()
    assert connection.getresponse().status == 404
    connection.close()

    connection = http.client.HTTPConnection("127.0.0.1", web_server.port, timeout=20)
    body = b"{not-json"
    connection.request(
        "POST", f"/session/{TOKEN}/api/jobs/plan", body=body,
        headers={"X-BFT-Session": TOKEN, "Content-Length": str(len(body))})
    response = connection.getresponse()
    payload = json.loads(response.read())
    assert response.status == 400
    assert payload["error"] == "INVALID_REQUEST"
    connection.close()


def test_raw_upload_can_be_checked_and_deleted(web_server, tmp_path):
    root = tmp_path / "upload-project"
    root.mkdir()
    (root / "file.py").write_text("x = 1\n", encoding="utf-8")
    bundle = BundleToolService().create_bundle(
        [root], base_path=root, profile="plain_marker").text.encode("utf-8")

    connection = http.client.HTTPConnection("127.0.0.1", web_server.port, timeout=20)
    connection.request(
        "POST", f"/session/{TOKEN}/api/uploads", body=bundle,
        headers={
            "X-BFT-Session": TOKEN,
            "X-BFT-Filename": "uploaded%20bundle.txt",
            "Content-Length": str(len(bundle)),
        })
    response = connection.getresponse()
    uploaded = json.loads(response.read())["upload"]
    assert response.status == 201
    assert uploaded["name"] == "uploaded bundle.txt"
    connection.close()

    status, submitted, _headers = _call(
        web_server, "POST", "api/jobs/check-bundle",
        payload={"upload_id": uploaded["id"], "profile": "plain_marker"})
    assert status == 202
    checked = _job(web_server, submitted["id"])
    assert checked["result"]["entries"][0]["path"] == "file.py"

    status, result, _headers = _call(
        web_server, "DELETE", f"api/uploads/{uploaded['id']}")
    assert status == 200 and result["removed"] is True
    status, result, _headers = _call(
        web_server, "DELETE", f"api/uploads/{uploaded['id']}")
    assert status == 404 and result["removed"] is False
