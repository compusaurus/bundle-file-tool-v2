"""The BFT File -> Settings command delegates only to the governed launcher."""

from __future__ import annotations

from types import SimpleNamespace

from ui import main_window
from ui.window_placement import WorkArea


class _FakeApp:
    config_hub_process = None

    def __init__(self):
        self.statuses = []
        self.callbacks = []

    def set_status(self, message):
        self.statuses.append(message)

    def after(self, _milliseconds, callback):
        self.callbacks.append(callback)

    def _check_config_hub_startup(self, instance, checks_remaining):
        main_window.BundleFileToolApp._check_config_hub_startup(
            self,
            instance,
            checks_remaining,
        )


def test_settings_starts_the_governed_config_hub(monkeypatch):
    app = _FakeApp()
    launched = SimpleNamespace(process=SimpleNamespace(poll=lambda: None))
    monkeypatch.setattr(main_window, "launch_bft_config_hub", lambda: launched)

    main_window.BundleFileToolApp.show_settings(app)

    assert app.config_hub_process is launched
    assert app.statuses == ["Opening governed settings in ConfigHub..."]
    assert len(app.callbacks) == 1


def test_settings_passes_the_current_display_to_config_hub(monkeypatch):
    app = _FakeApp()
    launched = SimpleNamespace(process=SimpleNamespace(poll=lambda: None))
    received = []
    area = WorkArea(-1920, 0, 0, 1040)
    monkeypatch.setattr(
        main_window,
        "monitor_work_area_for_widget",
        lambda _app: area,
    )
    monkeypatch.setattr(
        main_window,
        "launch_bft_config_hub",
        lambda *, target_monitor: received.append(target_monitor) or launched,
    )

    main_window.BundleFileToolApp.show_settings(app)

    assert received == [area.as_tuple()]


def test_settings_reports_success_after_the_startup_watch(monkeypatch):
    app = _FakeApp()
    launched = SimpleNamespace(process=SimpleNamespace(poll=lambda: None))
    monkeypatch.setattr(main_window, "launch_bft_config_hub", lambda: launched)
    monkeypatch.setattr(
        main_window,
        "config_hub_startup_error",
        lambda _instance: None,
    )

    main_window.BundleFileToolApp.show_settings(app)
    while app.callbacks:
        app.callbacks.pop(0)()

    assert app.statuses == [
        "Opening governed settings in ConfigHub...",
        "Opened governed settings in ConfigHub",
    ]


def test_settings_surfaces_an_early_child_process_failure(monkeypatch):
    app = _FakeApp()
    launched = SimpleNamespace(process=SimpleNamespace(poll=lambda: 1))
    errors = []
    monkeypatch.setattr(main_window, "launch_bft_config_hub", lambda: launched)
    monkeypatch.setattr(
        main_window,
        "config_hub_startup_error",
        lambda _instance: "ConfigHub startup exploded",
    )
    monkeypatch.setattr(
        main_window.messagebox,
        "showerror",
        lambda title, message, **_options: errors.append((title, message)),
    )

    main_window.BundleFileToolApp.show_settings(app)
    app.callbacks.pop()()

    assert app.config_hub_process is None
    assert app.statuses == [
        "Opening governed settings in ConfigHub...",
        "Could not open governed settings",
    ]
    assert errors == [
        ("Governed Settings failed to open", "ConfigHub startup exploded")
    ]


def test_settings_does_not_screen_scrape_or_relaunch_an_existing_config_hub(monkeypatch):
    app = _FakeApp()
    app.config_hub_process = SimpleNamespace(process=SimpleNamespace(poll=lambda: None))
    monkeypatch.setattr(
        main_window,
        "launch_bft_config_hub",
        lambda: (_ for _ in ()).throw(AssertionError("must not relaunch")),
    )

    main_window.BundleFileToolApp.show_settings(app)

    assert app.statuses == ["Governed Settings is already open"]
