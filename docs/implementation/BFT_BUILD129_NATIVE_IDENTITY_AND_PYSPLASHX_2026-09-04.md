# BFT Build 129 native identity and PySplashX integration

**Date:** 2026-09-04  
**Lifecycle:** `ACTIVE_CANDIDATE`  
**Visibility:** `RESTRICTED_INTERNAL`

## Scope

Build 129 gives the Tk application the same sealed-bundle identity introduced
for the browser workspace and integrates the CompusaurusRex (Crex) startup
video through PySplashX 0.1.0 on the native and web surfaces. It also corrects
the web create-action state exposed during Build 129 acceptance. No integrity,
extraction, or progress contract changes in this build.

## Runtime design

PySplashX renders native video with Qt Multimedia while BFT's native workspace
uses Tkinter. BFT therefore follows PySplashX's supported Tk-host pattern:

1. BFT establishes its no-console startup log.
2. `core.splash.run_startup_splash()` writes a temporary relocation-safe
   profile with the packaged media path and per-user log path.
3. The selected BFT interpreter runs `python -m pysplashx run PROFILE` in an
   isolated child process.
4. After playback completes or is dismissed, BFT constructs the Tk workspace.

The child process has a 20-second ceiling. Missing PySplashX/PySide6, missing
assets, invalid profile JSON, process failure, playback failure, or timeout is
reported to the startup log and never prevents BFT from opening. The Windows
launcher probes its supported environments and prefers one containing both
PySplashX and PySide6. CLI commands call the same integration by default;
placing `--skip-splash` before the subcommand bypasses it for that command.
Setting `BFT_SPLASH=0` bypasses it for launchers or automation without changing
governed configuration.

The local web server uses PySplashX's packaged standards-based web component,
not Qt. BFT serves that module and the same MP4 through its authenticated
loopback session, including single-range byte responses for media seeking. The
video is muted, skippable by button or Escape, bypassed for reduced motion,
played on every new page load, replayable from the top bar, and fail-open after
15 seconds.

## ConfigHub contribution

The BFT Settings command requests two governed application tabs: **Bundle File
Tool** and **PySplashX**. PyProjectMgr's PySplashX provider verifies the
registered schema against the active PySplashX 0.1.0 package, derives editable
fields from that schema, validates the candidate through PySplashX's public
profile API, and reloads the committed profile plus its media before accepting
the transaction. A real-Tk acceptance test verifies all seven PySplashX setup
sections are rendered.

## Completed-plan action correction

The Build 128 browser gate required both a plan and a non-empty output field,
so the button shown in the user's completed-plan screenshot stayed disabled.
Build 129 enables **Create bundle** as soon as the plan is actionable. If the
output is empty, the action opens the native Save As bridge. BFT then performs
an incremental output-aware replan before creation; this reuses the scan but
applies `BLOCKED_ACTIVE_OUTPUT` if the chosen target already exists in the
source tree. This closes the UI defect without weakening self-bundle safety.

## Exact integrated assets

| Asset | Size | SHA-256 |
|---|---:|---|
| `src/ui/assets/bft-icon.png` | 46,704 bytes | `9a5039c6b1f3d8fc6661121b6695e90ca91120576b9d17fe03f09ffd058f7665` |
| `src/ui/assets/videos/crex_splash.mp4` | 1,892,621 bytes | `e3dcaf85cd50ca520268c7247825a69527a698084239e45b2204f0aab2aa3eff` |
| `src/web/static/pysplashx-splash.mjs` | 7,435 bytes | `0f1f9ff297050bab59951dda9ae25a8e73d2cf4f5f6af24523cd33807be59e82` |
| `vendor/pysplashx-0.1.0-py3-none-any.whl` | 35,511 bytes | `e07568eda58ca9f74f30149afcc18691f0bbf57095ac61a8aaac47bd6e6437bd` |

The MP4 is H.264 720 × 720 at 24 fps with AAC stereo audio and a 7.792-second
duration. The BFT profile uses fit aspect handling, rounded corners, centered
placement, click-to-close, and close-at-natural-end behavior.

## Dependency and delivery policy

The service layer and web workspace remain free of new required Python runtime
dependencies. PySplashX and PySide6 are an optional native-branding extra for
Tk and CLI; the browser uses PySplashX's dependency-free DOM adapter. The delivery carries the exact
PySplashX wheel; `scripts/setup_supported_envs.ps1` installs PySide6 6.11.1 and
both governed ThermX-family wheels into the Windows qualification matrix. macOS
setup installs its compatible PySide6 platform wheel before the local
PySplashX wheel.

The Build 129 installer always places and identity-checks PySplashX in existing
supported environments. It reports whether each environment has PySide6, but a
missing optional Qt runtime does not invalidate core BFT installation.

The first installation rehearsal exposed a CSS content marker containing
embedded quotation marks. Although the installed CSS bytes were correct, the
batch verifier interpreted the marker's quotes as command syntax and stopped at
Gate D. The marker is now quote-free, and the delivery builder rejects both
quotation marks and percent-expansion tokens in every batch-consumed marker.

The subsequent rehearsal reached the PySplashX identity gate and exposed a
second packaging-only assumption: PySplashX deliberately reports its product
and build identity as `pysplashx 0.1.0 (build 13)`, while the installer compared
the entire response with the bare semantic version. The gate now extracts the
version token and compares that token with the delivery's required version.

## Rights gate

The source PySplashX project records the Crex candidate as rights-pending. Its
inclusion here is an internal BFT integration authorized for this build, not a
public redistribution clearance. Before any public Build 129 publication, the
release owner must record ownership/license coverage for the video, audio,
fonts, and incorporated artwork plus any required attribution. Until then,
Build 129 remains a restricted internal candidate.
