"""Native chooser and web process entry-point behavior."""

from __future__ import annotations

import json
import sys

import pytest

import web.dialog_helper as dialog_helper
import web_main


class FakeRoot:
    def __init__(self):
        self.withdrawn = False
        self.attributes_seen = []
        self.destroyed = False

    def withdraw(self):
        self.withdrawn = True

    def attributes(self, *args):
        self.attributes_seen.append(args)

    def destroy(self):
        self.destroyed = True


def test_initial_directory_uses_a_file_parent_and_climbs_missing_paths(tmp_path):
    existing = tmp_path / "folder"
    existing.mkdir()
    file_path = existing / "bundle.txt"
    file_path.write_text("x", encoding="utf-8")

    assert dialog_helper._initial_directory(str(file_path)) == str(existing)
    assert dialog_helper._initial_directory(str(existing / "missing" / "x")) == str(existing)
    assert dialog_helper._initial_directory("") == ""


def test_each_native_chooser_kind_is_owned_and_root_is_destroyed(monkeypatch, tmp_path):
    roots = []
    monkeypatch.setattr(dialog_helper.tk, "Tk", lambda: roots.append(FakeRoot()) or roots[-1])
    monkeypatch.setattr(dialog_helper.filedialog, "askdirectory", lambda **kwargs: "folder")
    monkeypatch.setattr(dialog_helper.filedialog, "askopenfilename", lambda **kwargs: "file")
    monkeypatch.setattr(dialog_helper.filedialog, "asksaveasfilename", lambda **kwargs: "save")

    assert dialog_helper.choose("folder", title="Folder", initial_path=str(tmp_path)) == "folder"
    assert dialog_helper.choose("file", title="File") == "file"
    assert dialog_helper.choose("save", title="Save", default_name="bundle.txt") == "save"
    with pytest.raises(ValueError, match="Unknown chooser"):
        dialog_helper.choose("other", title="Bad")

    assert all(root.withdrawn and root.destroyed for root in roots)
    assert all(("-topmost", True) in root.attributes_seen for root in roots)


def test_dialog_helper_main_emits_one_json_response(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["dialog_helper", "folder", "--title", "Pick"])
    monkeypatch.setattr(dialog_helper, "choose", lambda *args, **kwargs: "C:/picked")
    assert dialog_helper.main() == 0
    assert json.loads(capsys.readouterr().out) == {"path": "C:/picked"}


class FakeServer:
    session_url = "http://127.0.0.1:1234/session/test/"

    def __init__(self):
        self.served = False
        self.closed = False

    def serve_forever(self, poll_interval):
        assert poll_interval == 0.25
        self.served = True
        raise KeyboardInterrupt

    def server_close(self):
        self.closed = True


def test_web_main_prints_private_url_serves_and_closes(monkeypatch, capsys):
    server = FakeServer()
    monkeypatch.setattr(web_main, "create_server", lambda port: server)
    assert web_main.main(["--port", "1234", "--no-browser"]) == 0
    assert server.served and server.closed
    assert capsys.readouterr().out.strip() == server.session_url


def test_web_main_schedules_default_browser_open(monkeypatch):
    server = FakeServer()
    opened = []

    class ImmediateTimer:
        def __init__(self, delay, callback, args):
            assert delay == 0.25
            self.callback = callback
            self.args = args

        def start(self):
            self.callback(*self.args)

    monkeypatch.setattr(web_main, "create_server", lambda port: server)
    monkeypatch.setattr(web_main.threading, "Timer", ImmediateTimer)
    monkeypatch.setattr(web_main.webbrowser, "open", lambda url: opened.append(url))
    assert web_main.main([]) == 0
    assert opened == [server.session_url]
