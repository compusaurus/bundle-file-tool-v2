"""Windowless Windows launcher for BFT hosted by a WSL Ubuntu installation."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import subprocess
import threading
import time
from urllib.request import urlopen
import webbrowser


def valid_url(url):
    return re.fullmatch(r"http://127\.0\.0\.1:[0-9]{1,5}/session/[A-Za-z0-9_-]{20,}/", url) is not None


def ready(url, version):
    if not valid_url(url):
        return False
    try:
        with urlopen(url + "api/bootstrap", timeout=2) as response:
            data = json.load(response)
        static = Path(__file__).resolve().parents[1] / "src/web/static"
        revision = hashlib.sha256(b"".join((static / name).read_bytes()
            for name in ("index.html", "app.js", "app.css",
                         "pysplashx-splash.mjs", "pysplashx-splash.css"))).hexdigest()
        return (data.get("schema") == "bft.web-bootstrap.v1" and data.get("platform") == "linux"
                and data.get("path_picker") == "browser" and data.get("version") == version
                and data.get("workspace_revision") == revision)
    except (OSError, ValueError):
        return False


def launch(distribution, linux_launcher, *, native=False, open_browser=True):
    root = Path(__file__).resolve().parents[1]
    version = (root / "VERSION.txt").read_text().strip()
    directory = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "BundleFileTool" / "wsl"
    directory.mkdir(parents=True, exist_ok=True)
    label = re.sub(r"[^A-Za-z0-9_.-]", "_", distribution)
    cache = directory / (label + "-web-session.json")
    if not native and cache.is_file():
        try:
            url = json.loads(cache.read_text())["url"]
            if ready(url, version):
                if open_browser:
                    webbrowser.open(url)
                return url
        except (OSError, ValueError, KeyError, TypeError):
            pass
    command = ["wsl.exe", "-d", distribution, "--exec", linux_launcher]
    if not native:
        command += ["--no-browser", "--browser-picker"]
    logfile = directory / (label + ("-native.log" if native else "-web.log"))
    with logfile.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=log, text=True, encoding="utf-8", errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        output = queue.Queue()
        def drain():
            for line in process.stdout:
                output.put(line.strip())
            output.put(None)
        threading.Thread(target=drain, daemon=True).start()
        if native:
            result = process.wait()
            if result:
                raise RuntimeError(f"Linux BFT exited with code {result}.\nDiagnostic log: {logfile}")
            return None
        try:
            url = output.get(timeout=45)
            if url is None or not valid_url(url):
                raise RuntimeError("Linux BFT did not return its local browser address")
            deadline = time.monotonic() + 30
            while not ready(url, version):
                if process.poll() is not None or time.monotonic() >= deadline:
                    raise RuntimeError("The Linux BFT browser service did not become ready")
                time.sleep(0.3)
            cache.write_text(json.dumps({"url": url, "version": version,
                                         "distribution": distribution}), encoding="utf-8")
            if open_browser:
                webbrowser.open(url)
            print(url, flush=True)
            process.wait()
            return url
        except BaseException:
            process.terminate()
            raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--distribution", default="BFT-Ubuntu-24.04")
    parser.add_argument("--linux-launcher", required=True)
    parser.add_argument("--native", action="store_true")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    try:
        launch(args.distribution, args.linux_launcher, native=args.native, open_browser=not args.no_browser)
    except Exception as exc:
        import tkinter as tk
        from tkinter import messagebox
        dialog = tk.Tk()
        dialog.withdraw()
        messagebox.showerror("Bundle File Tool Linux", str(exc), parent=dialog)
        dialog.destroy()
        raise SystemExit(1)
