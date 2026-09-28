# Build 131 workspace and Linux delivery

Requested by Ringo in BFT notes dated September 20, 2026, with the ConfigHub
failure added during implementation.

The native workspace uses a full-width source row, a separate action row, and
four notebook pages. Visibility preferences belong to UserStateStore, outside
governed configuration. Existing selection, override, inspection, check, and
creation operations retain their shared model and service implementations.

ConfigHub diagnosis found an empty PyProjectMgr `.venv313` selected before a
working `.venv`, plus a missing BFT manifest configuration digest. Build 131
probes CLI/provider imports, uses isolated child Python imports, and restores
the digest before regenerating governance artifacts with PyProjectMgr.

## Qualification

- Windows 11, Python 3.13.15: 1,667 passed in 130.40 seconds; branch-aware
  coverage 85.76% against the unchanged 85% gate.
- BFT-Ubuntu-24.04 WSL2, Python 3.12.3: 1,667 passed in 65.79 seconds using
  Xvfb; branch-aware coverage 85.15% against the same gate. No skipped tests.
- Existing Tk variable cleanup warnings remain non-failing: one on Windows,
  two on Linux.
- ConfigHub: 19 integration checks passed. ConfigEditor: 11 passed.
- The actual Windows Settings route validates BFT and PySplashX with zero
  blockers and zero warnings and opens the ConfigEditor window.
- Native layout inspected at 800 by 600. Source occupies its own wide row;
  default visible pages are Selections and Operational Guidance. Integration
  checks cover saved visibility, hiding all pages and restoring a page, small
  window controls, and horizontal scrolling on each selected page.
- Linux native Tk initialization and BFT construction passed against WSLg.
  The installed launcher opened a live WSLg Selection Workspace window.

The Win32 adapter tests use a portable callback factory only for their fake
Win32 APIs on non-Windows test hosts. Production Windows calling conventions
are unchanged; these tests do not claim a native Linux display driver.

## Delivery and local installation

Windows delivery: `dist/INSTALL_BUNDLETOOL_v2_1_131_workspace_tabs_and_linux.zip`.
Linux delivery: `dist/bundle-file-tool-2.1.131-linux.tar.gz`.
Each archive has a SHA-256 sidecar. Both contain the same verified BFT payload.
The Windows archive also retains the existing cross-product integration kit.
The payload excludes local databases, scan reports, backups, and personal state.

Linux installs under `/home/mpw/.local/share/bundle-file-tool/releases`; the
`current` symlink points at the accepted installation. Launchers are
`/home/mpw/.local/bin/bft`, `bft-gui`, and `bft-web`. Earlier BFT installations
and preferences were retained.

Windows desktop shortcut:
`F:\documents\DLP\Desktop\Bundle File Tool Linux.lnk`, targeting
`wsl.exe -d BFT-Ubuntu-24.04 --exec /home/mpw/.local/bin/bft-gui`.
The Linux application-menu entry is
`/home/mpw/.local/share/applications/bundle-file-tool.desktop`.

The Linux BFT runtime is installed with PyThermX. Native video playback and
native Linux ConfigHub remain optional suite dependencies: PySplashX/PySide6
and a configured Linux PyProjectMgr/ConfigEditor installation respectively.
Windows ConfigHub is repaired and verified. No Linux companion suite was
installed or substituted with a Windows configuration editor.

The existing Windows source installation now contains Build 131. Its complete
test gate passed; the destructive Windows stager was not rerun over the shared
working directory. The delivery installer retains the staging gates and adds
validation through the actual BFT ConfigHub launch route.
