# Linux and WSL2 setup

Build 133 supports the CLI, native Tk workspace, and local web workspace on
Linux with Python 3.11, 3.12, or 3.13. Ubuntu 24.04 uses Python 3.12.

Install the operating-system prerequisites once on Ubuntu:

```sh
sudo apt install python3-venv python3-tk
```

Extract the Linux delivery, enter its `bundle-file-tool-2.1.135` directory,
and run:

```sh
sh scripts/install_linux.sh
```

The installer verifies every payload checksum, creates a separate virtual
environment, and installs the included packaging and PyThermX
wheels without accessing the network. It retains earlier installations under
`~/.local/share/bundle-file-tool/releases` and switches the `current` link only
after the new runtime passes its startup check. Personal preferences remain in
`~/.config/bundle_file_tool/user_state.json`.

Launch with `~/.local/bin/bft-gui`, `~/.local/bin/bft-web`, or
`~/.local/bin/bft --skip-splash --help`. A **Bundle File Tool** application-menu
entry is installed automatically. Native Tk needs a desktop display; WSL2 uses
WSLg. Headless machines can use the CLI.

The optional native video splash needs the included PySplashX wheel, PySide6,
and its OS multimedia libraries. Install these into
`~/.local/share/bundle-file-tool/current/.venv` if wanted; the Tk application
works without them. Browser splash assets are included.

## Windows desktop shortcut to WSL

After Linux installation, run from this delivery in Windows PowerShell:

```powershell
& .\scripts\install_wsl_shortcut.ps1 -Distribution BFT-Ubuntu-24.04
```

The **Bundle File Tool Linux** desktop shortcut starts the installed Linux
browser service and opens it in the Windows browser. The separate
**Bundle File Tool Linux Native** shortcut starts the Tk app when WSLg works.
Neither depends on an activated terminal.
Use `/home/mpw/...` for Linux files and `/mnt/c/Users/mpw/...` for Windows files.

## Governed settings

ConfigHub is provided by the separate PyProjectMgr and ConfigEditor projects.
For a Linux suite installation, set `PYPROJECTMGR_PROJECT_ROOT` to the Linux
PyProjectMgr directory and configure its registry roots, including
`BFT_PROJECT_ROOT` for the installed BFT release. BFT checks candidate Python
environments for the required ConfigHub imports and reports missing dependencies.
The Windows BFT app continues to use the Windows suite installation.

## Verification

Install `pytest`, `pytest-cov`, and `PyYAML` in a test environment, then run
`python -m pytest` from the installed release. Tk tests require a display;
`xvfb-run -a python -m pytest` provides one on a headless Linux host.

## This PC's stable WSL graphics limitation

The native app draws correctly on Ubuntu's X server, but WSLg cannot present
its window on Windows. Diagnostics show shared-memory I/O errors in weston.log
and WireDecoderError_DecodeW2S1InvalidData / RDP graphics errors in the Windows
RDPClient log. Restarting the dedicated distro did not repair it. This matches
Microsoft's [WSLg issue 1489](https://github.com/microsoft/wslg/issues/1489).
Ringo chose to retain stable WSL and use the Linux browser launcher.

The browser server still runs in Ubuntu, binds only to 127.0.0.1, and requires
its private per-session token. The browser file chooser lists Linux paths;
Windows files are available under /mnt/c, /mnt/f, and other mounted drives.
Repeat shortcut launches reuse a healthy session with the same BFT version
and workspace assets.
Use Stop server in the browser to end the Linux process.

The versioned Linux installer retains prior releases. To install into a new
specific folder or upgrade an existing direct installation, use
`python3 scripts/install_bft.py --mode fresh --destination /chosen/folder`
(or --mode upgrade), as described in INSTALLATION.md.
