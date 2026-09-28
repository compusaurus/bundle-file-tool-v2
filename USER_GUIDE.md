# Bundle File Tool 2.1 User Guide

## What BFT does

BFT combines project files into a portable text bundle and extracts supported
bundles back into files. It can also show why files are included or excluded,
validate bundle structure and checksums, and copy bundles through the Windows
clipboard.

## Starting BFT

From the project folder, run:

```powershell
.venv311\Scripts\activate.bat
python src\main.py
```

Python 3.12 and 3.13 users may activate `.venv312` or `.venv313` instead.
Build 131 also includes normal no-console, local web, and separate diagnostic
launchers in `launchers/windows` and `launchers/macos`. See
`docs/MACOS_SETUP.md` for the macOS application wrappers and environment
instructions.

The native window now uses BFT's custom sealed-bundle icon. If PySplashX and
PySide6 are installed, the Crex video plays before the Tk workspace opens. The
splash can be dismissed by clicking it. It is decorative and fail-open: BFT
continues if video playback is unavailable. The Windows no-console launcher
selects a supported environment containing both PySplashX and PySide6 when one
is available. Set `BFT_SPLASH=0` before a launcher invocation to skip it.

## Web workspace

Choose **Tools > Open Web Workspace** in the Tk application, launch **Bundle
File Tool Web** from the installed shortcut/app, or run `python
src/web_main.py`. BFT opens a private, per-run URL in the default browser. The
server listens only on `127.0.0.1`; it is not a hosted service and cannot be
reached from another device.

The Bundle and Un-bundle modes use the same planning, checking, creation,
validation, and extraction service as CLI and Tk. In Bundle mode, use
**Choose folder…** for the usual source workflow or **Choose file…** for a
single-file bundle. The complete source path appears below the selector and
wraps when it is long; table paths and the selected-path inspector do the same,
with the full value also available as hover text. Other local paths use **Browse…**, and
bundle output opens a native Save As dialog. Browser uploads are optional,
bounded temporary copies that are removed when the server stops. Changing a
Bundle source clears its existing plan so it cannot be checked or created by
mistake; select **Plan selection** again to review the new source.

The Crex startup clip plays through PySplashX on every new web page load. It is
muted for browser autoplay compatibility; choose **Skip**, press Escape, or use
a reduced-motion system preference to bypass it. **Replay PySplashX** in the
top bar replays it on demand. Playback or media failure always reveals the
workspace.

After planning, **Create bundle** is enabled even if no output path has been
entered. Choosing it opens Save As, then BFT refreshes the plan without another
filesystem scan so the selected output can never be included as an input.

Long operations show shared phase progress and a cancel action. The browser
renders these events with NodeThermX, including a prominent back-and-forth
indicator while the total is unknown and explicit completed, failed, or
cancelled terminal state. Extraction is
enabled only for the exact bundle most recently checked with no hard blockers.
Use **Stop server** when the session is finished; closing only the browser tab
does not stop the local process.

Use **Studio** or **Midnight** in the top bar to change the browser appearance.
BFT remembers the choice in the same per-user state store used for last-opened
folders; it remains effective when a later web session uses a different port.

## Un-bundle mode

1. Choose **File > Open Bundle** or press **Ctrl+O**.
2. Review the detected format, file list, and integrity status. Bundles are
   checked on load by default; **Check Bundle** runs the check on demand.
3. Resolve any blocking finding before extraction. Select an output directory
   and overwrite policy.
4. Use **Extract Files**. Dry-run mode previews the operation without writing.
   Extraction always enforces hard integrity blockers.

**File > Un-bundle from Clipboard** opens bundle text currently stored on the
clipboard and presents it in the same un-bundle workspace.

## Bundle mode

The Source field has its own row. **Show views** controls the **Selections**,
**Rules**, **Result set**, and **Operational Guidance** pages and remembers
your choices. Rules and Result set start hidden. Select Operational Guidance
for step-by-step help; hiding a page never changes the selection plan.

**Layout** offers **Tabs**, **Side by side**, **Stacked**, and **Grid**. Selected
views divide the available workspace evenly. **Show all** displays all four in
a grid. The layout is remembered for the next launch. In a short Result set pane,
**Show explanation** starts collapsed to leave room for rows; select it to read
the explanation and use the session override control. In especially short panes,
the **Actions…** menu provides Include visible, Exclude visible, Clear overrides,
Expand all, and Collapse all while leaving result rows visible.

**New window** opens a view separately while retaining its current contents.
Close that window or select **Return to workspace** to bring it back. **Return
all to workspace** brings every separate view back. On Windows, RailGun detects
additional displays and shows **Other display** on each view, plus **Move
workspace to other display**. With three or more displays, repeated clicks cycle
through them. If a monitor disconnects, off-screen views return to an available
display. On other native platforms, use New window and your OS window controls
to place it manually.

To compare Selections and Result set on the left with guidance on the right:
select those three views, choose **Side by side**, and press **Other display**
on Operational Guidance. Selections and Result set then split the main workspace
evenly and stay synchronized. These layout controls belong to the native app.

Linux and WSL2 setup is described in `docs/LINUX_SETUP.md`.


1. Select **Bundle** in the mode selector.
2. Choose a source directory.
3. Select a preset and review included, excluded, and blocked paths.
4. Use the selection report to inspect the effective rules, then use
   **Check selection** to read and check the planned content without publishing
   a bundle.
5. Resolve blocking findings directly or exclude their source paths for the
   current session.
6. Create a bundle file or copy the reconciled bundle to the clipboard. The
   default workflow checks before creation and verifies a saved artifact after
   creation.

Large CLI and Tk scans and bundle operations display PyThermX progress; the web
workspace displays the same BFT progress events through NodeThermX. Changing a
preset reuses the scan snapshot; it does not rescan file contents.

When a plan is large, BFT shows estimated source, output, temporary-storage,
and peak-memory requirements before execution. The CLI requires
`--allow-large`; the desktop asks for confirmation. Large results are streamed
to an artifact instead of being duplicated in memory. Clipboard and automatic
preview remain intentionally bounded.

## Validation

Use **Check Bundle** in Un-bundle mode for the actionable integrity report.
**Tools > Validate Bundle** remains available for compatibility. BFT reports
the detected format, file count, warnings, parse errors, nested-bundle findings,
unsafe paths, portable path collisions, and checksum failures.

## Logs

Choose **Tools > View Logs** to browse persistent `.json`, `.log`, and `.txt`
files in the configured BFT log directory. The viewer is read-only.
**Tools > View Startup Logs** opens the per-user logs created before the GUI is
constructed, including failures from a normal no-console launch.

## Settings

Choose **File > Settings** to open ConfigEditor through PyProjectMgr. ConfigHub
identifies BFT as the requester and PyProjectMgr as the governance orchestrator.
The session contains separate **Bundle File Tool** and **PySplashX** application
tabs; the latter exposes General, Interfaces, Media, Timing, Geometry, Runtime,
and Logging setup sections for the BFT splash profile.
On multi-display systems it opens on the display containing the invoking BFT
window.

Choose **File > Startup Window** to select Restore Last, Normal, Maximized, or
Minimized. Restore Last is the default. Closing BFT while minimized does not
make later Restore Last launches invisible. On macOS, Maximized fills the
monitor work area and does not enter fullscreen.

Choose **Tools > Integrity Check Preferences** to control automatic checks on
load, before creation or extraction, and after saving. These are convenience
preferences; confirmed hard blockers cannot be disabled.

## Command-line examples

Every CLI command plays the PySplashX startup clip by default when its optional
native runtime is available. Put the global `--skip-splash` option before the
subcommand to suppress it for one invocation.

```powershell
.venv311\Scripts\python.exe src\cli.py validate path\to\bundle.txt
.venv313\Scripts\python.exe src\cli.py --skip-splash validate path\to\bundle.txt
.venv311\Scripts\python.exe src\cli.py check path\to\bundle.txt --format json
.venv311\Scripts\python.exe src\cli.py plan path\to\project
.venv311\Scripts\python.exe src\cli.py bundle path\to\project --precheck --output project_bundle.txt
.venv311\Scripts\python.exe src\cli.py unbundle project_bundle.txt --output extracted
```

Use `--help` on the program or a subcommand for the complete option list.

## Troubleshooting

- If ConfigHub cannot start, review the diagnostic path shown by BFT and verify
  the governed PyProjectMgr installation.
- If a governed-configuration warning appears, repair or reinstall the current
  delivery rather than editing `bundle_config.json` directly.
- If a window was saved on a disconnected display, BFT clamps it to the
  nearest available display at startup.
- Supported environment names are exactly `.venv311`, `.venv312`, and
  `.venv313`.
- If the Crex clip is skipped, run `scripts/setup_supported_envs.ps1` on
  Windows or install `PySide6` and the governed `vendor/pysplashx-0.1.0-py3-none-any.whl`
  in BFT's selected environment. Review the startup log for the exact status.


## Build 133 installation and settings

See [Installation](docs/INSTALLATION.md) for fresh-folder and upgrade choices.
Settings opens ConfigHub with Bundle File Tool, PyThermX (BFT), and PySplashX
tabs. PyThermX (BFT) controls native and terminal progress; browser progress uses
NodeThermX. Legacy settings are read only and explain which current control to use.
The Linux desktop shortcut uses the Ubuntu-hosted browser workspace, including
a browser file chooser.

In Rules, leave **List matches** checked to display each pattern on its own row.
Clear it for the compact view; BFT remembers the choice. Result set initially
selects **Included**. Choose All, Excluded, or Blocked when reviewing those files.

The PySplashX Shape field controls the outline, not the video's dimensions.
Rect gives square corners. The bundled square CRex video reports 720 x 720.
Native and Web read the same splash profile; reload Web or restart native BFT
after changing it. Native window frame, stacking, heartbeat and logging controls
apply only to the native splash. See the [settings audit](docs/implementation/BFT_BUILD133_SETTINGS_AUDIT_2026-09-21.md) for scope and qualification.

## Bundle identification in Build 135

New bundles record the producing BFT version in their file-header metadata.
Un-bundle shows “Created with BFT” after opening and checking them. Older files
without a tag show “Producer build not recorded.” This works with plain-marker
and Markdown-fence bundles and does not add headers to the extracted files.

If opening fails, the dialog and operation log identify the input file and the
affected entry. Tools > View Startup Logs retains the traceback. Preserve the
original bundle when reporting a size mismatch; do not edit its size metadata.
