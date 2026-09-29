# Build 2.1.136 — macOS ConfigHub launch and governed digest verification

- Fixed "PyProjectMgr is unavailable" when Bundle File Tool is opened from Finder or the Dock on macOS.
- A Finder launch inherits a minimal PATH, so the app now also searches Homebrew, /usr/local/bin, ~/.local/bin, the running interpreter's own directory, and the per-version framework and user Python bin directories.
- The macOS app launchers now export PATH, so a double-clicked app matches a Terminal launch for the app and anything it starts.
- The unavailable message now reports every location that was searched instead of naming remedies alone.
- Accepted a POSIX virtual environment that provides python3 without python.
- Fixed governed digest verification reporting a false tamper finding on macOS and Linux: the byte-hashed manifest and governed config are no longer end-of-line normalised, so their recorded SHA256 values validate on every platform.

# Build 2.1.135 — Mac framework aliases and bundle tags

- Fixed duplicate manifest paths from Mac framework file aliases, which stopped Create Bundle before Save As.
- Preserved selected alias names while retaining resolved-target containment checks.
- Tagged new plain-marker and Markdown-fence bundles with the producing BFT build and displayed it in Un-bundle.
- Added input filename, entry, byte-size and producer context to parse diagnostics and persistent error logs.
- Added real Linux Save As regression coverage with file aliases, progress, review and cancellation.

# Build 2.1.134 — Comparison views and displays

- Added Tabs, Side by side, Stacked, and equal Grid layouts with remembered choices.
- Added separate live view windows, close-to-return behavior, and Return all.
- Integrated RailGun's Windows display detection and per-view/workspace move buttons.
- Recover separate views when a monitor disconnects and hide them in Un-bundle mode.
- Made result controls responsive and explanations collapsible in short panes.
- Retained fresh-folder/upgrade installation and the stable-WSL browser launcher.

# Build 2.1.133 — Readable rules and settings audit

- Added a remembered List matches option with one rule pattern per row.
- Result set starts on Included in native and Web workspaces.
- Fixed Web's state-name mismatch that left Included/Excluded/Blocked counts and filtered results empty.
- ConfigHub edits the BFT-owned PyThermX profile consumed by native and terminal progress.
- Native and Web splash presentation now follow the same configured media, timing and square-corner shape.
- Corrected Web operation defaults, configured logging, unsupported profile choices and misleading or inactive settings controls.
- Retained fresh-folder/upgrade installation and the stable-WSL browser launcher.

# Build 2.1.132 — Reliable delivery and settings

- Added an installer with fresh-folder and upgrade choices, checksum verification, backups, and automatic program-file rollback on failure.
- Added macOS installation entry point and corrected app wrapper versions and archive executable permissions.
- ConfigHub now includes PyThermX and validates its governed schema version against a compatible runtime.
- Added a Windows desktop launcher for the Linux-hosted browser workspace, with an in-browser file chooser for systems with unusable WSLg graphics.
- Preserved the Build 131 native workspace layout and remembered tab visibility.

# Build 2.1.131 — Workspace tabs and Linux support

- Source uses a full-width row; action controls remain visible at small window sizes.
- Selections, Rules, Result set, and Operational Guidance tabs have remembered visibility.
- ConfigHub skips incomplete Python environments and isolates imports from BFT.
- Restored the governed configuration digest required by ConfigHub.
- Added offline Linux installation, application-menu entry, and WSL desktop shortcut.

# Changelog

## 2.1.130

- Made the PySplashX web component a strict-CSP-safe fixed viewport overlay so
  startup media no longer enters document flow or displaces the BFT workspace.
- Added reusable signed-coordinate display models, attention-aware display
  resolution, disconnected-display rescue, and zero-dependency Win32 adapters.
- Resolved one launch work area for both PySplashX and Tk, including
  virtual-environment descendant-process window placement, so the splash and
  application remain on the same display.

## 2.1.129

- Applied BFT's custom sealed-bundle PNG as the default native Tk window icon,
  replacing the platform's generic feather icon and propagating the identity to
  child windows.
- Integrated the governed PySplashX 0.1.0 wheel and exact 7.792-second Crex MP4
  for native and local-web startup playback.
- Kept Qt Multimedia isolated from Tkinter in a short-lived child process, with
  a 20-second ceiling and fail-open handling for missing dependencies, damaged
  assets, playback errors, and nonzero child exit.
- Made PySplashX the CLI default and added the global `--skip-splash` opt-out;
  `BFT_SPLASH=0` remains available for launchers and automation.
- Made the Windows launcher select a splash-capable supported environment when
  one is installed instead of blindly selecting the first environment.
- Added PySide6 to the reproducible supported-environment toolchain, packaged
  both native assets, and pinned icon, video, and PySplashX-wheel identities in
  regression and installer gates.
- Added PySplashX's dependency-free web component, muted per-page Crex
  playback, Skip/Escape/reduced-motion behavior, an explicit replay control,
  and HTTP byte-range media delivery to the loopback workspace.
- Added a governed PySplashX provider and dedicated setup tab to the BFT-scoped
  ConfigHub session.
- Replaced a quote-sensitive web-skin delivery marker with a batch-safe marker
  and made the delivery builder reject future quote/percent marker hazards.
- Fixed the completed-plan action gate: **Create bundle** now enables before an
  output is entered, opens Save As on demand, and performs a metadata-only
  output-aware replan so an existing target cannot be bundled into itself.
- Retained the Build 128 Studio/Midnight web experience and the existing
  PyThermX and NodeThermX integrations unchanged.

## 2.1.128

- Reworked the browser workspace into a more modern, responsive card layout
  while retaining the existing Bundle and Un-bundle workflows.
- Added Studio and Midnight skins with an authenticated, per-user preference
  that persists across BFT's short-lived loopback session ports.
- Replaced the initial-letter brand tile with local BFT-specific mark and icon
  assets; the browser favicon and visible header now share that identity.
- Made long source, activity, selected, and table paths readable through a
  full-width source field, wrapping preview, multi-line path cells, and native
  full-value hover text.
- Kept all identity and appearance assets local, allowlisted, CSP-compatible,
  and included by Python package data and the governed delivery manifest.
- Added focused static, adapter, persistence, HTTP, and asset regressions, plus
  wide and narrow live-browser acceptance for both skins.

## 2.1.127

- Retained and reverified the governed PyThermX 0.5.3 Build 16 wheel used by
  the CLI and Tk progress adapters.
- Replaced the browser workspace's one-off decorative bar with the vendored
  NodeThermX 0.3.0 Build 3 DOM adapter and its native, accessible progress
  element.
- Added a strict BFT progress-event to ThermX Schema 1.1 mapping, including
  determinate and indeterminate modes, phase timing, cooperative cancellation,
  and honest completed, failed, and cancelled terminal states.
- Preserved the actual last reported value at termination instead of forcing
  every successful job to 100 percent in browser code.
- Corrected plan and replan completion events so selection counts stay in the
  message while completed work closes truthfully at 100 percent.
- Added the NodeThermX MIT notice, exact asset identity gates, package/server
  checks, and BFT-specific visual theming while retaining the adapter's
  reduced-motion, forced-color, narrow-layout, and cross-browser behavior.
- Reconciled the implementation index and installed-baseline documentation
  after the completed Build 126 Windows deployment.

## 2.1.126

- Completed the CLI/Tk/web triad with a dependency-free local browser
  workspace over the existing renderer-independent service contracts.
- Added Bundle planning, capacity review, decision filters, rule-chain
  inspection, session overrides, prechecks, creation, and saved-output
  verification to the browser surface.
- Added local-path and bounded-upload bundle checks, validation, entry review,
  dry runs, and extraction with the same hard safety gates used by CLI and Tk.
- Added native folder, file, save, and output-directory selectors; browsers do
  not reveal absolute paths, so a short-lived Tk chooser process bridges the
  local UI without uploading an entire project.
- Added cancellable background jobs and the shared progress-event stream,
  including explicit indeterminate phases instead of a misleading frozen 100%.
- Restricted the server to IPv4 loopback with an unguessable session route,
  mutation token, Host/Origin/Fetch-Site validation, no third-party assets,
  restrictive response headers, and bounded temporary state.
- Added Windows and macOS web launchers, the Tk **Open Web Workspace** action,
  the `bft-web` console entry point, and focused adapter/HTTP/security tests.

## 2.1.125

- Added one structured integrity-check result shared by the service, CLI, and
  Tk desktop, with stable finding codes, severity, path, remediation, and JSON.
- Added direct **Check selection** and **Check Bundle** actions, automatic
  check-on-load and pre-create behavior, saved-output verification, and
  per-user automation preferences.
- Made nested bundles, unsafe extraction paths, checksum mismatches, and
  portable path collisions hard service gates that adapters cannot bypass.
- Replaced generic late failures with actionable findings and session
  exclusion of blocking source paths.
- Added filter counts, explicit empty states, search labeling, disabled
  zero-scope actions, inspector guidance, and persistent checked/stale/blocked
  status.
- Added the CLI `check` command with text and JSON output, plus optional
  `bundle --precheck`.
- Split integrity and verification progress so a completed integrity phase is
  never followed by silent checksum/path work.
- Rescheduled the web member of the CLI/Tk/web triad to Build 126 so it can
  consume the frozen Build 125 check and safety contracts.

## 2.1.124

- Fixed self-bundling stalls by applying a BFT-specific exclusion preset before
  directory descent; generated environments, caches, logs, outputs, and
  temporary work trees no longer dominate the scan.
- Added capacity estimates and explicit approval for large CLI and desktop
  runs, with clipboard and automatic-preview limits.
- Made progress truthful through source verification, completed reads,
  integrity checking, formatting, writing, durable flush, and atomic
  publication; every long phase supports cooperative cancellation.
- Replaced full-artifact duplication with a bounded UTF-8 spool and streaming
  file/stdout publication while preserving byte-exact bundle formats.
- Qualified macOS path aliases and captured progress behavior without weakening
  canonical path containment or stdout purity.
- Added windowless Windows and macOS GUI launchers, separate diagnostic
  launchers, per-session startup logs, and documented macOS setup.
- Added per-user Restore Last, Normal, Maximized, and Minimized startup choices;
  macOS maximization uses the monitor work area rather than fullscreen.

## 2.1.123

- Integrated PyThermX 0.5.3, which performs the initial Tk canvas layout when
  cancellation is hidden; Open Bundle and Validate Bundle now show a complete
  progress indicator instead of a narrow window shell.
- Added a real-Tk BFT regression for the no-cancel progress-dialog geometry.
- Made structured session logs lazy: a persistent session file is created only
  when its first event is written, and the log viewer ignores legacy empty
  files.
- Bound the remaining classic bundle/unbundle Tk variables to their owning
  frames, eliminating deferred cross-thread finalizer warnings in the strict
  multi-runtime release sequence.
- Removed 399 zero-byte session logs while preserving the populated diagnostic
  log.

## 2.1.122

- Added a versioned BFT → PyProjectMgr → ConfigEditor invocation contract.
- ConfigEditor now identifies BFT as requester and PyProjectMgr as governor.
- ConfigEditor performs its own monitor-aware initial placement before display.
- Added functional bundle validation, clipboard unbundling, and log viewing.
- Replaced the internal documentation notice with an installed user guide.
- Added dialog ownership, restored-geometry reconciliation, and a working
  Ctrl+O shortcut.
- Standardized supported environment names as `.venv311`, `.venv312`, and
  `.venv313`, with clean recreation required for the Build 122 baseline.
- Corrected public packaging metadata and console entry points.
