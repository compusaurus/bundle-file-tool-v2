# Bundle File Tool

Use `INSTALL_BFT.cmd` on Windows or `INSTALL_BFT.command` on macOS for a fresh folder or an upgrade. See [Installation](docs/INSTALLATION.md).

Bundle File Tool (BFT) creates, reviews, validates, and extracts portable text
bundles. Build 135 provides command-line, native Tkinter, and local browser
interfaces on Windows, macOS, and Linux with Python 3.11, 3.12, or 3.13. The macOS installer is included; native Mac acceptance remains to be run.

Build 135 repairs Create Bundle for Mac framework file aliases and records the
producing BFT build in new bundles. Un-bundle displays that build and records
the input filename and entry details when parsing fails. See the
[Build 135 repair record](docs/implementation/BFT_BUILD135_MAC_FRAMEWORKS_2026-09-22.md).

The CLI and Tk surfaces use the governed PyThermX 0.5.3 progress package. The
web surface uses the vendored NodeThermX 0.3.0 Build 3 DOM adapter; its runtime
assets are local to BFT, require no browser framework or network service, and
retain NodeThermX's MIT license notice under `vendor/`.

The browser workspace includes Studio and Midnight skins, a BFT-specific visual
identity, and full-path presentation for long source names and planned entries.
The appearance choice is remembered in BFT's per-user state rather than tied to
the short-lived browser session URL. It also uses PySplashX's dependency-free
web component to play the same Crex clip on each new page load, with muted
autoplay, Skip/Escape controls, reduced-motion bypass, a **Replay PySplashX**
control, and a fail-open timeout.

The native Tk application uses the same BFT bundle mark as its window icon.
When the optional `splash` dependencies are installed, startup plays the bundled
Crex clip through PySplashX 0.1.0 in an isolated Qt process before Tk opens. A
missing multimedia runtime or playback problem is non-fatal. CLI commands play
the splash by default; put `--skip-splash` before the subcommand to start
immediately. `BFT_SPLASH=0` remains available for launchers and automation.

The native Bundle workspace uses Selections, Rules, Result set, and Operational
Guidance views. Show views remembers your choices; Layout offers tabs, equal
side-by-side panes, stacked panes, or a grid. Show all displays every view.
New window detaches a live view, and closing it returns it to the workspace.
On Windows, RailGun detects additional displays and offers Other display buttons.
See the [Build 134 comparison guide](docs/implementation/BFT_BUILD134_COMPARISON_VIEWS_2026-09-22.md).
Rules offers List matches, showing each pattern on its own row. Result set starts
on Included. ConfigHub includes the BFT-owned PyThermX progress profile and the
shared native/Web splash settings. See the [Build 133 settings audit](docs/implementation/BFT_BUILD133_SETTINGS_AUDIT_2026-09-21.md).
The Source field occupies a separate full-width row. Linux and WSL2 installation
instructions are in [docs/LINUX_SETUP.md](docs/LINUX_SETUP.md).

## Start the application

Use one of the standardized environments:

```powershell
.venv311\Scripts\activate.bat
python src\main.py
```

The other supported environment names are `.venv312` and `.venv313`. Normal
Windows desktop launch uses `launchers\windows\Bundle File Tool.vbs` without a
console. macOS setup and application-wrapper instructions are in
[docs/MACOS_SETUP.md](docs/MACOS_SETUP.md).

Start the loopback-only web workspace with `launchers\windows\Bundle File Tool
Web.vbs`, the **Tools > Open Web Workspace** command in Tk, or:

```powershell
.venv311\Scripts\python.exe src\web_main.py
```

The private per-run URL opens in the default browser. It accepts local paths
through native Browse selectors and is never bound to the LAN or internet.

For command-line help:

```powershell
.venv311\Scripts\python.exe src\cli.py --help
```

The supported console commands are `bundle`, `unbundle`, `validate`, `check`,
and `plan`. The Tk and web workspaces provide the same core operations plus direct
selection and bundle integrity checks, a selection workspace, governed settings
through ConfigHub—including a dedicated PySplashX setup tab—clipboard ingress,
documentation, and log viewing.

## Documentation

See [USER_GUIDE.md](USER_GUIDE.md) for user-facing instructions and
[CHANGELOG.md](CHANGELOG.md) for release history. Internal architecture and
implementation records are stored separately under `docs/`.

## License

Bundle File Tool is proprietary software. See [LICENSE.txt](LICENSE.txt).
 
