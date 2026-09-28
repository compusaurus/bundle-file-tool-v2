"""Non-blocking BFT-to-PyProjectMgr ConfigHub launch adapter."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


class ConfigHubLaunchError(RuntimeError):
    """Raised when the governed setup orchestrator cannot be located or started."""


@dataclass
class ConfigHubProcess:
    process: subprocess.Popen
    command: tuple[str, ...]
    diagnostic_path: Path | None = None


def launch_bft_config_hub(
    *,
    environment: Mapping[str, str] | None = None,
    target_monitor: tuple[int, int, int, int] | None = None,
) -> ConfigHubProcess:
    """Start a BFT-scoped ConfigHub session through PyProjectMgr."""

    env = dict(os.environ if environment is None else environment)
    env["BFT_PROJECT_ROOT"] = str(Path(__file__).resolve().parents[2])
    command, cwd = _resolve_command(env)
    scoped = (
        *command,
        "setup",
        "--application", "bft",
        "--application", "bft_pythermx",
        "--application", "pysplashx",
        "--requester", "bft",
    )
    if target_monitor is not None:
        left, top, right, bottom = target_monitor
        if right <= left or bottom <= top:
            raise ConfigHubLaunchError(
                "The invoking display work area has invalid dimensions"
            )
        scoped = (
            *scoped,
            f"--target-work-area={left},{top},{right},{bottom}",
        )
    diagnostic_path = _diagnostic_log_path(env)
    diagnostic_stream = None
    try:
        diagnostic_path.parent.mkdir(parents=True, exist_ok=True)
        diagnostic_stream = diagnostic_path.open("w", encoding="utf-8")
        launched_at = datetime.now(UTC).isoformat(timespec="seconds")
        diagnostic_stream.write(f"[{launched_at}] Launching governed BFT settings\n")
        diagnostic_stream.write(subprocess.list2cmdline(scoped) + "\n")
        diagnostic_stream.flush()
    except OSError:
        if diagnostic_stream is not None:
            diagnostic_stream.close()
            diagnostic_stream = None
        diagnostic_path = None

    creationflags = 0
    if os.name == "nt":
        creationflags = (
            getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            | getattr(subprocess, "CREATE_NO_WINDOW", 0)
        )
    try:
        popen_options = {
            "cwd": str(cwd) if cwd else None,
            "env": env,
            "close_fds": True,
            "creationflags": creationflags,
        }
        if diagnostic_stream is not None:
            popen_options.update(
                stdout=diagnostic_stream,
                stderr=subprocess.STDOUT,
            )
        process = subprocess.Popen(scoped, **popen_options)
    except OSError as exc:
        raise ConfigHubLaunchError(f"Could not start governed settings: {exc}") from exc
    finally:
        if diagnostic_stream is not None:
            diagnostic_stream.close()
    return ConfigHubProcess(
        process=process,
        command=tuple(scoped),
        diagnostic_path=diagnostic_path,
    )


def config_hub_startup_error(instance: ConfigHubProcess) -> str | None:
    """Describe an early ConfigHub exit, including its diagnostic tail."""

    return_code = instance.process.poll()
    if return_code is None:
        return None

    message = f"ConfigHub exited during startup with code {return_code}."
    diagnostic_path = instance.diagnostic_path
    if diagnostic_path is None:
        return message

    try:
        detail = diagnostic_path.read_text(encoding="utf-8", errors="replace")[-4000:].strip()
    except OSError:
        detail = ""
    if detail:
        message += f"\n\n{detail}"
    return f"{message}\n\nDiagnostic log: {diagnostic_path}"


def _resolve_command(environment: Mapping[str, str]) -> tuple[tuple[str, ...], Path | None]:
    explicit = environment.get("PYPROJECTMGR_EXECUTABLE", "").strip()
    if explicit:
        executable = Path(explicit).expanduser()
        if not executable.is_file():
            raise ConfigHubLaunchError(
                f"PYPROJECTMGR_EXECUTABLE does not name a file: {executable}"
            )
        return (str(executable),), executable.parent

    installed = shutil.which("pyprojmgr", path=environment.get("PATH"))
    if installed:
        return (installed,), None

    roots: list[Path] = []
    configured_root = environment.get("PYPROJECTMGR_PROJECT_ROOT", "").strip()
    if configured_root:
        roots.append(Path(configured_root).expanduser())

    # Developer-suite fallback.  It is used only when the governed environment
    # and installed console entry point are absent, and only if the exact
    # sibling project exists.
    try:
        python_workspace = Path(__file__).resolve().parents[4]
        roots.append(python_workspace / "pyprojectmgr_project" / "pyprojectmgrV2")
    except IndexError:
        pass
    roots.append(Path.home() / "Python" / "pyprojectmgr_project" / "pyprojectmgrV2")

    for root in roots:
        main = root / "main.py"
        if main.is_file():
            python = _python_for(root, environment)
            # Both projects have top-level `core` and `cli` packages. Isolate the
            # child from BFT's PYTHONPATH and user-site packages.
            base: tuple[str, ...] = (str(python), "-I", str(main), "--skip-splash")
            return base, root

    raise ConfigHubLaunchError(
        "PyProjectMgr is unavailable. Install its 'pyprojmgr' command, set "
        "PYPROJECTMGR_EXECUTABLE, or set PYPROJECTMGR_PROJECT_ROOT."
    )


def _runtime_startup_error(
    python: Path, project_root: Path, environment: Mapping[str, str] | None = None,
) -> str | None:
    """Probe ConfigHub's CLI imports before choosing an installed environment."""
    try:
        result = subprocess.run(
            [str(python), "-I", "-c",
             "import sys; sys.path.insert(0, 'src'); "
             "import tkinter; import cli.cli_interface; "
             "import configuration_hub.launcher; import pysplashx"],
            cwd=str(project_root),
            env=dict(environment) if environment is not None else None,
            capture_output=True, text=True, errors="replace", timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return str(exc)
    if result.returncode:
        detail = (result.stderr or result.stdout).strip().splitlines()
        return detail[-1] if detail else f"exit code {result.returncode}"
    return None


def _python_for(
    project_root: Path, environment: Mapping[str, str] | None = None,
) -> Path:
    candidates: Sequence[str] = (
        ("python.exe", "pythonw.exe") if os.name == "nt" else ("python",)
    )
    failures = []
    checked = set()
    for environment_name in (".venv311", ".venv312", ".venv313", ".venv"):
        scripts = project_root / environment_name / (
            "Scripts" if os.name == "nt" else "bin"
        )
        for name in candidates:
            path = scripts / name
            if path.is_file():
                error = _runtime_startup_error(path, project_root, environment)
                checked.add(path)
                if error is None:
                    return path
                failures.append(f"{path}: {error}")
                # pythonw shares the same environment as python; do not probe twice.
                break

    current = Path(sys.executable)
    if os.name == "nt" and current.name.casefold() == "pythonw.exe":
        console_python = current.with_name("python.exe")
        if console_python.is_file():
            current = console_python
    if current not in checked:
        error = _runtime_startup_error(current, project_root, environment)
        if error is None:
            return current
        failures.append(f"{current}: {error}")
    raise ConfigHubLaunchError(
        "No ready PyProjectMgr Python environment was found. Repair its runtime "
        "dependencies or set PYPROJECTMGR_EXECUTABLE to a working installation.\n\n"
        + "\n".join(failures)
    )


def _diagnostic_log_path(environment: Mapping[str, str]) -> Path:
    explicit = environment.get("BFT_CONFIG_HUB_LOG", "").strip()
    if explicit:
        return Path(explicit).expanduser()

    if environment.get("BFT_PORTABLE") == "1":
        return Path.cwd() / ".bft_config_hub_launch.log"

    if os.name == "nt":
        local_app_data = environment.get("LOCALAPPDATA", "").strip()
        base = (
            Path(local_app_data)
            if local_app_data
            else Path.home() / "AppData" / "Local"
        )
        return base / "BundleFileTool" / "config_hub_launch.log"

    xdg_config = environment.get("XDG_CONFIG_HOME", "").strip()
    base = Path(xdg_config) if xdg_config else Path.home() / ".config"
    return base / "bundle_file_tool" / "config_hub_launch.log"


__all__ = [
    "ConfigHubLaunchError",
    "ConfigHubProcess",
    "config_hub_startup_error",
    "launch_bft_config_hub",
]
