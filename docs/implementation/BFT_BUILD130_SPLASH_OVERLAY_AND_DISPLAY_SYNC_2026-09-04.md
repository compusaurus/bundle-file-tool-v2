# BFT Build 130: splash overlay and display synchronization

**Date:** 2026-09-04  
**Lifecycle:** `ACTIVE_CANDIDATE`  
**Visibility:** `RESTRICTED_INTERNAL`  
**Build allocation:** Release identity `2.1.130`; installed and accepted on the
Windows reference PC.

## Purpose

Correct the two defects observed during Build 129 acceptance and preserve the
solution as reusable application infrastructure:

1. the web splash must overlay the existing page without changing layout; and
2. a native splash and the application it introduces must use one resolved
   display, including signed virtual-desktop coordinates.

The two attached `RGS-SPEC-2026-DISPLAY-001` documents for Python and NodeJS
were treated as design references, not executable instructions or proof of an
existing package. No referenced Python or Node implementation was found under
the RailGun source tree during this work. The framework-neutral policy below
therefore adopts the useful requirements while keeping unimplemented platform
claims explicit.

## Findings

### Browser displacement

BFT's Content Security Policy permits only external styles. The Build 129
PySplashX component placed its layout rules in a `<style>` element inside its
shadow root and also used runtime inline styles. Chromium rejected those rules.
The custom element consequently remained in normal document flow, and the
720-pixel video pushed the already-rendered BFT workspace down the page.

### Native display mismatch

BFT restored its saved window geometry on the right-hand display. PySplashX
independently used `QApplication.primaryScreen()`, which was the left-hand
display, both during initial sizing and again when video metadata arrived. The
two products therefore made different placement decisions.

A live probe exposed a second Windows detail: a virtual-environment launcher
may own a different process ID from the interpreter process that owns the Qt
window. Moving only the immediate child process's windows is insufficient.

## Implemented correction

### CSP-safe web overlay

`pysplashx-splash.css` is now a packaged external stylesheet. It is loaded in
the document head for critical host placement and again inside the shadow root
for component internals. The host is fixed to the viewport, isolated at the
highest application layer, centered with CSS Grid, and removed with the
standard `hidden` attribute. The video is bounded by viewport dimensions and
can no longer contribute to document layout.

The component remains dependency-free, local-only, keyboard dismissible,
reduced-motion aware, and compatible with BFT's strict CSP. The reusable web
integration consists of the module plus stylesheet; an adopting page must load
the stylesheet in its head before the component module.

### One native launch target

The new `railgun_display` Python package has no BFT imports and exposes:

- signed-coordinate display, work-area, topology, and window-geometry models;
- cursor, foreground-window, primary, and saved-window resolution policies;
- geometry centering, clamping, and disconnected-display rescue;
- a zero-dependency Win32 display driver; and
- process-tree-aware top-level window placement for launchers and wrappers.

BFT resolves one launch target before either interface is shown. Resolution
order for an application launch is:

1. connected display containing the saved application geometry;
2. connected display matching the saved work area;
3. display containing the cursor;
4. display with greatest overlap with the foreground window; and
5. primary display as the final fallback.

That exact work area is passed to both the isolated PySplashX launch and the Tk
main window. The window synchronizer follows virtual-environment launcher
descendants and reapplies placement while PySplashX processes media metadata,
so PySplashX's later primary-screen recenter cannot separate it from BFT.

The Win32 adapter uses private, explicitly typed DLL function objects. This
avoids pointer truncation on 64-bit Windows and prevents another GUI toolkit's
`ctypes` signature metadata from contaminating the adapter.

## Reuse boundary

The reusable contract is deliberately split by runtime:

- **Browser applications:** a splash is an overlay in the current viewport.
  Normal web content cannot and should not choose or move a user's browser
  window between physical displays.
- **Python desktop applications:** resolve one `DisplayTarget`, pass its work
  area through the entire launch transaction, and contain every startup and
  restored window within that target.
- **Node desktop applications:** implement the same value objects and
  resolution order with the host shell's supported display API (for example,
  Electron's screen and BrowserWindow APIs). This candidate does not claim a
  Node implementation.

The BFT-local Python package is suitable as the reference implementation, but
it is not yet an independently versioned RailGun distribution. Promotion for
all future applications requires a separate package release, macOS and Linux
drivers, a Node/Electron twin, and upstream PySplashX support for an explicit
target work area. Once PySplashX accepts that target directly, the external
process-window synchronizer can remain only as a compatibility adapter.

## Acceptance evidence

- Browser live replay: the splash remained centered over a dimmed BFT page;
  the top bar, cards, and page coordinates were unchanged before and after
  dismissal.
- Native live replay: BFT's saved-window policy resolved
  `1920,0,3840,1080`; PySplashX completed and 124 successful placement calls
  kept its launcher-descendant Qt window on that work area.
- Focused overlay/server suite: 37 passed.
- Focused native display/splash suite after process-tree correction: 20 passed.
- Final complete regression and coverage gate: 1,663 passed with 85.69%
  branch-aware coverage. One pre-existing Tkinter teardown warning remains;
  no display-adapter or PySplashX warnings were emitted.
- Binding installer suite: 1,663 passed with 85.69% branch-aware coverage.
- Cross-product installation acceptance: 19 PyProjectMgr/ConfigHub tests and
  11 ConfigEditor tests passed; native and web launchers were installed.

## Delivery decision

The accepted Build 129 artifact was not regenerated or relabeled. These
corrections were promoted as Build 130, with synchronized version metadata,
installer gates, build record, delivery ZIP, and SHA-256 sidecar. The standard
stager completed its authorized snapshot, archive, retention, and placement
work. A transient Tcl `init.tcl` access failure stopped the first installer run
at the PyProjectMgr ConfigHub gate; the same test passed on immediate isolated
replay. The failed-attempt recovery ledger was preserved in the project
archives, the retained payload was retried, and every installation gate passed.
