# Build 133: readable rules and settings audit

## Requested behavior

Rules now offers **List matches**, enabled initially and remembered per user.
Each rule remains a parent row; its individual patterns appear as separate
child rows. Turning the option off restores the compact single-row display.
Result set initially selects **Included** in native and browser workspaces.
All, Excluded, and Blocked remain available.

Live browser acceptance caught a pre-existing capitalization mismatch: the
service serializes `Included`, `Excluded`, and `Blocked`, while Web used lowercase
filter/count keys. Counts, filtered rows, and state colors now normalize their
comparison keys while preserving readable state labels. The actual rendering
functions are exercised with a real serialized three-state service plan by
`tests/web/selection_rendering.cjs` (JSON plan on stdin).

## Settings audit and corrections

This review traced the exposed fields to their consumers rather than relying
only on schema validity. ConfigHub launched by BFT now requests **Bundle File
Tool**, **PyThermX (BFT)**, and **PySplashX**. The separate shared PyThermX
profile remains available to other applications.

### Bundle File Tool settings

| Settings | Consumer and behavior |
|---|---|
| `version`, `schema_version` | Release/schema identity; read only. |
| `global_settings.input_dir`, `output_dir` | Initial folders in native and Web; remembered source/save folders take precedence where applicable. Explicit operation paths take precedence. |
| `global_settings.log_dir` | Operational logger and log viewer. Relative paths resolve under the governed BFT root. Corrected the logger, which previously ignored this field. Restart an open application after changing it. |
| `global_settings.relative_base_path` | Legacy; now read only. The selected source root determines relative bundle paths. |
| `app_defaults.default_mode` | Native and Web initial mode. CLI subcommands explicitly select an operation. |
| `app_defaults.bundle_profile` | Default bundle serializer, `plain_marker` or `md_fence`. Removed unsupported `jsonl` from offered values and validation. |
| `app_defaults.add_headers` | Extraction header policy. Moved into Extraction in ConfigHub. Governed allowlists still restrict header insertion. |
| `app_defaults.encoding`, `eol` | Legacy; now read only. Source encoding and line endings are detected and preserved, not converted using these fields. |
| `app_defaults.overwrite_policy` | Extraction conflict behavior. Web now honors the configured default. Web labels `prompt` as “Stop on existing file,” matching its fail-closed behavior. |
| `app_defaults.dry_run_default` | Initial extraction dry-run state. Web now honors it instead of defaulting to writing files. |
| `app_defaults.treat_binary_as_base64` | Binary transport policy consumed by the core service. |
| `safety.allow_globs`, `deny_globs`, `max_file_mb` | Discovery/selection and service enforcement. Required safety rules cannot be weakened through ConfigHub. |
| `ui.bundle_mode` | Native workspace/classic interface choice; restart required. Web has its own interface. |
| `ui.layout`, `show_info_panel`, `show_log_panel` | Legacy; now read only. Current workspace tab visibility is a per-user preference; logs open from Tools. |
| `ui.progress.enabled`, `min_files`, `min_parse_mb` | Native Tk progress policy/thresholds. Browser progress is always displayed using NodeThermX. |
| `ui.progress.show_elapsed`, `show_rate` | Legacy; now read only. Use the BFT PyThermX profile's Tk/terminal controls. |

Legacy `session` and remembered-folder keys in the governed configuration are
not exposed as working settings. Runtime UI preferences live in per-user state:
last folders, workspace tabs, list/compact rule display, web skin, and startup
and checking preferences. Included is the initial filter, not a persisted filter.

The local governed input/output defaults still identify Ringo's Windows bundle
folder. They are retained as local preferences. Before distributing outside
this team, prepare neutral governed defaults and their manifest checksum; a
foreign machine must not inherit a developer's personal folder as its default.

### PyThermX (BFT)

The former tab edited the shared Therm project profile while BFT instantiated
hard-coded styles. BFT now owns `config/pythermx_profile.json`, using the exact
schema 1.1 supported by its qualified PyThermX 0.5.3 wheel.

| Settings | Consumer and behavior |
|---|---|
| Profile metadata | Profile/schema identity and validation. |
| `enabled` | Enables BFT terminal and native Tk progress. CLI `--progress none`, non-interactive auto mode, and native thresholds can still suppress it. |
| `defaults.surface` | Read only in BFT's tab; BFT explicitly chooses terminal or Tk for its entry point. |
| Terminal width, characters, brackets | CLI style and bar rendering. |
| Terminal visibility, count format, unit, elapsed, rate | CLI text rendering; a non-null unit overrides the operation's unit label. |
| Terminal spinner, timing, separator, history | CLI redraw, indeterminate progress, promotion and history behavior. |
| Tk width, height, minimum width, stretch, thickness, padding | Native dialog/widget geometry. Stretch now controls dialog resizing and widget packing. |
| Tk status alignment/position and visibility/count/unit/time/rate | Native renderer; unit is a presentation override when supplied. |
| Tk marquee and promotion separator | Indeterminate animation and promotion display. |
| Tk cancel controls | Native cancel presentation; operation support determines whether cancellation is available. |
| Tk palette | Native progress colors. |
| Advanced pump interval, drain budget, queue capacity | Passed through `tk_style()` to the native widget's bounded event pump. |

Browser progress uses NodeThermX and is not controlled by this PyThermX tab.
The qualified dependency is unchanged. ConfigHub's provider validates against
the corresponding packaged schema version and verifies commits by rereading.

### PySplashX

The bundled CRex MP4's video track reports **720 x 720**, a square aspect ratio.
The file has not been resized or replaced. The profile now specifies `rect`
and radius zero, which preserves square corners. Shape controls the display
outline; media dimensions determine its aspect ratio.

| Settings | Consumer and behavior |
|---|---|
| Profile metadata | Native/profile schema validation; no visual effect. |
| `enabled`, `interfaces.native.enabled`, `interfaces.web.enabled` | Respectively global/native/Web startup enablement. Native disablement is checked before probing multimedia dependencies. |
| Media type, sources, selected filenames | Native and Web use the selected configured asset. Relative source folders resolve against the profile. Web serves only the configured media/mask through session routes. |
| Video aspect mode | Fit/expand/ignore maps to Qt aspect mode and Web object fit. Display dimensions preserve the media ratio. |
| Video start/end positions and loop behavior | Both surfaces honor seek, bounded segment, close/freeze/replay. End zero means natural end. |
| Image duration | Both support selected images. Zero waits for dismissal, subject to BFT's startup cap. |
| Shape and rounded radius | Native region and browser clipping; radius applies to rounded shape. |
| PNG mask and threshold | Selected PNG alpha mask; threshold only applies to PNG-mask shape. |
| `geometry.is_native` | Native OS window frame/title bar, not original media size. Native only; browser overlays have no OS frame. Description corrected after tracing the Qt window flags. |
| Scale percent | Video: percentage of available display, preserving aspect. Image: percentage of original image dimensions; Web also bounds this to its viewport. |
| Position | Center is the supported schema value. Native display placement follows BFT's monitor resolver; Web centers within its page. |
| Close on click | Both surfaces. Web also retains explicit Skip and Escape. |
| Always on top, heartbeat | Native only, now described as such. |
| Log level/file | Native splash logging. Relative log files resolve under the per-user startup log directory; configured absolute paths are honored. |

BFT retains a **20-second startup cap** to avoid stranding application startup.
Browser reduced-motion preferences and blocked autoplay can skip the animation.
Missing/invalid optional media fails open. The browser reads the same profile
at bootstrap instead of using hard-coded shape/media settings. Reload Web after
changing it. Native reads the profile on its next launch.

## Qualification

The complete suite passed 1,697 tests on Windows Python 3.13 (85.73% coverage)
and 1,697 on Ubuntu Python 3.12 (85.13%). Both pass the 85% coverage gate.
The test harness reported one Windows and two Ubuntu Tk finalizer warnings;
these are not silently suppressed or counted as application acceptance failures.
After extending the installer guard to customized progress/splash profiles,
69 focused installer/settings/inspector checks passed on Windows. ConfigHub's
21 tests passed, including real Tk rendering and BFT-profile commit verification.
Native visual acceptance at 1000 x 720 confirmed readable per-pattern rows and
Included selected on opening Result set. MP4 track and AVC sample headers both
confirm 720 x 720 media dimensions.

The fresh/upgrade installer now protects customized PyThermX and PySplashX
profiles as well as governed application settings. Unmodified prior profiles
receive release defaults; customized profiles require explicit replacement,
and all replaced files are backed up.

A real Windows fresh Build 133 installation passed in a folder containing spaces.
A separate real Build 132 installation upgraded to 133 with a new runtime,
retained personal files/preferences, a verified 132 backup, and only the current
versioned installer in its active folder. Ubuntu's 12 installer checks also
passed, including customized-profile protection.

This is an internal release candidate. Native macOS acceptance still requires a Mac.
This PC retains stable WSL and the working Ubuntu browser launcher selected by
Ringo; the host's WSLg presentation problem is not an application fix.
No public release or Git commit is created by this delivery.
