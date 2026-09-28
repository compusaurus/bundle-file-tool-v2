"""Fail-open PySplashX startup integration for the native BFT host."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.startup import startup_log_directory
from railgun_display import (
    ActiveDisplayResolver,
    DisplayRect,
    create_display_driver,
    place_process_tree_windows,
)


SPLASH_ENABLED_ENV = "BFT_SPLASH"
SPLASH_TIMEOUT_SECONDS = 20.0
SPLASH_ASSET_ROOT = Path(__file__).resolve().parents[1] / "ui" / "assets"
SPLASH_PROFILE_TEMPLATE = SPLASH_ASSET_ROOT / "pysplashx_profile.json"
SPLASH_VIDEO = SPLASH_ASSET_ROOT / "videos" / "crex_splash.mp4"


@dataclass(frozen=True)
class SplashAttempt:
    """Observable result of one optional startup-splash attempt."""

    status: str
    detail: str = ""

    @property
    def completed(self) -> bool:
        return self.status == "completed"


def _splash_enabled(environment: Mapping[str, str]) -> bool:
    value = environment.get(SPLASH_ENABLED_ENV, "1").strip().lower()
    return value not in {"0", "false", "no", "off"}


def _runtime_available() -> bool:
    """Check both packages without importing Qt into BFT's Tk process."""

    return (
        importlib.util.find_spec("pysplashx") is not None
        and importlib.util.find_spec("PySide6") is not None
    )


def _runtime_profile(destination: Path) -> Path:
    """Write a temporary, relocation-safe profile for the packaged video."""

    profile = read_splash_profile()
    profile["media"]["media_sources"] = [str(_profile_path(source))
                                          for source in profile["media"]["media_sources"]]
    mask = profile["geometry"]["mask_settings"]["mask_path"]
    if mask:
        profile["geometry"]["mask_settings"]["mask_path"] = str(_profile_path(mask))
    log_directory = startup_log_directory()
    log_directory.mkdir(parents=True, exist_ok=True)
    log_path = Path(profile["logging"]["log_file"]).expanduser()
    if not log_path.is_absolute():
        log_path = log_directory / log_path
    log_path.parent.mkdir(parents=True, exist_ok=True)
    profile["logging"]["log_file"] = str(log_path)
    destination.write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")
    return destination


def read_splash_profile() -> dict:
    return json.loads(SPLASH_PROFILE_TEMPLATE.read_text(encoding="utf-8"))


def _profile_path(value: str) -> Path:
    path = Path(value).expanduser()
    return (path if path.is_absolute() else SPLASH_PROFILE_TEMPLATE.parent / path).resolve()


def splash_media_path(*, mask: bool = False) -> Path:
    """Resolve only the explicitly selected media, never a browser-supplied path."""
    profile = read_splash_profile()
    if mask:
        value = profile['geometry']['mask_settings']['mask_path']
        if not value:
            raise FileNotFoundError('No splash mask configured')
        return _profile_path(value)
    media = profile['media']
    filename = Path(media[media['media_type']]['filename']).expanduser()
    if filename.is_absolute() and filename.is_file():
        return filename
    for source in media['media_sources']:
        candidate = _profile_path(source) / filename
        if candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError(f'Configured splash media is missing: {filename}')


def web_splash_settings() -> dict:
    """Public component attributes derived from the same profile as native BFT."""
    try:
        profile = read_splash_profile()
        media, geometry = profile['media'], profile['geometry']
        splash_media_path()
        enabled = bool(profile['enabled'] and profile['interfaces']['web']['enabled'])
        return {
            'enabled': 'true' if enabled else 'false',
            'src': 'assets/splash-media',
            'media-type': media['media_type'],
            'shape': geometry['shape'],
            'scale-percent': geometry['scale_percent'],
            'radius-px': geometry['rounded_corners']['radius_px'],
            'mask-src': 'assets/splash-mask' if geometry['shape'] == 'png_mask' else '',
            'mask-threshold': geometry['mask_settings']['mask_threshold'],
            'aspect-ratio-mode': media['video']['aspect_ratio_mode'],
            'start-pos-ms': media['video']['temporal']['start_pos_ms'],
            'end-pos-ms': media['video']['temporal']['end_pos_ms'],
            'loop-behavior': media['video']['loop_behavior'],
            'static-duration-ms': media['image']['static_duration_ms'],
            'close-on-click': str(profile['runtime_behavior']['close_on_click']).lower(),
            'max-duration-ms': int(SPLASH_TIMEOUT_SECONDS * 1000),
        }
    except (OSError, ValueError, KeyError, TypeError) as error:
        return {'enabled': 'false', 'error': f'Splash unavailable: {error}'}


def _active_work_area() -> DisplayRect | None:
    """Resolve one attention-aware target without making splash availability fatal."""

    driver = create_display_driver()
    if driver is None:
        return None
    try:
        target = ActiveDisplayResolver(driver).resolve()
    except (AttributeError, OSError, TypeError, ValueError):
        return None
    return target.work_area if target is not None else None


def _run_positioned(
    command: list[str],
    *,
    environment: Mapping[str, str],
    timeout: float,
    work_area: DisplayRect | None,
) -> subprocess.CompletedProcess[Any]:
    """Run a native splash while keeping its process windows on one display."""

    process = subprocess.Popen(command, env=dict(environment))
    stopped = threading.Event()

    def synchronize() -> None:
        while not stopped.is_set():
            if work_area is not None:
                try:
                    place_process_tree_windows(process.pid, work_area)
                except (AttributeError, OSError, TypeError, ValueError):
                    pass
            stopped.wait(0.04)

    synchronizer = threading.Thread(
        target=synchronize,
        name="bft-splash-display-sync",
        daemon=True,
    )
    synchronizer.start()
    try:
        return_code = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.terminate()
        try:
            process.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        raise
    finally:
        stopped.set()
        synchronizer.join(timeout=0.25)
    return subprocess.CompletedProcess(command, return_code)


def run_startup_splash(
    *,
    environment: Mapping[str, str] | None = None,
    runner: Callable[..., Any] | None = None,
    timeout: float = SPLASH_TIMEOUT_SECONDS,
    target_work_area: DisplayRect | None = None,
) -> SplashAttempt:
    """Play the Crex splash in an isolated PySplashX process.

    PySplashX uses Qt Multimedia while BFT uses Tkinter.  The process boundary
    is PySplashX's supported Tk-host pattern and prevents the two GUI event
    loops from sharing one process.  Branding is intentionally fail-open: a
    missing dependency, damaged asset, playback error, or timeout never blocks
    BFT from opening.
    """

    configured_environment = dict(os.environ if environment is None else environment)
    if not _splash_enabled(configured_environment):
        return SplashAttempt("disabled", f"{SPLASH_ENABLED_ENV}=0")
    try:
        profile = read_splash_profile()
        if not profile['enabled'] or not profile['interfaces']['native']['enabled']:
            return SplashAttempt('disabled', 'Disabled in the BFT splash profile')
        splash_media_path()
    except (OSError, ValueError, KeyError, TypeError) as error:
        return SplashAttempt('unavailable', str(error))
    if not _runtime_available():
        return SplashAttempt("unavailable", "PySplashX or PySide6 is not installed")

    work_area = target_work_area or _active_work_area()

    try:
        with tempfile.TemporaryDirectory(prefix="bft-pysplashx-") as scratch:
            profile_path = _runtime_profile(Path(scratch) / "pysplashx_profile.json")
            command = [sys.executable, "-m", "pysplashx", "run", str(profile_path)]
            if runner is None:
                completed = _run_positioned(
                    command,
                    environment=configured_environment,
                    timeout=timeout,
                    work_area=work_area,
                )
            else:
                completed = runner(
                    command,
                    check=False,
                    env=configured_environment,
                    timeout=timeout,
                )
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
        return SplashAttempt("failed", f"{type(error).__name__}: {error}")

    return_code = int(getattr(completed, "returncode", 1))
    if return_code != 0:
        return SplashAttempt("failed", f"PySplashX exited with status {return_code}")
    return SplashAttempt("completed")


__all__ = [
    "SPLASH_ASSET_ROOT",
    "SPLASH_ENABLED_ENV",
    "SPLASH_PROFILE_TEMPLATE",
    "SPLASH_TIMEOUT_SECONDS",
    "SPLASH_VIDEO",
    "SplashAttempt",
    "run_startup_splash",
]
