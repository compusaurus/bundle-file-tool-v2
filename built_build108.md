# BFT v2.1 Build 108 — Build Record

**Kit:** `INSTALL_BUNDLETOOL_v2_1_108_pythermx_tk.zip`
**Prepared by:** John, Lead Developer
**Date:** 2026-08-23
**Responds to:** Ringo — "is the current version of pythermx integrated fully into Bundle
File Tool now?"
**Supersedes for installation:** Builds 106 and 107. See §9.

---

## 1. The honest answer to the question

No, it was not. Two gaps, and the second is the one that mattered.

**PyThermX had moved on.** Build 107 vendored 0.2.0. The current release is **0.3.1**, and
the 0.2.0 wheel is no longer in `therm/dist/`.

**The GUI had no progress at all.** Build 107 integrated the CLI only; built_build107.md §12
recorded the Tkinter adapter as out of scope. Since Ringo's original complaint was about a
GUI operation, the half that shipped was not the half that was asked for.

Build 108 closes both.

## 2. A pin that could not fail

Worth recording, because the test was mine and it was ineffective.

Build 107 shipped `pythermx>=0.2.0,<0.3` and a test asserting the declared floor was
`>=0.2.0` and that the installed version was at least 0.2. When 0.3.1 was installed, the
environment **violated the shipped pin** and the suite stayed green — a floor check cannot
detect an upper-bound breach.

`test_installed_pythermx_satisfies_the_declared_pin` now evaluates the real specifier with
`packaging`, against the actually-installed version. That catches the whole class, not the
instance.

## 3. Why the GUI needed a thread, not just a widget

The UI called `discover_files()` directly from the button handler. Tk could not process a
single event until the walk finished. **The missing feedback was a blocked event loop, not a
missing widget** — dropping a progress bar into that handler would have painted one frame and
then frozen with the rest of the window, which is worse than nothing because it looks like a
hang with a bar on it.

So the work moved to a worker thread. PyThermX 0.3.0 supplies exactly this seam and is
explicit about the division:

> Only immutable values cross the channel, so a worker cannot reach the deliberately
> non-thread-safe model; the pump constructs and mutates models on the UI thread. **The
> adapter creates no threads of its own.**

We create the thread, because PyThermX deliberately does not. `run_with_progress()` owns the
whole arrangement: worker posts to the channel, pump drains onto the UI thread, a nested
`update()` loop keeps the window painting, and the worker's return value or exception is
handed back on the calling thread.

Re-raising matters. The call sites are wrapped in `try/except` that shows a message box; had
the thread boundary swallowed exceptions, a failed bundle would have reported success.

## 4. One event stream, two adapters

`src/ui/tk_progress.py` makes the same decisions as `src/cli_progress.py`, because the
semantics belong to the event stream rather than to either renderer:

| Event | CLI | Tkinter |
|---|---|---|
| New phase | new `ThermometerCore` | `post_begin(PhaseSpec(...))` |
| Indeterminate → total known | `promote()` | `post_promote(...)` |
| Ordinary tick | `update()` | `post_update(...)` |
| `PHASE_COMPLETE` | `finish()` | `post_message(...)` |

Phase labels are imported from the CLI adapter rather than duplicated, so a phase is never
named two different things on two surfaces.

The layering test now covers the new module too: no file under `src/core/` may import
`tkinter`, `pythermx`, `pythermx.tk`, `cli_progress` or `ui.tk_progress`.

## 5. Configurable, per the standing rule

Two new governed keys, in `bundle_config.json` and `ConfigManager.DEFAULT_CONFIG`:

```json
"ui": { "progress": { "enabled": true, "min_files": 200,
                      "show_elapsed": true, "show_rate": true } }
```

`min_files` exists because a modal dialog for eleven files is worse than no dialog. Discovery
is exempt from the threshold — it cannot know its size until it has finished, which is the
whole reason it reports indeterminate progress in the first place.

## 6. Coverage scope corrected

`src/ui/*` was omitted wholesale since Build 104, with the recorded reason "requires a
display, has no automated coverage today". That is no longer true of `tk_progress.py`, which
is tested against a real widget and a real Tk root.

Leaving it inside the blanket omit would have done two bad things at once: understated the
real UI gap, and excused the new code from the gate. The omit now names the four untested
frames explicitly; `tk_progress.py` is measured at **91%**, and total coverage went **up**.

## 7. Governance drift, found again — provenance confirmed

While running the gate I found `bundle_config.json` overwritten **today at 11:54:52**:
`version` reverted to `2.1.0` and `safety.allow_globs` replaced by an allow-list.

**Provenance identified** (after Ringo recalled having used the tool itself today). The
drifted document is the Build-104-era configuration archived inside
`C:\Users\mpw\Python\bundles\BFTv2_v2.1 Build 104_bundle.txt`. Parsed out of that bundle and
compared field by field, the two are identical in every value — `version` `2.1.0`, the
14-entry allow-list, `window_geometry` `1902x980+-3+24`, `first_launch`,
`last_bundle_save_dir` — except one: `last_source_dir`, which today reads
`.../bundle_file_tool_v2/scripts`.

That geometry string exists in only two places on the disk: inside that bundle, and in the
saved copy from the 2026-08-18 drift incident. No current default produces it.

**pyprojectmgr is cleared.** A reasonable first suspicion, since a scan did run that morning,
but three independent checks rule it out: BFT's own `.pyprojectmgr/logs/pyprojmgr.log` and
`assets.db` were last written 2026-08-20; no pyprojectmgr log mentions `bundle_file_tool`, and
its only run in that window (11:59:49) scanned its own directory *after* the overwrite; and its
source contains no reference to `bundle_config.json`.

**The installed build is cleared too, and this was verified rather than assumed.**
`ConfigManager.save()` raises `ReadOnlyConfigError` unconditionally, `_create_default_file()`
is creation-only and never overwrites an existing file, and nothing under `src/` calls
`.save()`. The installed 2.1.107 could not have produced this document.

What remains is an **older Bundle File Tool** — the pre-Build-104 whole-document save that
wrote UI state into the governed config — operating on this project root. That matches Ringo's
recollection, and it means the mechanism is exactly the one Builds 104 and 105 removed, still
alive in a copy those builds never reached.

**Correction to this record.** An earlier draft of this section said only `bundle_config.json`
changed today. That was wrong, and the error was mine: I read it from a listing I had
truncated with `head -20`. `src/core/config_ids.py` and `src/core/static_ids.py` also carry
today's mtime (11:53:32). Their content is byte-identical to the 2026-08-20 snapshot and their
headers still read *Generated: 2026-08-18*, so they were rewritten with identical bytes rather
than altered. Nothing was lost in either file.

This is the fourth recurrence. Build 105 anchored *this* installation's config resolution to
its own application root, which protects the installed copy but cannot protect the file from a
different, older copy on the same disk. Closing it properly means the governed file has to
defend itself — **George**, that is a design question, and I would rather raise it than patch
around it a fifth time. The cheapest useful step is a load-time record of the file's SHA256 and
the writing process's identity, so a fifth occurrence names its own cause instead of costing an
afternoon of forensics.

## 7a. A Build 107 defect, found while verifying the demo commands

`unbundle --progress bar` drew nothing. The flag parsed, the writer emitted
events, and the sink never reached `extract_manifest` - my Build 107 edit to
that call site silently failed to apply and the script's assertion was too
coarse to notice.

Two things let it ship, and both are worth naming:

1. **`emit()` swallows sink failures by design.** That is correct for a
   diagnostic which must never break the operation it observes. It also means
   "no sink" and "working sink" are indistinguishable from the inside - nothing
   raises, nothing logs, the extraction succeeds.
2. **The Build 107 tests called `extract_manifest(progress=...)` directly.**
   They proved the writer emits. Nothing proved the *command* passes a sink.

`test_cli_unbundle_renders_progress` now runs the real command and asserts a
bar appears on stderr. Restoring the defect makes it fail with
`the extract phase drew no thermometer`, so it holds the line rather than
merely describing it.

The bundle path was correct throughout; only extraction was affected, and only
the display - no bundle or extraction ever produced wrong output.

## 8. Payload — 23 files

| # | File | Change |
|---|---|---|
| 1 | `src/ui/tk_progress.py` | **New.** Tkinter adapter and `run_with_progress` |
| 2 | `src/ui/bundle_frame.py` | Scan and read on a worker thread; threshold helper |
| 3 | `src/ui/unbundle_frame.py` | Extract on a worker thread; threshold helper |
| 4 | `tests/unit/test_pythermx_tk_integration.py` | **New.** 37 tests |
| 4a | `src/cli.py` | **Fix:** unbundle now passes the progress sink (see 7a) |
| 5 | `vendor/pythermx-0.3.1-py3-none-any.whl` | **Replaces** the 0.2.0 wheel |
| 6 | `pyproject.toml` | Pin `>=0.3.1,<0.4`; coverage scope narrowed |
| 7 | `bundle_config.json`, `src/core/config.py` | `ui.progress` keys |
| 8 | `tests/unit/test_pythermx_integration.py` | Real specifier evaluation |
| 9–23 | Version surfaces and the Build 106/107 superset | |

**Gate C2** is new: placement copies files but never removes them, so upgrading from Build
107 would leave `pythermx-0.2.0` sitting in `vendor/` beside 0.3.1. The installer deletes it
and fails if it cannot.

## 9. Supersession

Gate A0 accepts `2.1.105`, `2.1.106`, `2.1.107` and `2.1.108`. The payload is a strict
superset of both earlier kits. `PREP_AND_STAGE_BFT.bat` requires **exactly one**
`INSTALL_BUNDLETOOL_*.zip` in Downloads, so the Build 106 and 107 zips must be moved out
before staging this one.

## 10. Evidence

```
702 passed in 10.04s
Required test coverage of 85.0% reached. Total coverage: 90.29%
src\ui\tk_progress.py   85 stmts   8 miss   91%
```

- Build 107 baseline: 661 passed, 90.23%. Build 108: 702 passed, 90.29%. 41 new tests.
- All 661 Build 107 tests pass unchanged against PyThermX 0.3.1, which is the expected
  result: `thermometer_core.py` is byte-identical to the 0.2.0 release commit and a
  release-contract test in the therm project enforces that.
- Real-app smoke: `BundleFileToolApp` constructs, the scan runs on thread `bft-progress`
  (not `MainThread`), the first event is `('discover', None)` and the last is
  `('discover', 32)` — the handoff — and no `Toplevel` is left behind.
- Helper block `380037a3…`, verified against the canonical include and re-hashed after
  assembly.

## 11. Open items

- **George**: the `OperationProgress` contract-shape ruling (built_build106.md §8) is still
  open. Two adapters now consume it, so a change costs two files rather than one.
- **George**: the governed-config self-defence question in §7.
- **WP5**, migrating the CLI onto `BundleToolService`, remains separate and unstarted.
- The GUI has no **cancel** path. `run_with_progress` disables the dialog's close button
  rather than offering a control that would do nothing. Cancellation needs cooperative
  checks inside `discover_files`/`create_manifest`, which is a core change and its own build.
- The Web adapter, the third consumer Paul named, is still unwritten.
