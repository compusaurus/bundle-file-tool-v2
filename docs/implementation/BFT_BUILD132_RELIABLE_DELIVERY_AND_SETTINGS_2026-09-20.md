# Build 132 delivery and settings

## Changes

- Fresh-folder/upgrade installer for Windows, macOS, and Linux, with offline
  runtime preparation, checksums, settings replacement guard, file backups,
  and automatic rollback of program files and the active runtime pointer.
- macOS command entry point and application registration; all app executable
  permissions are preserved in the macOS tar archive. Mac wrappers identify
  Build 132 and resolve the installed runtime.
- Windows BFT ConfigHub requests BFT, PyThermX, and PySplashX and supplies its
  own root. ConfigHub's PyThermX provider compares the governed schema's version
  to the corresponding supported runtime schema. The shared source profile is
  schema 1.3. Its runtime snapshot is documented in vendor/confighub/README.md.
- The web Source input occupies a full-width row above the workspace columns.
  The full path can also wrap below the input. Browse folders and Browse files
  buttons sit beside the Source heading, leaving the input its full width.
- The splash component stylesheet is loaded only inside its shadow root;
  its Skip button positioning no longer displaces the workspace's controls.
- The Windows Linux shortcut starts the Ubuntu browser service with a private
  loopback session, checks Linux/version identity, opens the Windows browser,
  and reuses an existing healthy session. Its file chooser works in the browser.

## Host diagnosis and selected Linux route

The Linux Tk application reached its main loop and drew the complete workspace
on the X server. Windows exposed only a blank taskbar thumbnail. WSL is
2.7.12.0, WSLg 1.0.73.2, and Windows is 10.0.26200.9457. Weston reports a
shared-memory I/O error. The Windows RDPClient log reports
WireDecoderError_DecodeW2S1InvalidData and graphics decode events 1033/226/1404.

Restarting only BFT-Ubuntu-24.04 did not fix presentation. A temporary tmpfs
mount workaround was ineffective and was unmounted. Microsoft tracks matching
symptoms in [WSLg issue 1489](https://github.com/microsoft/wslg/issues/1489) and
a shared-memory fix in [WSL PR 41499](https://github.com/microsoft/WSL/pull/41499).
Ringo explicitly chose stable WSL plus a working Linux browser launcher.
No preview WSL release or graphics/security setting was installed or changed.

## Verification

Windows Python 3.13: 1,686 tests passed, 85.77% coverage.
Ubuntu Python 3.12: 1,686 tests passed, 85.16% coverage, two non-failing Tk
teardown warnings. Both meet the 85% coverage gate. ConfigHub: 20 tests passed,
including real Tk rendering of all three tabs; three-app validate-only reported
zero errors and zero warnings.

The fresh-installer rehearsal caught an incorrect class name in its final Tk
import check. Automatic rollback ran; the class name was corrected and the
Windows fresh installation subsequently completed in a folder containing spaces.
An actual fresh Build 131 installation was then upgraded to Build 132. The
acceptance check verified the previous version's backup, a new isolated runtime,
retention of a personal file and portable preferences, and removal of the
obsolete versioned installer from the active folder. Both installation paths
contained spaces. Follow-up focused checks passed: 36 installer/ConfigHub/launcher
checks and 31 browser checks after the final integration changes.

Installed Ubuntu acceptance verified all 272 payload files, governed configuration
integrity, a byte-for-byte create/extract round trip, and the native Tk Source
layout in a virtual display. The actual Windows Linux desktop shortcut opened
the Ubuntu browser workspace. Visual review found and fixed an existing global
splash CSS collision that displaced ordinary buttons. The corrected in-app
preview visibly displayed both Source picker buttons; Browse folders listed
Ubuntu directories and Select returned the chosen full path. The final browser
static, picker, and HTTP checks passed (28 tests).

No native Mac was available. Mac qualification is limited to shared installer
behavior, shell syntax, application structure, and executable archive modes.
Run native acceptance on the destination Mac before treating it as qualified.

This remains an internal delivery under the existing BFT license. The existing
Windows source tree was updated directly; the legacy developer-suite stager was
not rerun over the shared working directory. No Git commit or public release
was created.
