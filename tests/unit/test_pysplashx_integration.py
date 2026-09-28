"""BFT's PySplashX process boundary, assets, and fail-open policy."""

from __future__ import annotations

import hashlib
import json
import subprocess
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from core import splash
import cli
from railgun_display import DisplayRect


ROOT = Path(__file__).resolve().parents[2]
WHEEL = ROOT / "vendor" / "pysplashx-0.1.0-py3-none-any.whl"


def test_crex_video_and_profile_are_packaged_with_exact_identity() -> None:
    assert splash.SPLASH_VIDEO.stat().st_size == 1_892_621
    assert hashlib.sha256(splash.SPLASH_VIDEO.read_bytes()).hexdigest() == (
        "e3dcaf85cd50ca520268c7247825a69527a698084239e45b2204f0aab2aa3eff"
    )
    profile = json.loads(splash.SPLASH_PROFILE_TEMPLATE.read_text(encoding="utf-8"))
    assert profile["profile_meta"]["schema_version"] == "2.2"
    assert profile["media"]["media_type"] == "video"
    assert profile["media"]["video"]["filename"] == "crex_splash.mp4"
    assert profile["media"]["video"]["loop_behavior"] == "close"
    assert profile["interfaces"] == {
        "native": {"enabled": True},
        "web": {"enabled": True},
    }


def test_governed_pysplashx_wheel_is_exact_and_declares_qt_dependency() -> None:
    assert hashlib.sha256(WHEEL.read_bytes()).hexdigest() == (
        "e07568eda58ca9f74f30149afcc18691f0bbf57095ac61a8aaac47bd6e6437bd"
    )
    with zipfile.ZipFile(WHEEL) as archive:
        metadata_name = next(name for name in archive.namelist() if name.endswith("METADATA"))
        metadata = archive.read(metadata_name).decode("utf-8")
    assert "Name: pysplashx" in metadata
    assert "Version: 0.1.0" in metadata
    assert "Requires-Dist: PySide6<7,>=6.8" in metadata


def test_disabled_splash_does_not_probe_or_start_runtime(monkeypatch) -> None:
    monkeypatch.setattr(
        splash,
        "_runtime_available",
        lambda: (_ for _ in ()).throw(AssertionError("runtime should not be probed")),
    )

    attempt = splash.run_startup_splash(environment={"BFT_SPLASH": "off"})

    assert attempt.status == "disabled"


def test_missing_optional_runtime_is_non_fatal(monkeypatch) -> None:
    monkeypatch.setattr(splash, "_runtime_available", lambda: False)

    attempt = splash.run_startup_splash(environment={})

    assert attempt.status == "unavailable"
    assert "not installed" in attempt.detail


def test_splash_uses_public_cli_in_an_isolated_process(monkeypatch, tmp_path) -> None:
    captured: dict[str, object] = {}
    monkeypatch.setattr(splash, "_runtime_available", lambda: True)
    monkeypatch.setattr(splash, "startup_log_directory", lambda: tmp_path / "logs")

    def runner(command, **options):
        profile_path = Path(command[-1])
        captured["command"] = list(command)
        captured["options"] = options
        captured["profile"] = json.loads(profile_path.read_text(encoding="utf-8"))
        return SimpleNamespace(returncode=0)

    attempt = splash.run_startup_splash(
        environment={"BFT_SPLASH": "1"}, runner=runner, timeout=9.5
    )

    assert attempt.completed
    assert captured["command"][1:4] == ["-m", "pysplashx", "run"]
    assert captured["options"] == {
        "check": False,
        "env": {"BFT_SPLASH": "1"},
        "timeout": 9.5,
    }
    profile = captured["profile"]
    assert profile["media"]["media_sources"] == [str(splash.SPLASH_VIDEO.parent.resolve()), str(splash.SPLASH_ASSET_ROOT.resolve())]
    assert profile["logging"]["log_file"] == str(tmp_path / "logs" / "pysplashx.log")


def test_native_splash_receives_the_resolved_application_display(monkeypatch, tmp_path):
    target = DisplayRect(1920, 0, 3840, 1040)
    captured = {}
    monkeypatch.setattr(splash, "_runtime_available", lambda: True)
    monkeypatch.setattr(splash, "startup_log_directory", lambda: tmp_path / "logs")

    def positioned(command, **options):
        captured["command"] = command
        captured.update(options)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(splash, "_run_positioned", positioned)

    attempt = splash.run_startup_splash(
        environment={"BFT_SPLASH": "1"},
        target_work_area=target,
        timeout=8.0,
    )

    assert attempt.completed
    assert captured["work_area"] == target
    assert captured["timeout"] == 8.0
    assert captured["environment"] == {"BFT_SPLASH": "1"}


def test_splash_timeout_and_child_failure_are_non_fatal(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(splash, "_runtime_available", lambda: True)
    monkeypatch.setattr(splash, "startup_log_directory", lambda: tmp_path / "logs")

    def timeout(*_args, **_kwargs):
        raise subprocess.TimeoutExpired("pysplashx", 1)

    timed_out = splash.run_startup_splash(environment={}, runner=timeout, timeout=1)
    failed = splash.run_startup_splash(
        environment={}, runner=lambda *_args, **_kwargs: SimpleNamespace(returncode=7)
    )

    assert timed_out.status == "failed"
    assert "TimeoutExpired" in timed_out.detail
    assert failed.status == "failed"
    assert "status 7" in failed.detail


def test_main_wires_splash_before_the_tk_entry_point() -> None:
    source = (ROOT / "src" / "main.py").read_text(encoding="utf-8")
    splash_call = source.index("splash_attempt = run_startup_splash(")
    gui_import = source.index("from ui.main_window import main as gui_main")

    assert splash_call < gui_import
    assert "resolve_application_launch(" in source
    assert "gui_main(launch_work_area=launch_work_area)" in source


def test_cli_runs_pysplashx_by_default_before_bundle_work(monkeypatch, tmp_path) -> None:
    calls: list[str] = []
    source = tmp_path / "source"
    source.mkdir()
    monkeypatch.setattr(cli, "run_startup_splash", lambda: calls.append("splash"))
    monkeypatch.setattr(cli, "handle_bundle", lambda _args: calls.append("bundle"))

    with pytest.raises(SystemExit) as exit_info:
        cli.main(["bundle", str(source)])

    assert exit_info.value.code == 0
    assert calls == ["splash", "bundle"]


def test_cli_skip_splash_bypasses_pysplashx(monkeypatch, tmp_path) -> None:
    calls: list[str] = []
    source = tmp_path / "source"
    source.mkdir()
    monkeypatch.setattr(
        cli,
        "run_startup_splash",
        lambda: (_ for _ in ()).throw(AssertionError("splash must be skipped")),
    )
    monkeypatch.setattr(cli, "handle_bundle", lambda _args: calls.append("bundle"))

    with pytest.raises(SystemExit) as exit_info:
        cli.main(["--skip-splash", "bundle", str(source)])

    assert exit_info.value.code == 0
    assert calls == ["bundle"]
