"""Dependency-free loopback HTTP shell for the BFT web adapter."""

from __future__ import annotations

import json
import mimetypes
import re
import secrets
import subprocess
import sys
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qs, unquote, urlsplit

from core.exceptions import BundleFileToolError
from core.service import BundleToolService
from web.adapter import MAX_JSON_BYTES, MAX_UPLOAD_BYTES, WebAdapter
from web.file_browser import browse_directory


LOOPBACK_HOST = "127.0.0.1"
SESSION_PREFIX = "/session/"
STATIC_ROOT = Path(__file__).resolve().parent / "static"
from core.splash import splash_media_path
WEB_SPLASH_VIDEO = Path(__file__).resolve().parents[1] / "ui" / "assets" / "videos" / "crex_splash.mp4"


class BFTWebServer(ThreadingHTTPServer):
    """HTTP server carrying the private per-run web session."""

    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, server_address, handler_class, *,
                 token: str, adapter: WebAdapter) -> None:
        self.session_token = token
        self.web_adapter = adapter
        self._adapter_closed = False
        super().__init__(server_address, handler_class)

    @property
    def port(self) -> int:
        return int(self.server_address[1])

    @property
    def origin(self) -> str:
        return f"http://{LOOPBACK_HOST}:{self.port}"

    @property
    def session_path(self) -> str:
        return f"{SESSION_PREFIX}{self.session_token}/"

    @property
    def session_url(self) -> str:
        return self.origin + self.session_path

    def server_close(self) -> None:
        if not self._adapter_closed:
            self._adapter_closed = True
            self.web_adapter.close()
        super().server_close()


class BFTRequestHandler(BaseHTTPRequestHandler):
    """Serve the web workspace without exposing a public network surface."""

    server: BFTWebServer
    protocol_version = "HTTP/1.1"

    def log_message(self, _format: str, *args: object) -> None:
        return

    def _security_headers(self, content_type: str) -> None:
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy",
                         "default-src 'self'; script-src 'self'; style-src 'self'; "
                         "img-src 'self' data:; media-src 'self'; connect-src 'self'; "
                         "object-src 'none'; base-uri 'none'; frame-ancestors 'none'; "
                         "form-action 'self'")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")

    def _send_bytes(self, status: HTTPStatus, payload: bytes,
                    content_type: str) -> None:
        self.send_response(status)
        self._security_headers(content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(payload)

    def _send_json(self, status: HTTPStatus, value: Any) -> None:
        payload = json.dumps(value, ensure_ascii=False,
                             separators=(",", ":")).encode("utf-8")
        self._send_bytes(status, payload, "application/json; charset=utf-8")

    def _valid_host(self) -> bool:
        return self.headers.get("Host", "") == f"{LOOPBACK_HOST}:{self.server.port}"

    def _valid_mutation(self) -> bool:
        if self.headers.get("X-BFT-Session", "") != self.server.session_token:
            return False
        origin = self.headers.get("Origin")
        if origin is not None and origin != self.server.origin:
            return False
        fetch_site = self.headers.get("Sec-Fetch-Site")
        return fetch_site in (None, "same-origin", "none")

    def _relative_session_path(self) -> Optional[str]:
        parsed = urlsplit(self.path)
        prefix = self.server.session_path
        if not parsed.path.startswith(prefix):
            return None
        return parsed.path[len(prefix):]

    def do_HEAD(self) -> None:
        self.do_GET()

    def do_GET(self) -> None:
        if not self._valid_host():
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        relative = self._relative_session_path()
        if relative is None:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        if relative in ("", "index.html"):
            self._serve_static("index.html")
            return
        if relative == "api/bootstrap":
            self._send_json(HTTPStatus.OK, self.server.web_adapter.bootstrap())
            return
        if relative.startswith("api/jobs/"):
            job_id = relative[len("api/jobs/"):].strip("/")
            job = self.server.web_adapter.jobs.get(job_id)
            if job is None:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "job not found"})
                return
            query = parse_qs(urlsplit(self.path).query)
            try:
                after = max(0, int(query.get("after", ["0"])[0]))
            except ValueError:
                after = 0
            self._send_json(HTTPStatus.OK, job.snapshot(after=after))
            return
        if relative.startswith("assets/"):
            self._serve_static(relative[len("assets/"):])
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:
        if not self._valid_host():
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        relative = self._relative_session_path()
        if relative is None:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        if not self._valid_mutation():
            self._send_json(HTTPStatus.FORBIDDEN, {"error": "session rejected"})
            return
        try:
            if relative == "api/filesystem":
                self._send_json(HTTPStatus.OK, browse_directory(self._read_json()))
                return
            if relative == "api/dialogs":
                payload = self._read_json()
                self._send_json(HTTPStatus.OK, self._choose_path(payload))
                return
            if relative == "api/preferences/skin":
                payload = self._read_json()
                self._send_json(
                    HTTPStatus.OK, self.server.web_adapter.set_web_skin(payload))
                return
            if relative.startswith("api/jobs/") and relative.endswith("/cancel"):
                job_id = relative[len("api/jobs/"):-len("/cancel")].strip("/")
                job = self.server.web_adapter.jobs.get(job_id)
                if job is None:
                    self._send_json(HTTPStatus.NOT_FOUND, {"error": "job not found"})
                    return
                accepted = job.request_cancel()
                self._send_json(HTTPStatus.ACCEPTED, {
                    "accepted": accepted,
                    "job": job.snapshot(),
                })
                return
            if relative.startswith("api/jobs/"):
                action = relative[len("api/jobs/"):].strip("/")
                payload = self._read_json()
                job = self.server.web_adapter.submit(action, payload)
                self._send_json(HTTPStatus.ACCEPTED, job.snapshot())
                return
            if relative == "api/uploads":
                length = self._content_length(MAX_UPLOAD_BYTES)
                encoded_name = self.headers.get("X-BFT-Filename", "bundle.txt")
                upload = self.server.web_adapter.add_upload(
                    unquote(encoded_name), length, self.rfile)
                self._send_json(HTTPStatus.CREATED, {"upload": upload.to_dict()})
                return
            if relative == "api/shutdown":
                self._send_json(HTTPStatus.ACCEPTED, {"stopping": True})
                threading.Thread(target=self.server.shutdown,
                                 name="bft-web-shutdown", daemon=True).start()
                return
        except BundleFileToolError as error:
            self._send_json(HTTPStatus.BAD_REQUEST, {
                "error": type(error).__name__, "message": str(error)})
            return
        except (ValueError, json.JSONDecodeError) as error:
            self._send_json(HTTPStatus.BAD_REQUEST, {
                "error": "INVALID_REQUEST", "message": str(error)})
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    @staticmethod
    def _choose_path(payload: Any) -> Dict[str, str]:
        if not isinstance(payload, dict):
            raise ValueError("The chooser request must be a JSON object.")
        kind = payload.get("kind")
        if kind not in {"folder", "file", "save"}:
            raise ValueError("Chooser kind must be folder, file, or save.")
        title = str(payload.get("title", "Select a path"))[:160]
        initial = str(payload.get("initial_path", ""))[:32768]
        default_name = str(payload.get("default_name", ""))[:255]
        command = [
            sys.executable, str(Path(__file__).resolve().parent / "dialog_helper.py"), kind,
            "--title", title, "--initial-path", initial,
            "--default-name", default_name,
        ]
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            completed = subprocess.run(
                command, check=False, capture_output=True, text=True,
                encoding="utf-8", timeout=600, creationflags=creationflags)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise BundleFileToolError(
                "The native path chooser could not be opened. You can still "
                "enter or paste an absolute local path.") from error
        if completed.returncode != 0:
            raise BundleFileToolError(
                "The native path chooser could not be opened. You can still "
                "enter or paste an absolute local path.")
        try:
            response = json.loads(completed.stdout.strip())
        except json.JSONDecodeError as error:
            raise BundleFileToolError(
                "The native path chooser returned an invalid response.") from error
        path = response.get("path", "")
        return {"path": path if isinstance(path, str) else ""}

    def do_DELETE(self) -> None:
        if not self._valid_host():
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        relative = self._relative_session_path()
        if relative is None or not self._valid_mutation():
            self._send_json(HTTPStatus.FORBIDDEN, {"error": "session rejected"})
            return
        if relative.startswith("api/uploads/"):
            upload_id = relative[len("api/uploads/"):].strip("/")
            removed = self.server.web_adapter.remove_upload(upload_id)
            self._send_json(HTTPStatus.OK if removed else HTTPStatus.NOT_FOUND,
                            {"removed": removed})
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def _content_length(self, maximum: int) -> int:
        raw = self.headers.get("Content-Length")
        if raw is None:
            raise ValueError("Content-Length is required.")
        try:
            length = int(raw)
        except ValueError as error:
            raise ValueError("Content-Length must be an integer.") from error
        if length < 0 or length > maximum:
            raise ValueError(f"Request body exceeds the {maximum}-byte limit.")
        return length

    def _read_json(self) -> Any:
        length = self._content_length(MAX_JSON_BYTES)
        body = self.rfile.read(length)
        if len(body) != length:
            raise ValueError("Request body ended before its declared size.")
        try:
            return json.loads(body.decode("utf-8"))
        except UnicodeDecodeError as error:
            raise ValueError("JSON requests must use UTF-8.") from error

    def _serve_static(self, name: str) -> None:
        allowed = {
            "index.html",
            "app.css",
            "app.js",
            "nodethermx-web.css",
            "nodethermx-web.js",
            "bft-web-mark.png",
            "bft-web-icon.png",
            "pysplashx-splash.mjs",
            "pysplashx-splash.css",
            "crex_splash.mp4",
            "splash-media",
            "splash-mask",
        }
        if name not in allowed:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        try:
            path = (splash_media_path(mask=name == 'splash-mask')
                    if name in {'splash-media', 'splash-mask'} else
                    WEB_SPLASH_VIDEO if name == "crex_splash.mp4" else STATIC_ROOT / name)
            payload = path.read_bytes()
        except (OSError, ValueError, KeyError, TypeError):
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type in {
                "application/javascript", "application/json"}:
            content_type += "; charset=utf-8"
        if content_type.startswith('video/'):
            self._send_media_bytes(payload, content_type)
        else:
            self._send_bytes(HTTPStatus.OK, payload, content_type)

    def _send_media_bytes(self, payload: bytes, content_type: str) -> None:
        """Serve one local video with single-range support for browser seeking."""
        size = len(payload)
        requested = self.headers.get("Range")
        if requested is None:
            self.send_response(HTTPStatus.OK)
            self._security_headers(content_type)
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(size))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(payload)
            return

        match = re.fullmatch(r"bytes=(\d*)-(\d*)", requested.strip())
        try:
            if match is None or (not match.group(1) and not match.group(2)):
                raise ValueError
            if match.group(1):
                start = int(match.group(1))
                end = int(match.group(2)) if match.group(2) else size - 1
            else:
                suffix = int(match.group(2))
                if suffix <= 0:
                    raise ValueError
                start = max(0, size - suffix)
                end = size - 1
            if start < 0 or start >= size or end < start:
                raise ValueError
            end = min(end, size - 1)
        except ValueError:
            self.send_response(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
            self._security_headers(content_type)
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Range", f"bytes */{size}")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        selected = payload[start:end + 1]
        self.send_response(HTTPStatus.PARTIAL_CONTENT)
        self._security_headers(content_type)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(len(selected)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(selected)


def create_server(*, port: int = 0, token: Optional[str] = None,
                  service: Optional[BundleToolService] = None,
                  adapter: Optional[WebAdapter] = None) -> BFTWebServer:
    """Create a server that can only bind to the IPv4 loopback interface."""
    if not isinstance(port, int) or not 0 <= port <= 65535:
        raise ValueError("port must be an integer from 0 through 65535")
    session_token = token or secrets.token_urlsafe(32)
    if len(session_token) < 24:
        raise ValueError("session token must contain at least 24 characters")
    if adapter is not None and service is not None:
        raise ValueError("pass either service or adapter, not both")
    web_adapter = adapter or WebAdapter(service or BundleToolService())
    return BFTWebServer(
        (LOOPBACK_HOST, port), BFTRequestHandler,
        token=session_token, adapter=web_adapter)
