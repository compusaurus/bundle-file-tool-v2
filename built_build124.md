# Bundle File Tool v2.1 Build 124 - Build Record

**Prepared:** 2026-09-01  
**Status:** Windows release candidate; independent macOS acceptance pending  
**Release identity:** `2.1.124`

## Outcome

Build 124 addresses the reported self-bundle run that displayed 100 percent and
then appeared frozen. The original tree contained 93,133 scanned paths; 71,074
were selected, and `tmp` plus `out` accounted for about 95 percent of selected
paths. The old read counter reached 100 percent before the final read returned,
then performed two silent metadata validations, integrity scanning, full-string
formatting, output writing, flush, and replacement. Formatting also duplicated
the complete artifact in memory.

The Build 124 BFT-source preset prunes generated work before descent. On the
same development root, the plan fell to 3,171 scanned paths and 3,049 included
paths in about 1.3 seconds. Explicit empty preset selection remains an opt-out.

Creation now exposes distinct source verification, completed-read,
post-read verification, integrity, formatting, writing, finalization, and
completion phases. Every long phase is cancellable; no terminal completion is
emitted before atomic publication. Large plans carry conservative output,
temporary-storage, and peak-memory estimates and require explicit approval.
Formatting and publication use a bounded UTF-8 spool, and large results remain
file-backed instead of being copied into another complete Python string.

## Cross-platform desktop work

- macOS `/var` and `/private/var` assertions compare canonical paths while
  production containment remains fail-closed.
- Captured CLI progress may be terminal-redrawn or line-oriented; stdout bundle
  purity, phase information, and percentage signals remain mandatory.
- Windows normal launch uses `pythonw.exe`; macOS normal launch uses an `.app`
  wrapper. Separate diagnostic launchers retain visible console output.
- GUI stdout/stderr are redirected before Tk import to per-user
  `startup_*.log` files, with native startup-failure surfacing.
- Per-user Restore Last, Normal, Maximized, and Minimized choices extend the
  existing state and monitor-placement subsystems. macOS maximize uses the work
  area rather than fullscreen, and a minimized close never overwrites the last
  visible state.

## Identity and delivery

| Artifact | SHA-256 |
|---|---|
| `vendor/pythermx-0.5.3-py3-none-any.whl` | `fdf58d38c61a91f539aed37f846eb25b94f8aaa7d3cba401308c312e517f2690` |
| `bundle_config.json` | `1bd094d2f395c4b471e647955aea9bf417c04add9f23b9f78d6c8a2aef7fd433` |
| `.pyprojectmgr/project_manifest.json` | `7b3c60a1f205e1566ffda62ea7563ed95d13096cd832fc35fe5379af760342fa` |

The Build 124 delivery builder includes the complete governed root set, the
vendored PyThermX wheel, Windows and macOS launchers, macOS setup instructions,
the full source/test trees, and checksum manifests. Windows setup accepts
`BFT_SETUP_STARTUP_MODE` and `BFT_INSTALL_DIAGNOSTIC_LAUNCHER` without writing
window state into governed configuration.

## Verification status

- Large-plan/service/planning regression group: 232 passed.
- Path-portability group: 84 passed.
- Startup, launcher, state, and placement group: 41 passed.
- Cancellation/service phase group: 35 passed, 7 display-dependent skipped.
- Complete recovered Python 3.11, 3.12, and 3.13 non-display matrix: each row
  passed 1,446 tests with 122 display-dependent skips.
- Branch coverage in that no-Tcl runtime: 74.83 percent. The binding 85 percent
  gate remains intact and is pending a qualified Windows runtime where the 122
  real-Tk tests execute; the gate was not lowered or bypassed.
- Candidate delivery manifest: 228 payload hashes and 7 cross-product hashes;
  all 228 payload files were independently rehashed after ZIP extraction.
- Extracted-package CLI identity, governed-config digest, generated-manifest
  identity, bundle, validation, extraction, and byte-exact round trip: passed.
- Full Windows 3.11–3.13 real-Tk acceptance and official Mac qualification are
  still required before final cross-platform approval. The recovered runtimes
  contain `_tkinter` but lack their `init.tcl` payload, so they cannot provide
  honest real-display evidence.

Build 125 owns the web member of the CLI/Tk/web triad; no web framework is
introduced into this reliability release.

Repository commit and tag actions remain reserved for the authorized
interactive release owner.
