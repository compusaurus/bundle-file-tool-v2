"""BFT Settings-to-ConfigHub launch seam tests."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from ui import config_hub_launcher as launcher

# launchd hands a Finder- or Dock-launched .app this PATH. A Terminal launch of
# the same installation inherits the full user PATH instead, which is why the
# identical build could work from one and fail from the other.
MINIMAL_MACOS_PATH = "/usr/bin:/bin:/usr/sbin:/sbin"


def _console_script(directory: Path, name: str = "pyprojmgr") -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    script = directory / name
    script.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    script.chmod(0o755)
    return script


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


def test_a_finder_launched_app_finds_a_user_installed_console_script(monkeypatch, tmp_path):
    """Regression: the Build 135 macOS .app reported PyProjectMgr unavailable.

    The app bundle exports PYTHONPATH but not PATH, so a Finder launch searched
    only launchd's minimal PATH and never saw a pip-installed console script.
    """

    script = _console_script(tmp_path / ".local" / "bin")
    monkeypatch.setattr(launcher.sys, "platform", "darwin")
    monkeypatch.setattr(launcher.os, "name", "posix")

    command, cwd = launcher._resolve_command(
        {"PATH": MINIMAL_MACOS_PATH, "HOME": str(tmp_path)}
    )

    assert command == (str(script),)
    assert cwd is None


def test_a_terminal_launch_still_resolves_from_path_first(monkeypatch, tmp_path):
    """The fallback must not change a launch that PATH already satisfies."""

    on_path = _console_script(tmp_path / "terminal" / "bin")
    _console_script(tmp_path / ".local" / "bin")
    monkeypatch.setattr(launcher.sys, "platform", "darwin")
    monkeypatch.setattr(launcher.os, "name", "posix")

    command, _cwd = launcher._resolve_command(
        {"PATH": str(on_path.parent), "HOME": str(tmp_path)}
    )

    assert command == (str(on_path),)


def test_an_explicit_executable_still_wins_over_the_fallback(monkeypatch, tmp_path):
    explicit = _console_script(tmp_path / "governed" / "bin", "pyprojmgr")
    _console_script(tmp_path / ".local" / "bin")
    monkeypatch.setattr(launcher.sys, "platform", "darwin")
    monkeypatch.setattr(launcher.os, "name", "posix")

    command, cwd = launcher._resolve_command(
        {
            "PYPROJECTMGR_EXECUTABLE": str(explicit),
            "PATH": MINIMAL_MACOS_PATH,
            "HOME": str(tmp_path),
        }
    )

    assert command == (str(explicit),)
    assert cwd == explicit.parent


def test_fallback_directories_cover_the_macos_console_script_locations(monkeypatch, tmp_path):
    monkeypatch.setattr(launcher.sys, "platform", "darwin")
    monkeypatch.setattr(launcher.os, "name", "posix")

    directories = launcher._fallback_executable_dirs({"HOME": str(tmp_path)})

    assert tmp_path / ".local" / "bin" in directories
    assert Path("/usr/local/bin") in directories
    assert Path("/opt/homebrew/bin") in directories
    assert Path(launcher.sys.executable).resolve().parent in directories


def test_fallback_directories_keep_macos_paths_off_other_platforms(monkeypatch, tmp_path):
    """Homebrew and framework locations are macOS-only and must not leak."""

    monkeypatch.setattr(launcher.sys, "platform", "linux")

    directories = launcher._fallback_executable_dirs({"HOME": str(tmp_path)})

    assert tmp_path / ".local" / "bin" in directories
    assert Path("/usr/local/bin") in directories
    assert Path("/opt/homebrew/bin") not in directories


def test_the_unavailable_message_names_everything_that_was_searched(monkeypatch, tmp_path):
    """The dialog has to say where it looked, or the reader can only guess."""

    monkeypatch.setattr(launcher.sys, "platform", "darwin")
    monkeypatch.setattr(launcher.os, "name", "posix")

    with pytest.raises(launcher.ConfigHubLaunchError) as failure:
        launcher._resolve_command({"PATH": MINIMAL_MACOS_PATH, "HOME": str(tmp_path)})

    message = str(failure.value)
    assert "PyProjectMgr is unavailable" in message
    assert MINIMAL_MACOS_PATH in message
    assert str(tmp_path / ".local" / "bin") in message
    assert "main.py" in message


def test_a_posix_environment_providing_only_python3_is_accepted(monkeypatch, tmp_path):
    monkeypatch.setattr(launcher.os, "name", "posix")
    monkeypatch.setattr(launcher, "_runtime_startup_error", lambda *args: None)
    binaries = tmp_path / ".venv313" / "bin"
    binaries.mkdir(parents=True)
    python3 = binaries / "python3"
    python3.write_text("", encoding="utf-8")

    assert launcher._python_for(tmp_path) == python3
