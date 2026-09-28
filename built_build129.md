# Bundle File Tool v2.1 Build 129 - Build Record

**Prepared:** 2026-09-04  
**Status:** Installed and accepted on the Windows reference PC  
**Release identity:** `2.1.129`

## Outcome

Build 129 replaces Tk's generic feather with BFT's custom sealed-bundle icon
and integrates the exact Crex startup video through the governed PySplashX
0.1.0 native runtime and web component. Qt video runs in the library's
supported isolated helper process, then exits before BFT gives Tk control of
the native event loop. The browser renders the same media through the packaged,
dependency-free component and a loopback-only byte-range endpoint.

Splash presentation is fail-open and bounded to 20 seconds. The Windows
launcher selects a supported environment containing both PySplashX and PySide6
when available. CLI commands now play the splash by default and accept the
global `--skip-splash` option before the subcommand; `BFT_SPLASH=0` remains an
automation opt-out. The web splash appears on every new page load and can be
replayed from the top bar.

The BFT-scoped ConfigHub session now includes a real PySplashX provider and
dedicated setup tab alongside BFT settings. Provider validation uses the
packaged PySplashX schema and runtime before any profile can be committed.

Build 129 also corrects the browser Create-bundle gate identified during live
acceptance. A completed actionable plan now enables the button with no output
entered; the click opens Save As and refreshes only the output-sensitive
emission contract before creation.

## Qualification evidence

- Focused native/CLI/web splash, launcher, and ConfigHub regressions: 45 passed.
- Real Windows Python 3.13 / PySide6 6.11.1 playback: passed; the 7.792-second
  Crex clip reached its natural close and returned success.
- Real Tk construction: passed; `pyimage1` remained registered on the root as
  the retained default icon image.
- Live Chromium acceptance: passed; Crex appeared on page load, completed and
  dismissed, then reappeared through **Replay PySplashX**.
- Real CLI self-bundle acceptance: both the default-splash and `--skip-splash`
  commands bundled 3,118 files and produced byte-identical 75,126,228-byte
  artifacts (SHA-256 `8bb7981c6826cbfb225b9aaf3106ec647a3bd537160699cc4a60a2fe0bad4de4`).
- ConfigHub cross-product provider and real-Tk acceptance: 19 passed; the BFT
  session rendered the PySplashX application tab and all seven setup sections.
- Corrective release-contract regression: 12 passed; the delivery builder now
  rejects quotation marks and percent expansion tokens in batch-consumed
  content markers, and the installer parses the semantic
  version token from the branded `pysplashx 0.1.0 (build 13)` CLI response and
  compares it with the package version required by the delivery.
- Binding Windows Python 3.11 installer suite: 1,652 passed in 103.16 seconds;
  required
  coverage gate passed at 85.95% (85.0% required). Two non-failing Tk cleanup
  warnings were reported by pytest; no product or assertion failures occurred.
- Cross-product installation acceptance: 19 PyProjectMgr/ConfigHub tests and
  11 ConfigEditor tests passed; native and web desktop launchers were created.
- Governed delivery: 275 BFT files and 9 cross-product integration files.
  Independent clean extraction verified every delivery and integration manifest
  hash, plus the installer, build record, icon, Crex media, web component, and
  PySplashX wheel. The definitive archive checksum is shipped in the adjacent
  `.zip.sha256` sidecar.

## Publication status

This is a restricted internal release candidate. The Crex rights and
attribution gate recorded in the implementation note must be closed before any
public redistribution. Repository commit and tag actions remain reserved for
the authorized interactive release owner.
