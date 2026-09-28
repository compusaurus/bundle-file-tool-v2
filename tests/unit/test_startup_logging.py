"""No-console GUI launches retain early, discoverable diagnostics."""

from __future__ import annotations

import sys

from core import startup


def test_gui_startup_redirects_both_streams_to_one_session_log(
        tmp_path, monkeypatch):
    monkeypatch.setattr(startup, "startup_log_directory", lambda: tmp_path)
    original_stdout, original_stderr = sys.stdout, sys.stderr

    session = startup.begin_gui_startup(diagnostic=False)
    try:
        print("ordinary startup note")
        print("early startup warning", file=sys.stderr)
        session.record_ready()
        path = session.log_path
    finally:
        session.close()

    assert sys.stdout is original_stdout
    assert sys.stderr is original_stderr
    text = path.read_text(encoding="utf-8")
    assert "status=starting" in text
    assert "ordinary startup note" in text
    assert "early startup warning" in text
    assert "status=gui-created" in text


def test_startup_logs_live_beside_per_user_state(tmp_path, monkeypatch):
    state = tmp_path / "settings" / "user_state.json"
    monkeypatch.setattr(
        startup.UserStateStore, "resolve_path", staticmethod(lambda: state))
    assert startup.startup_log_directory() == state.parent / "logs"
