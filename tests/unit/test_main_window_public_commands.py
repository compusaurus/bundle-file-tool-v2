"""Public BFT menu commands must execute real behavior, never placeholders."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from ui import main_window
from ui.mode_manager import AppMode


class _ModeManager:
    def __init__(self, unbundle: bool = True):
        self.unbundle = unbundle
        self.changes = []

    def is_unbundle_mode(self):
        return self.unbundle

    def set_mode(self, mode):
        self.changes.append(mode)
        self.unbundle = mode is AppMode.UNBUNDLE


class _App:
    def __init__(self):
        self.mode_manager = _ModeManager(unbundle=False)
        self.unbundle_frame = SimpleNamespace(load_bundle_text=lambda *args, **kwargs: None)
        self.user_state = None
        self.config_manager = None
        self.statuses = []

    def after(self, _delay, callback):
        callback()

    def set_status(self, value):
        self.statuses.append(value)


def test_clipboard_unbundle_switches_mode_and_loads_text():
    app = _App()
    received = []
    app.clipboard_get = lambda: "bundle payload"
    app.unbundle_frame = SimpleNamespace(
        load_bundle_text=lambda text, **options: received.append((text, options))
    )

    main_window.BundleFileToolApp.menu_unbundle_clipboard(app)

    assert app.mode_manager.changes == [AppMode.UNBUNDLE]
    assert received == [("bundle payload", {"source_label": "Clipboard"})]


def test_validate_bundle_uses_the_shared_service(monkeypatch, tmp_path):
    app = _App()
    bundle = tmp_path / "bundle.txt"
    bundle.write_text("payload", encoding="utf-8")
    captured = []
    result = SimpleNamespace(
        valid=True,
        profile="plain_marker",
        file_count=3,
        warnings=[],
        errors=[],
    )
    service = SimpleNamespace(
        validate_bundle=lambda source, progress=None: captured.append(source) or result
    )
    monkeypatch.setattr(main_window.filedialog, "askopenfilename", lambda **_options: str(bundle))
    monkeypatch.setattr(main_window, "BundleToolService", lambda **_options: service)
    monkeypatch.setattr(
        main_window,
        "run_with_progress",
        lambda _parent, _title, work, **_options: work(progress=None, cancel=None),
    )
    reports = []
    monkeypatch.setattr(
        main_window.messagebox,
        "showinfo",
        lambda title, text, **_options: reports.append((title, text)),
    )

    main_window.BundleFileToolApp.menu_validate_bundle(app)

    assert captured == [bundle]
    assert "Status: VALID" in reports[0][1]
    assert app.statuses == ["Bundle is valid"]


def test_documentation_opens_the_installed_user_guide(monkeypatch, tmp_path):
    app = _App()
    guide = tmp_path / "USER_GUIDE.md"
    guide.write_text("guide", encoding="utf-8")
    monkeypatch.setattr(
        main_window.ConfigManager,
        "governed_config_path",
        staticmethod(lambda: tmp_path / "bundle_config.json"),
    )
    opened = []
    monkeypatch.setattr(
        main_window,
        "TextFileViewer",
        lambda parent, path, **options: opened.append((parent, path, options)),
    )

    main_window.BundleFileToolApp.show_documentation(app)

    assert opened == [(app, guide, {"title": "Bundle File Tool User Guide"})]


def test_log_command_resolves_relative_configured_directory(monkeypatch, tmp_path):
    app = _App()
    app.config_manager = SimpleNamespace(get=lambda *_args: "logs")
    monkeypatch.setattr(
        main_window.ConfigManager,
        "governed_config_path",
        staticmethod(lambda: tmp_path / "bundle_config.json"),
    )
    opened = []
    monkeypatch.setattr(
        main_window,
        "LogViewer",
        lambda parent, path: opened.append((parent, path)),
    )

    main_window.BundleFileToolApp.menu_view_logs(app)

    assert opened == [(app, tmp_path / "logs")]


def test_startup_log_command_opens_per_user_diagnostic_directory(
        monkeypatch, tmp_path):
    app = _App()
    opened = []
    monkeypatch.setattr(main_window, "startup_log_directory", lambda: tmp_path)
    monkeypatch.setattr(
        main_window, "LogViewer",
        lambda parent, path: opened.append((parent, path)))

    main_window.BundleFileToolApp.menu_view_startup_logs(app)

    assert opened == [(app, tmp_path)]


def test_ctrl_o_handler_dispatches_open_bundle():
    calls = []
    app = SimpleNamespace(menu_open_bundle=lambda: calls.append(True))

    assert main_window.BundleFileToolApp._open_bundle_shortcut(app) == "break"
    assert calls == [True]


def test_closing_while_minimized_preserves_last_visible_geometry(
        monkeypatch, tmp_path):
    from core.user_state import UserStateStore

    store = UserStateStore(str(tmp_path / "state.json"))
    store.set("last_non_minimized_geometry", "1200x800+30+40")
    store.set("last_non_minimized_state", "maximized")
    app = SimpleNamespace(
        user_state=store,
        _startup_effective_state="normal",
        state=lambda: "iconic",
        quit=lambda: None,
        destroy=lambda: None,
    )
    monkeypatch.setattr(
        main_window, "monitor_work_area_for_widget", lambda _window: None)

    main_window.BundleFileToolApp.on_close(app)

    reloaded = UserStateStore(str(tmp_path / "state.json"))
    assert reloaded.get("last_window_state") == "minimized"
    assert reloaded.get("last_non_minimized_state") == "maximized"
    assert reloaded.get("last_non_minimized_geometry") == "1200x800+30+40"
