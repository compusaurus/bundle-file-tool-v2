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
    searched_dirs: list[Path] = []
    if not installed:
        # A macOS .app launched from Finder or the Dock inherits launchd's
        # minimal PATH (/usr/bin:/bin:/usr/sbin:/sbin), which hides a
        # pip-installed console script that resolves fine from Terminal. The
        # same installation therefore launches or fails depending only on how
        # it was started, so search the conventional locations directly.
        searched_dirs = _fallback_executable_dirs(environment)
        if searched_dirs:
            installed = shutil.which(
                "pyprojmgr",
                path=os.pathsep.join(str(each) for each in searched_dirs),
            )
    if installed:
        return (installed,), None

    roots: list[Path] = []
    configured_root = environment.get("PYPROJECTMGR_PROJECT_ROOT", "").strip()
    if configured_root:
        roots.append(Path(configured_root).expanduser())

    # Developer-suite fallback.  It is used only when the governed environment
    # and installed console entry point are absent, and only if the exact
    # sibling project exists.  Depth 4 mirrors the `%ROOT%\..\..` probe the
    # Windows installer performs; depth 3 covers a flatter checkout.
    for depth in (4, 3):
        try:
            python_workspace = Path(__file__).resolve().parents[depth]
        except IndexError:
            continue
        roots.append(python_workspace / "pyprojectmgr_project" / "pyprojectmgrV2")
    roots.append(_home(environment) / "Python" / "pyprojectmgr_project" / "pyprojectmgrV2")

    for root in roots:
        main = root / "main.py"
        if main.is_file():
            python = _python_for(root, environment)
            # Both projects have top-level `core` and `cli` packages. Isolate the
            # child from BFT's PYTHONPATH and user-site packages.
            base: tuple[str, ...] = (str(python), "-I", str(main), "--skip-splash")
            return base, root

    raise ConfigHubLaunchError(_unavailable_message(environment, searched_dirs, roots))


def _home(environment: Mapping[str, str]) -> Path:
    """The caller's home directory, honouring an explicitly supplied HOME."""

    configured = environment.get("HOME", "").strip()
    return Path(configured) if configured else Path.home()


def _fallback_executable_dirs(environment: Mapping[str, str]) -> list[Path]:
    """Where to look for 'pyprojmgr' when PATH does not carry it.

    Only consulted after a PATH lookup fails, so a normal Terminal or Windows
    launch keeps its existing behaviour untouched.
    """

    dirs: list[Path] = []

    def add(candidate: Path) -> None:
        if candidate not in dirs:
            dirs.append(candidate)

    # Alongside the interpreter running BFT, which covers `pyprojmgr`
    # installed into the same virtual environment.
    try:
        add(Path(sys.executable).resolve().parent)
    except OSError:
        pass
    if os.name == "nt":
        return dirs

    home = _home(environment)
    add(home / ".local" / "bin")
    add(Path("/usr/local/bin"))
    if sys.platform != "darwin":
        return dirs

    add(Path("/opt/homebrew/bin"))  # Apple-silicon Homebrew
    # `pip install --user` and the python.org framework builds place their
    # console scripts under a per-version directory, so enumerate what is
    # actually present rather than guessing version numbers.
    for base in (
        home / "Library" / "Python",
        Path("/Library/Frameworks/Python.framework/Versions"),
    ):
        try:
            versions = sorted(base.iterdir(), reverse=True)
        except OSError:
            continue
        for version in versions:
            add(version / "bin")
    return dirs


def _unavailable_message(
    environment: Mapping[str, str],
    searched_dirs: Sequence[Path],
    roots: Sequence[Path],
) -> str:
    """Explain what was searched, so the reader can act without guessing."""

    lines = [
        "PyProjectMgr is unavailable. Install its 'pyprojmgr' command, set "
        "PYPROJECTMGR_EXECUTABLE, or set PYPROJECTMGR_PROJECT_ROOT.",
        "",
        "Searched PATH for the 'pyprojmgr' command:",
        f"  {environment.get('PATH', '').strip() or '(unset)'}",
    ]
    if searched_dirs:
        lines.append("Also searched:")
        lines.extend(f"  {each}" for each in searched_dirs)
    if roots:
        lines.append("Searched for a PyProjectMgr checkout (main.py) in:")
        lines.extend(f"  {each}" for each in roots)
    return "\n".join(lines)


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
    # A POSIX virtual environment normally provides both names, but some
    # tools create only `python3`; probing just `python` missed those.
    candidates: Sequence[str] = (
        ("python.exe", "pythonw.exe") if os.name == "nt" else ("python", "python3")
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
