# BFT Build 135 installation

Extract the delivery before running its installer. CPython 3.11, 3.12, or 3.13
with Tk and venv is required. The base runtime uses only included wheels and
needs no network access. Close BFT before upgrading.

On Windows, double-click **INSTALL_BFT.cmd**. On macOS, open
**INSTALL_BFT.command** (or run `sh INSTALL_BFT.command` in Terminal).
Choose **Install into a new folder** or **Upgrade an existing BFT folder**, then
browse to the destination and click Install. Folder names may contain spaces;
the new installer does not require the name `bundle_file_tool_v2`.

Fresh installation requires a new or empty folder. Upgrade verifies an existing
BFT installation, backs up every replaced program file, creates a new Python
environment, and switches the runtime pointer after validation. On failure it
restores the prior program files and runtime pointer. Previous environments and
backups are retained in `.bft-venvs` and `.bft-backups`; installation results are
recorded in `.bft-install.json`.

Personal UI preferences, bundles, and other files outside the delivery are
retained. If the existing governed settings differ from those in the delivery,
installation stops unless **Use delivered governed settings** is selected.
That explicit choice backs up and replaces the settings; it does not merge
them. Review the backed-up configuration before restoring any custom settings
through ConfigHub. A fresh program folder still uses the current user's normal
preferences; use `BFT_PORTABLE=1` for separate test preferences.

The replacement guard also covers customized BFT PyThermX and PySplashX
profiles. Unchanged profiles from the prior delivery receive the new defaults;
customized profiles require the explicit replacement choice and are backed up.

Windows shortcuts are registered on the Desktop. Mac app wrappers are placed
in `~/Applications`. Diagnostic launchers remain under `launchers`.

## Command-line installation

```text
python scripts/install_bft.py --mode fresh --destination "NEW_FOLDER"
python scripts/install_bft.py --mode upgrade --destination "EXISTING_BFT_FOLDER"
```

Use `--no-shortcuts` for test installations. Use `--replace-settings` only after
reviewing the governed settings replacement described above. Run the script
from the extracted payload (`_bundletool_incoming` in the Windows delivery).

The legacy versioned `.bat` remains available for the established staged
Windows developer-suite upgrade, including its ConfigHub integration gates.
It is not the fresh-folder installer and is not a Mac installer.

## Optional video and governed settings

Browser splash media is included. Native video requires PySplashX and PySide6;
the base installer provides the native Tk application without that optional
video. To enable video, use the Python path recorded in `.bft-install.json`:

```text
PATH_TO_INSTALLED_PYTHON -m pip install "PySide6>=6.8,<7"
PATH_TO_INSTALLED_PYTHON -m pip install --no-index --no-deps vendor/pysplashx-0.1.0-py3-none-any.whl
```

ConfigHub belongs to the separate PyProjectMgr/ConfigEditor suite. Standalone
BFT installation does not install that suite. On this Windows PC the existing
suite is integrated and the three tabs are verified. Elsewhere, set
`PYPROJECTMGR_PROJECT_ROOT` and configure the suite's governed registry roots.
BFT supplies its own installed root to ConfigHub when launching settings.

See [macOS setup](MACOS_SETUP.md) and [Linux/WSL setup](LINUX_SETUP.md) for
platform details and the limits of the current qualification.
