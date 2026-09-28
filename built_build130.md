# Bundle File Tool v2.1 Build 130 - Build Record

**Prepared:** 2026-09-04  
**Status:** Installed and accepted on the Windows reference PC  
**Release identity:** `2.1.130`

## Outcome

Build 130 corrects the two splash presentation defects found during Build 129
acceptance. The local web splash is now a strict-CSP-safe fixed viewport
overlay; it no longer enters document flow or displaces the Bundle File Tool
workspace. Native startup resolves one signed-coordinate work area and gives
the same target to both PySplashX and the Tk application.

The reusable `railgun_display` package supplies framework-neutral geometry,
saved-window and attention-aware display resolution, disconnected-display
recovery, a zero-dependency Win32 driver, and process-tree-aware window
placement. Following launcher descendants is required because Windows virtual
environment launchers can use a different process ID from the interpreter that
owns the Qt splash window.

Build 130 retains the Build 129 custom icon, Crex media, PySplashX 0.1.0,
PyThermX 0.5.3, NodeThermX 0.3.0 Build 3, ConfigHub contribution, and
completed-plan Create-bundle correction.

## Qualification evidence

- Live Chromium replay passed: the splash remained centered above a dimmed
  workspace and page coordinates were unchanged before and after dismissal.
- Live Windows native replay passed: saved-window resolution selected
  `1920,0,3840,1080`; playback completed and the descendant Qt window received
  124 successful placement operations.
- Focused browser/server regression: 37 passed.
- Focused native splash/display regression: 20 passed.
- Binding Windows Python 3.13 suite: 1,663 passed in 113.91 seconds with 85.69%
  branch-aware coverage (85.0% required). One non-failing, pre-existing
  Tkinter teardown warning remained; no display or PySplashX warning remained.
- Binding installer suite: 1,663 passed with 85.69% branch-aware coverage.
- Cross-product installation acceptance: 19 PyProjectMgr/ConfigHub tests and
  11 ConfigEditor tests passed; native and web desktop launchers were created.
- The delivery installer verifies the exact web module and external stylesheet
  hashes, imports the reusable display API, byte-compiles the source, reruns
  the binding whole suite, and repeats the cross-product ConfigHub gates.

## Delivery status

The governed delivery contains 282 BFT files and 9 cross-product integration
files. Its SHA-256 sidecar and the stager preflight both verified the package.
The standard stager created and retained the Build 130 snapshot, archived the
outgoing installation, and placed the governed payload. The first installer
attempt stopped at the cross-product gate when Tcl temporarily could not read
its installed `init.tcl`; an immediate isolated replay of the same ConfigHub
test passed. The failed-attempt recovery ledger was preserved under the
project archives, and the retained payload was installed again. Every gate then
passed, including the binding whole suite, both cross-product suites, governed
configuration write protection, and native/web launcher installation.

## Publication status

This is a restricted internal release. The Crex rights and attribution gate
recorded in the Build 129 integration note remains open; Build 130 does not
grant public redistribution rights. Repository commit and tag actions remain
reserved for the authorized interactive release owner.
