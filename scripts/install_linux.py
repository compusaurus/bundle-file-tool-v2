"""Install a verified BFT source delivery and offline runtime on Linux."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys


def verify_payload(root: Path) -> list[Path]:
    manifest = root / "_delivery" / "delivery_manifest.sha256"
    files = []
    for line in manifest.read_text(encoding="utf-8-sig").splitlines():
        digest, name = line.split(" ", 1)
        relative = Path(name.strip().replace("\\", "/"))
        path = (root / relative).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError(f"Delivery path escapes its root: {name}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f"Delivery checksum mismatch: {name}")
        files.append(relative)
    if not files:
        raise ValueError("Delivery manifest is empty")
    return files


def install(source: Path, destination: Path) -> Path:
    if sys.platform != "linux" or not (3, 11) <= sys.version_info[:2] < (3, 14):
        raise RuntimeError("Linux installation requires Python 3.11, 3.12, or 3.13")
    # Check OS prerequisites before creating an installation.
    try:
        import tkinter  # noqa: F401
        import ensurepip  # noqa: F401
    except ImportError as exc:
        raise RuntimeError("Install python3-tk and python3-venv before running this installer") from exc

    files = verify_payload(source)
    manifest = source / "_delivery" / "delivery_manifest.sha256"
    identity = hashlib.sha256(manifest.read_bytes()).hexdigest()[:12]
    version = (source / "VERSION.txt").read_text().strip()
    if not all(c.isdigit() or c == "." for c in version):
        raise ValueError("Invalid delivery version")
    release = destination / "releases" / f"{version}-{identity}"
    if release.exists():
        verify_payload(release)
    else:
        release.mkdir(parents=True)
        for relative in files:
            target = release / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / relative, target)
        (release / "_delivery").mkdir()
        shutil.copy2(manifest, release / "_delivery" / manifest.name)
    runtime = release / ".venv" / "bin" / "python"
    if not runtime.exists():
        subprocess.run([sys.executable, "-m", "venv", str(release / ".venv")], check=True)
    wheels = sorted((release / "vendor" / "linux_bootstrap").glob("*.whl"))
    wheels += [release / "vendor" / "pythermx-0.5.3-py3-none-any.whl"]
    subprocess.run([str(runtime), "-m", "pip", "install", "--no-index",
                    "--disable-pip-version-check", *map(str, wheels)], check=True)
    subprocess.run([str(runtime), "-m", "pip", "install", "--no-index",
                    "--no-deps", "--no-build-isolation", "--disable-pip-version-check",
                    "-e", str(release)], check=True)
    subprocess.run([str(runtime), str(release / "src" / "cli.py"),
                    "--skip-splash", "--version"], check=True, cwd=release)
    (release / "bundle_config.json").chmod(0o444)
    current = destination / "current"
    if current.exists() and not current.is_symlink():
        raise RuntimeError(f"Refusing to replace a non-symlink: {current}")
    pending = destination / ".current-new"
    if pending.is_symlink():
        pending.unlink()
    pending.symlink_to(release, target_is_directory=True)
    pending.replace(current)

    bin_dir = Path.home() / ".local" / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    for name, entry in (("bft", "cli.py"), ("bft-gui", "main.py"), ("bft-web", "web_main.py")):
        launcher = bin_dir / name
        # Replace links themselves, never write through a link into an old venv.
        temporary = bin_dir / (name + ".new")
        temporary.write_text(
            "#!/bin/sh\nset -eu\n"
            + f"cd {shlex.quote(str(current))}\n"
            + f"exec {shlex.quote(str(current / '.venv/bin/python'))} -I "
            + f"{shlex.quote(str(current / 'src' / entry))} \"$@\"\n", encoding="utf-8")
        temporary.chmod(0o755)
        temporary.replace(launcher)
    applications = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "applications"
    applications.mkdir(parents=True, exist_ok=True)
    desktop = applications / "bundle-file-tool.desktop"
    executable = str(bin_dir / "bft-gui").replace("\\", "\\\\").replace('"', '\\"').replace("`", "\\`").replace("$", "\\$").replace("%", "%%")
    desktop.write_text(
        "[Desktop Entry]\nType=Application\nName=Bundle File Tool\n"
        "Comment=Create, inspect, and extract file bundles\n"
        f'Exec="{executable}"\n'
        f"Icon={current / 'src/ui/assets/bft-icon.png'}\n"
        "Terminal=false\nCategories=Development;Utility;\nStartupNotify=true\n", encoding="utf-8")
    desktop.chmod(0o755)
    print(json.dumps({"version": version, "installation": str(release),
                      "launcher": str(bin_dir / "bft-gui"), "desktop": str(desktop)}, indent=2))
    return release


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path,
                        default=Path.home() / ".local/share/bundle-file-tool")
    args = parser.parse_args()
    try:
        install(Path(__file__).resolve().parents[1], args.destination.expanduser().resolve())
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"BFT installation failed: {exc}\n")
