"""Verified BFT installation into a new folder or an existing installation.

Requires CPython 3.11-3.13 with Tk and venv. Runtime dependencies are bundled.
No arguments opens the installer window; explicit arguments support automation.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import queue
import shutil
import stat
import subprocess
import sys
import threading
import uuid


MANIFEST = Path("_delivery/delivery_manifest.sha256")
RUNTIME_POINTER = Path(".bft-runtime.txt")
RECEIPT = Path(".bft-install.json")


def payload_files(source: Path) -> list[Path]:
    """Reject missing, corrupt, duplicate, linked or escaping payload entries."""
    files: list[Path] = []
    seen: set[str] = set()
    for line in (source / MANIFEST).read_text(encoding="utf-8-sig").splitlines():
        digest, name = line.split(" ", 1)
        name = name.strip().replace("\\", "/")
        relative = Path(name)
        if (relative.is_absolute() or PureWindowsPath(name).drive
                or any(part in {"..", ".git", ".bft-venvs", ".bft-backups"} for part in relative.parts)
                or ":" in name or name.casefold() in seen):
            raise ValueError(f"Invalid or duplicate delivery path: {name}")
        path = source / relative
        if not path.resolve().is_relative_to(source.resolve()) or linked(path, source):
            raise ValueError(f"Linked or escaping delivery path: {name}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f"Delivery checksum mismatch: {name}")
        seen.add(name.casefold())
        files.append(relative)
    required = {"src/main.py", "src/cli.py", "VERSION.txt", "bundle_config.json",
                ".pyprojectmgr/project_manifest.json", "pyproject.toml"}
    if not required.issubset({p.as_posix() for p in files}):
        raise ValueError("Incomplete BFT delivery manifest")
    return files


def linked(path: Path, boundary: Path) -> bool:
    for candidate in (path, *path.parents):
        if candidate.is_symlink() or getattr(candidate, "is_junction", lambda: False)():
            return True
        if candidate == boundary:
            break
    return False


def check_destination(source: Path, destination: Path, files: list[Path], mode: str,
                      replace_settings: bool) -> None:
    if mode not in {"fresh", "upgrade"}:
        raise ValueError("Choose fresh or upgrade installation")
    if destination == Path(destination.anchor) or destination == Path.home().resolve():
        raise ValueError("Choose a dedicated BFT installation folder")
    if source.is_relative_to(destination) or destination.is_relative_to(source):
        raise ValueError("The installation folder must be separate from the delivery folder")
    if destination.exists() and not destination.is_dir():
        raise ValueError("The installation destination is not a folder")
    if mode == "fresh":
        if destination.exists() and any(destination.iterdir()):
            raise ValueError("Fresh installation requires a new or empty folder")
    else:
        if not all((destination / p).is_file() for p in
                   ("src/main.py", "VERSION.txt", "bundle_config.json", ".pyprojectmgr/project_manifest.json")):
            raise ValueError("Upgrade requires an existing BFT installation folder")
        current = json.loads((destination / "bundle_config.json").read_text(encoding="utf-8-sig"))
        incoming = json.loads((source / "bundle_config.json").read_text(encoding="utf-8-sig"))
        current.pop("version", None)
        incoming.pop("version", None)
        if current != incoming and not replace_settings:
            raise ValueError("Governed settings differ. Review them first, then select Use delivered "
                             "governed settings or pass --replace-settings to back up and replace them.")
        old = tuple(map(int, (destination / "VERSION.txt").read_text().strip().split(".")))
        new = tuple(map(int, (source / "VERSION.txt").read_text().strip().split(".")))
        if old > new:
            raise ValueError("This delivery cannot downgrade a newer installation")
    for relative in [*files, MANIFEST, RUNTIME_POINTER, RECEIPT,
                     Path(".bft-venvs"), Path(".bft-backups")]:
        target = destination / relative
        if linked(target, destination) or not target.resolve().is_relative_to(destination):
            raise ValueError(f"Refusing linked destination path: {relative}")
        if relative in files and target.exists() and not target.is_file():
            raise ValueError(f"A folder occupies a delivery file path: {relative}")
    if mode == "upgrade" and not replace_settings:
        prior_hashes = {}
        if (destination / MANIFEST).is_file():
            for line in (destination / MANIFEST).read_text(encoding="utf-8-sig").splitlines():
                digest, name = line.split(" ", 1)
                prior_hashes[name.strip().replace("\\", "/")] = digest
        for name in ("config/pythermx_profile.json", "src/ui/assets/pysplashx_profile.json"):
            current_profile, incoming_profile = destination / name, source / name
            if Path(name) not in files or not current_profile.is_file():
                continue
            current_bytes = current_profile.read_bytes()
            if (current_bytes != incoming_profile.read_bytes()
                    and hashlib.sha256(current_bytes).hexdigest() != prior_hashes.get(name)):
                raise ValueError(f"Customized settings profile differs: {name}. Review it first, then "
                                 "select Use delivered governed settings or pass --replace-settings "
                                 "to back up and replace it.")


def run(command: list[str], *, cwd: Path | None = None) -> None:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, errors="replace",
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}): {command[0]}\n"
                           + (result.stdout + result.stderr)[-6000:])


def prepare_runtime(source: Path, destination: Path, runtime_dir: Path, report=print) -> Path:
    report("Creating an isolated Python environment...")
    run([sys.executable, "-m", "venv", str(runtime_dir)])
    python = runtime_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    wheels = sorted((source / "vendor/linux_bootstrap").glob("*.whl"))
    wheels += [source / "vendor/pythermx-0.5.3-py3-none-any.whl"]
    report("Installing bundled runtime dependencies...")
    run([str(python), "-m", "pip", "install", "--no-index", "--disable-pip-version-check",
         *map(str, wheels)])
    # Editable registration keeps the program's governed root at destination.
    run([str(python), "-m", "pip", "install", "--no-index", "--no-deps",
         "--no-build-isolation", "--disable-pip-version-check", "-e", str(destination)])
    return python


def validate_runtime(python: Path, destination: Path) -> None:
    run([str(python), "-I", str(destination / "src/cli.py"), "--skip-splash", "--version"], cwd=destination)
    run([str(python), "-I", "-c", "import tkinter as tk; import pythermx; "
         "from core.service import BundleToolService; service=BundleToolService(); "
         "from ui.selection_workspace import SelectionWorkspaceFrame; "
         "root=tk.Tk(); root.withdraw(); root.update(); root.destroy()"], cwd=destination)


def copy_file(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.chmod(target.stat().st_mode | stat.S_IWUSR)
    shutil.copy2(source, target)


def install(source: Path, destination: Path, mode: str, *, replace_settings=False,
            shortcuts=False, report=print) -> dict:
    if not (3, 11) <= sys.version_info[:2] < (3, 14):
        raise RuntimeError("Installation requires Python 3.11, 3.12, or 3.13 with Tk and venv")
    import tkinter  # noqa: F401
    import ensurepip  # noqa: F401

    source = source.expanduser().resolve()
    # Canonicalize trusted OS aliases (for example /var on macOS). Refuse a
    # selected destination that is itself a link, and all links below it.
    destination = destination.expanduser().absolute()
    if destination.is_symlink() or getattr(destination, "is_junction", lambda: False)():
        raise ValueError("The selected installation folder cannot be a link")
    destination = destination.resolve()
    report("Verifying delivery checksums and destination...")
    files = payload_files(source)
    check_destination(source, destination, files, mode, replace_settings)
    version = (source / "VERSION.txt").read_text().strip()
    identity = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    runtime_relative = Path(".bft-venvs") / identity
    backup = destination / ".bft-backups" / identity
    copied: list[Path] = []
    existed: set[Path] = set()
    destination.mkdir(parents=True, exist_ok=True)
    obsolete_installers = [p.relative_to(destination) for p in destination.glob("INSTALL_BUNDLETOOL_*.bat")
                           if mode == "upgrade" and p.relative_to(destination) not in files]
    for relative in obsolete_installers:
        if linked(destination / relative, destination):
            raise ValueError(f"Refusing linked prior installer: {relative}")
    paths = [*files, MANIFEST, RUNTIME_POINTER, RECEIPT, *obsolete_installers]
    # Back up all overwritten files before touching the installation.
    for relative in paths:
        target = destination / relative
        if target.is_file():
            copy_file(target, backup / relative)
            existed.add(relative)
    try:
        report("Placing verified program files...")
        for relative in [*files, MANIFEST]:
            copied.append(relative)
            copy_file(source / relative, destination / relative)
        for relative in obsolete_installers:
            copied.append(relative)
            target = destination / relative
            target.chmod(target.stat().st_mode | stat.S_IWUSR)
            target.unlink()
        payload_files(destination)
        python = prepare_runtime(source, destination, destination / runtime_relative, report)
        report("Checking CLI, Tk, and application imports...")
        validate_runtime(python, destination)
        receipt = {"version": version, "mode": mode, "destination": str(destination),
                   "runtime": str(python.relative_to(destination)), "backup": str(backup),
                   "installed_at": identity,
                   "manifest_sha256": hashlib.sha256((source / MANIFEST).read_bytes()).hexdigest()}
        for relative, content in ((RUNTIME_POINTER, runtime_relative.as_posix() + "\n"),
                                   (RECEIPT, json.dumps(receipt, indent=2) + "\n")):
            copied.append(relative)
            (destination / relative).write_text(content, encoding="utf-8")
        (destination / "bundle_config.json").chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    except BaseException:
        report("Installation failed; restoring prior program files...")
        for relative in reversed(copied):
            target = destination / relative
            if relative in existed:
                copy_file(backup / relative, target)
            elif target.is_file():
                target.chmod(target.stat().st_mode | stat.S_IWUSR)
                target.unlink()
        # Leave the failed runtime and backups for diagnosis. The previous
        # runtime pointer remains active; never delete an older environment.
        raise
    report(f"Installed Bundle File Tool {version} in {destination}")
    if shortcuts:
        report("Registering desktop launchers...")
        if sys.platform == "darwin":
            run(["/bin/sh", str(destination / "scripts/install_macos.sh"), "install"])
        elif os.name == "nt":
            run(["cscript.exe", "//Nologo",
                 str(destination / "scripts/install_windows_shortcuts.vbs"), str(destination)])
    return receipt


def source_root() -> Path:
    return Path(__file__).resolve().parents[1]


def installer_window(source: Path) -> None:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    root = tk.Tk()
    root.title("Install Bundle File Tool")
    root.geometry("700x455")
    root.minsize(620, 420)
    frame = ttk.Frame(root, padding=18)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="Bundle File Tool installation", font=("TkDefaultFont", 15, "bold")).pack(anchor="w")
    mode = tk.StringVar(value="fresh")
    for label, value in (("Install into a new folder", "fresh"), ("Upgrade an existing BFT folder", "upgrade")):
        ttk.Radiobutton(frame, text=label, variable=mode, value=value).pack(anchor="w", pady=4)
    destination = tk.StringVar(value=str(Path.home() / "Applications" / "Bundle File Tool"))
    row = ttk.Frame(frame)
    row.pack(fill="x", pady=12)
    ttk.Entry(row, textvariable=destination).pack(side="left", fill="x", expand=True)
    def browse():
        selected = filedialog.askdirectory(title="Select installation folder", mustexist=False)
        if selected:
            destination.set(selected)
    ttk.Button(row, text="Browse...", command=browse).pack(side="right", padx=(8, 0))
    replace_settings = tk.BooleanVar(value=False)
    ttk.Checkbutton(frame, text="Use delivered governed settings (back up existing settings)",
                    variable=replace_settings).pack(anchor="w")
    ttk.Label(frame, text="Upgrades back up replaced files. Personal UI preferences are retained.\n"
              "Close BFT before upgrading. Install optional splash support separately.", wraplength=640).pack(anchor="w", pady=8)
    messages: queue.Queue = queue.Queue()
    output = tk.Text(frame, height=7, wrap="word", state="disabled")
    output.pack(fill="both", expand=True, pady=8)
    busy = False
    def start():
        nonlocal busy
        if not destination.get().strip():
            messagebox.showerror("Installation", "Choose an installation folder", parent=root)
            return
        selected = (Path(destination.get()), mode.get(), replace_settings.get())
        busy = True
        button.configure(state="disabled")
        def worker():
            try:
                receipt = install(source, selected[0], selected[1], replace_settings=selected[2],
                                  shortcuts=True,
                                  report=lambda msg: messages.put(("log", msg)))
                messages.put(("done", receipt))
            except Exception as exc:
                messages.put(("error", str(exc)))
        threading.Thread(target=worker, daemon=False).start()
    def poll():
        nonlocal busy
        while not messages.empty():
            kind, value = messages.get_nowait()
            if kind == "log":
                output.configure(state="normal")
                output.insert("end", value + "\n")
                output.see("end")
                output.configure(state="disabled")
            else:
                busy = False
                button.configure(state="normal")
                if kind == "error":
                    messagebox.showerror("Installation failed", value, parent=root)
                else:
                    messagebox.showinfo("Installation complete", "Installed in " + value["destination"]
                        + "\n\nWindows shortcuts are on the Desktop. Mac apps are in ~/Applications.\nThe launchers folder also contains diagnostic launchers.", parent=root)
        root.after(100, poll)
    button = ttk.Button(frame, text="Install", command=start)
    button.pack(anchor="e")
    root.protocol("WM_DELETE_WINDOW", lambda: None if busy else root.destroy())
    root.after(100, poll)
    root.mainloop()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("fresh", "upgrade"))
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--replace-settings", action="store_true")
    parser.add_argument("--no-shortcuts", action="store_true")
    args = parser.parse_args(argv)
    try:
        if not args.mode and args.destination is None:
            installer_window(source_root())
        elif not args.mode or args.destination is None:
            parser.error("--mode and --destination must be supplied together")
        else:
            print(json.dumps(install(source_root(), args.destination, args.mode,
                                     replace_settings=args.replace_settings,
                                     shortcuts=not args.no_shortcuts), indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, ImportError) as exc:
        print(f"BFT installation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
