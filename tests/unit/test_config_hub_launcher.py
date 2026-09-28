"""BFT Settings-to-ConfigHub launch seam tests."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from ui import config_hub_launcher as launcher


def test_installed_launcher_requests_bft_and_its_splash_profile(monkeypatch, tmp_path):
    received = {}
    process = SimpleNamespace(poll=lambda: None)
    monkeypatch.setattr(launcher.shutil, "which", lambda *args, **kwargs: "C:/suite/pyprojmgr.exe")
    monkeypatch.setattr(
        launcher.subprocess,
        "Popen",
        lambda command, **kwargs: received.update(command=command, kwargs=kwargs) or process,
    )

    result = launcher.launch_bft_config_hub(
        environment={
            "PATH": "C:/suite",
            "BFT_CONFIG_HUB_LOG": str(tmp_path / "launch.log"),
        }
    )

    assert result.process is process
    assert tuple(received["command"][-9:]) == (
        "setup",
        "--application",
        "bft",
        "--application",
        "bft_pythermx",
        "--application",
        "pysplashx",
        "--requester",
        "bft",
    )
    assert received["kwargs"]["stderr"] is launcher.subprocess.STDOUT


def test_launch_passes_the_invoking_monitor_to_pyprojectmgr(monkeypatch, tmp_path):
    process = SimpleNamespace(poll=lambda: None)
    monkeypatch.setattr(launcher.shutil, "which", lambda *args, **kwargs: "pyprojmgr")
    monkeypatch.setattr(launcher.subprocess, "Popen", lambda *args, **kwargs: process)
    target = (-1920, 0, 0, 1040)

    result = launcher.launch_bft_config_hub(
        environment={"BFT_CONFIG_HUB_LOG": str(tmp_path / "launch.log")},
        target_monitor=target,
    )

    assert result.command[-1] == "--target-work-area=-1920,0,0,1040"


def test_launch_rejects_an_invalid_invoking_monitor(monkeypatch, tmp_path):
    monkeypatch.setattr(launcher.shutil, "which", lambda *args, **kwargs: "pyprojmgr")

    with pytest.raises(launcher.ConfigHubLaunchError, match="invalid dimensions"):
        launcher.launch_bft_config_hub(
            environment={"BFT_CONFIG_HUB_LOG": str(tmp_path / "launch.log")},
            target_monitor=(100, 0, 0, 1040),
        )


def test_windows_project_runtime_prefers_console_python(monkeypatch, tmp_path):
    scripts = tmp_path / ".venv311" / "Scripts"
    scripts.mkdir(parents=True)
    console = scripts / "python.exe"
    windowless = scripts / "pythonw.exe"
    console.touch()
    windowless.touch()
    monkeypatch.setattr(launcher.os, "name", "nt")
    monkeypatch.setattr(launcher, "_runtime_startup_error", lambda *args: None)

    assert launcher._python_for(tmp_path) == console


def test_incomplete_numbered_environment_does_not_hide_working_legacy_env(monkeypatch, tmp_path):
    for name in (".venv313", ".venv"):
        scripts = tmp_path / name / "Scripts"
        scripts.mkdir(parents=True)
        (scripts / "python.exe").touch()
    monkeypatch.setattr(launcher.os, "name", "nt")
    monkeypatch.setattr(launcher, "_runtime_startup_error", lambda path, *args:
                        "No module named 'click'" if ".venv313" in str(path) else None)
    assert launcher._python_for(tmp_path) == tmp_path / ".venv" / "Scripts" / "python.exe"


def test_no_ready_environment_reports_dependency_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(launcher, "_runtime_startup_error", lambda *args: "No module named 'click'")
    with pytest.raises(launcher.ConfigHubLaunchError, match="No module named 'click'"):
        launcher._python_for(tmp_path)


def test_early_exit_reports_diagnostic_tail(tmp_path):
    diagnostic = tmp_path / "launch.log"
    diagnostic.write_text("hidden startup failure", encoding="utf-8")
    instance = launcher.ConfigHubProcess(
        process=SimpleNamespace(poll=lambda: 1),
        command=("pyprojmgr", "setup"),
        diagnostic_path=diagnostic,
    )

    error = launcher.config_hub_startup_error(instance)

    assert "exited during startup with code 1" in error
    assert "hidden startup failure" in error
    assert str(diagnostic) in error


def test_bad_explicit_launcher_fails_without_falling_back(tmp_path):
    missing = tmp_path / "missing.exe"
    with pytest.raises(launcher.ConfigHubLaunchError, match="does not name a file"):
        launcher.launch_bft_config_hub(environment={"PYPROJECTMGR_EXECUTABLE": str(missing)})
