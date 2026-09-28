# BFT v2.1 Build 115 — Build Record

**Kit:** `INSTALL_BUNDLETOOL_v2_1_115_selection_workspace.zip`
**Prepared by:** John, Lead Developer
**Date:** 2026-08-25
**Delivers:** v2.2 Selection Workspace **WP4 — Desktop Workspace**
**Authority:** `BFT_SELECTION_WORKSPACE_DESIGN_SPEC` §7–§9, §18; `ARCH-RULING-2026-08-25-01`
and addendum; Ringo's rulings of 2026-08-25
**Supersedes for installation:** Builds 106 through 114. See §10.

---

## 1. What this build is

Bundle mode becomes a Selection Workspace, per spec §7.1. The seven regions of
the render are all present and bound to one plan: action bar, summary band,
tri-state folder tree, rules-in-effect panel, filtered decision list, inspector
and footer. Both persona renders — §8 developer and §9 writer — describe the
same window, and the same window serves both.

**1,169 → 1,378 tests. Coverage 91.42% → 91.29%**, having added roughly a
thousand lines of UI.

## 2. The architecture that makes a GUI testable

`src/ui/bundle_frame.py` and its siblings are excluded from the coverage gate
because they need a display; everything in them is unmeasured. WP4 does not add
to that pile.

| Module | Toolkit | Coverage |
|---|---|---:|
| `ui/workspace_model.py` — every rule of the workspace | none | **95%** |
| `ui/rule_editor.py` — preview, review render, dialogs | Tk for dialogs only | **93%** |
| `ui/selection_workspace.py` — widget construction and binding | Tk | **85%** |

The view-model imports no toolkit at all — asserted by a test that parses its
imports — so tri-state computation, override scoping, filtering, undo history
and bulk scope are all verified headlessly. The Tk layer is thin enough that
what remains uncovered is widget plumbing rather than behaviour.

**Tri-state is drawn as text** (`[x]`, `[-]`, `[ ]`), not colour. §7.2 requires
that colour never carry meaning alone, and it is also what makes the tree
assertable in a test.

## 3. The screenshot case, finished

`.venv312` appears as **one excluded root** carrying the badge `Python env`,
with the count column reading **"not enumerated"** rather than a number.

That wording is deliberate and §7.4 demands it: BFT must not imply it inspected
files it intentionally did not walk. The render shows "3,898 excluded" because
its mock enumerated the environment; we prune before descent, so a file count
would be an invention. The summary band names pruned roots instead.

Selecting the folder explains it:

> Excluded because .venv312 is a Python env (pyvenv.cfg, Scripts/python.exe).
> Its contents were never enumerated, so nothing inside it was read or listed.
> This works regardless of folder name.

The offered action is **"Scan this folder anyway"** — descending is a re-scan,
not a rule override, and the button says so.

## 4. Nine defects found, eight of them real

Two were found by Ringo driving the build rather than by a gate, and one of those had been shipped for three builds. Both are recorded first.

### 4.1 Open Bundle failed on every bundle over 2 MB — shipped since Build 112

**Found by Ringo, on his own tree.** Opening any bundle above the progress
threshold died instantly with:

```
Failed to parse bundle:
UnbundleFrame.open_bundle.<locals>.<lambda>() got an unexpected keyword
argument 'cancel'
```

Build 112 taught `run_with_progress` to pass `cancel` to its work callable and
updated three of the four call sites. The fourth — Open Bundle — kept its
`lambda progress=None:` signature, so the call raised `TypeError` before a byte
was parsed.

It survived three builds because **it only failed above a threshold**. Bundles
under 2 MB skip the progress path entirely and worked perfectly; every quick
test used a small fixture. The failure was reserved for real files, which is
the worst possible distribution for a defect.

Fixed, and `allow_cancel=False` is now passed because `parse_file` has no
cancellation seam — rendering a Cancel button that cannot be honoured would be
worse than rendering none.

**The guard matters more than the fix.** `test_progress_callable_arity.py` reads
the keywords `run_with_progress` actually passes out of its own source, then
parses every `run_with_progress` call site in `src/ui` and asserts each work
callable accepts them. It is parameterised per call site, so a failure names the
file and line. Verified by mutation: reintroducing the old lambda fails two
tests. Verified end to end: a **4.1 MB, 2,000-entry bundle** now parses through
the dialog's exact calling convention.

George's Build 109 register cannot catch this class — it verifies *producers*
emit monotonic progress, and every producer here was correct. This is the
consumer-side half.

### 4.2 The review dialog gave no way to settle blocked items
**Found by Ringo, from a screenshot.** Create Bundle raised a Yes/No box reading
*"This selection still has open items: 28 path(s) blocked as recursion hazards.
Create the bundle anyway?"*

Wrong twice over. Blocked paths are held at Priority 0 and were never going into
the bundle, so "anyway" implied a risk that does not exist. And there was no way
to resolve the warning — the identical dialog returned on every Create Bundle,
forever, which trains people to click through it without reading.

The review is now a purpose-built dialog with three outcomes, because there are
genuinely three things an operator might mean:

| | |
|---|---|
| **Exclude blocked and continue** | records the decision, settles the warning |
| **Continue** | proceed as-is, warning stands |
| **Cancel** | go back and look again |

`acknowledge_blocked()` writes an explicit exclude for each blocked path. That
changes no decision — Priority 0 is not overridable — but it records the
operator's acknowledgement and shows up in the selection report as a deliberate
choice rather than an unread warning. The wording changed too: the reason now
reads *"these cannot be included and will be left out"*.

### 4.3 The progress bar and Cancel button had drifted out of the new surface

**Found by Ringo, by asking.** The first draft of the Selection Workspace had
*zero* references to `run_with_progress`. Scanning a 4,000-file tree would have
frozen the window with no bar and no way to stop it - quietly undoing Builds 107
through 112 on the surface that had just become the default for bundle mode.

The Build 109 progress register could not catch this. It guards the *service*:
every facade method that accepts a `progress` sink must prove a monotonic
sequence, and `plan_bundle` does. The regression was one level up - the UI simply
never passed a sink. A contract test on the producer says nothing about whether
the consumer connected it.

Both long operations now run behind the PyThermX dialog with a Cancel button, and
honour the Build 108 threshold so eleven files stay inline. A cancelled scan
leaves the previous plan untouched; a cancelled bundle reports how far it got and
what was left on disk, as Build 112 requires - a cancelled run is a third
outcome, not a failure.

Four tests now guard it: an AST check that both `rescan()` and `create_bundle()`
call `run_with_progress`, one that both offer cancellation, and two behavioural
tests for the cancelled paths.

### 4.4 The GUI hung on a modal dialog when the config drifted

`_report_config_integrity` carried the docstring *"never blocks startup"* directly
above a call to `messagebox.showwarning()`, which blocks until someone clicks it.
Any unattended launch against a drifted config waited forever.

Measured: **one test spent 265 seconds** sitting on that dialog. In the field it
would have been a hang, not a slow test — a kiosk, a scripted smoke test or a CI
probe would simply never return.

George's Build 109 ruling requires the alert to reach the GUI, so it is now a
**persistent banner** across the top of the window. That honours the ruling more
faithfully than a modal did: a banner cannot be dismissed and forgotten while
the drift is still present. stderr reporting and the status-bar text are
unchanged. With real drift present, startup is now **1.4 s**.

This predates WP4; my config edit merely exposed it. Two tests now guard it —
one parses `_report_config_integrity` for blocking calls, the other asserts the
alert still reaches both stderr and the GUI.

### 4.5 A checkbox took 478 ms on a 4,000-path tree

The WP4 exit gate is "4,000-path UX", and the first implementation missed it by
3.2×. Profiling was unambiguous:

| | |
|---|---:|
| full re-decide of 4,000 paths | 432 ms |
| everything in the view-model combined | 32 ms |

A full re-decide costs what it costs — ~0.1 ms per path is SEL-PERF-002's
measured figure. So the fix was not to make deciding faster but to **decide
less**: when only Layer 1 changed, only paths matched by an override pattern
that was added or removed can move.

The argument is exact, not a heuristic. `decide()` evaluates each path
independently and records a chain entry only for rules that actually match it,
so a path under no Layer 1 pattern — old set or new — consults an identical rule
list in an identical order and produces a byte-identical decision.

**478 ms → 128 ms p50, a 4× improvement**, and nine tests compare the incremental
path against the full one across varied override sequences so that if the
reasoning is ever wrong a test fails rather than a bundle changing quietly.

### 4.6 Unchecking a folder then re-checking a child did nothing

`session_rules` emitted every include before every exclude, and Layer 1 is
last-match-wins — so exclusion won every conflict regardless of what the
operator did last. In a tri-state tree that reads as a broken checkbox.

Layer 1 now takes an **ordered** `(action, pattern)` sequence: the operator's
action order *is* the rule order. The CLI's `--force-include` / `--force-exclude`
keep their existing meaning and are folded into the same sequence.

### 4.7 Every folder override came out as "include"

The frame decided direction with `view.state != "Included"`. A file reports a
*decision* state; a folder reports a *tri-state* (`checked`), which never equals
`"Included"` — so unchecking a folder from the inspector included it instead.

Direction is now the model's to answer, through one rule that serves both:
`desired_state()` — "not currently fully checked".

### 4.8 The confirmation for a safety override never appeared

The frame consulted `decision.confirm_required`, which is only set once an
override has **already won**. Asked before acting, it was always `False`, so
force-including a wheel past the archives default never prompted.

`needs_confirmation(path, include)` now asks of the *proposed* action, against
the `CONFIRM_ON_OVERRIDE` patterns.

### 4.9 A mistyped source folder planned successfully for nothing

`plan_bundle` scanned a non-existent directory to an empty result and reported
success. The CLI happened to check existence first; the workspace did not, so a
typo produced a confident plan for zero files. The service now refuses a source
that does not exist, which fixes it for every caller.

## 5. Acceptance criteria (§18)

| Criterion | Where |
|---|---|
| SEL-F-001 environment classified by signature, excluded | `test_the_environment_appears_as_one_excluded_root` |
| SEL-F-002 every decision exposes state, rule, layer, override | `test_every_row_carries_state_rule_and_layer` |
| SEL-F-003 folder action = one scoped override, no per-file mutations | `test_unchecking_a_folder_creates_exactly_one_override` |
| SEL-F-004 views and counts reconcile with the plan | `test_view_counts_match_the_plan_exactly` |
| SEL-F-005 groups give deterministic order, no duplicates | `test_groups_change_emission_order_only` |
| SEL-F-006 text and JSON reports reconcile | `test_the_review_reconciles_with_the_json_report` |
| SEL-X-001 service, CLI and Tk agree | 7 parameterised cases + rules-file and override cases |
| SEL-X-002 no adapter reimplements precedence | AST checks over all four adapters |
| SEL-GOV-001 runtime never writes governed policy | digest before/after a full session |
| SEL-GOV-003 project rule file is inactive until opted in | export test round-trips through `load_rules_file` |

**SEL-X-001 is the one worth naming.** Seven flag combinations are driven
through the service, a real CLI subprocess and the workspace, and their ordered
decisions compared. A selection built by clicking is also checked to be
reproducible by flag — `('exclude', 'docs/**')` in the workspace equals
`--force-exclude docs/**` on the command line — because §6 promises scripts the
same power as the desktop.

## 6. SEL-PERF-005 — the 4,000-path UX gate

| Gate | Measured | Budget |
|---|---:|---:|
| Checkbox toggle, 4,000 paths, p50 | **128 ms** | 150 ms |
| Search across 4,000 decisions, p95 | **< 20 ms** | 150 ms |
| Collapsed tree rows produced | **41** | < 50 |
| Files read during a toggle | **0** | 0 |
| Vendored subtree statted | **0 of 500** | 0 |

The tree is lazy: a collapsed 4,000-file plan produces 41 rows, not 4,000.
Building every descendant up front is the obvious implementation and the reason
large trees feel frozen.

The accessibility half of the gate is asserted too — every focusable row can
state its own label, state and reason as text.

## 7. Configurable, per standing direction

`ui.bundle_mode` in the governed config selects `workspace` (default) or
`classic`. Replacing the most-used surface outright would leave no way back if
something is wrong in the field; the Build 114 bundle frame is retained and
selectable.

## 8. What is not in this build

**WP5** (incremental preview cache) and **WP6** (preset and group persistence).
The footer says only *"selection plan computed without reading content"* — the
render's "Preview cache: 183 unchanged · 3 changed" is a WP5 figure and this
build must not display a cache metric it does not have. The rule editor edits
**session** overrides and exports a project rule file; saving personal presets
is WP6.

Also unresolved, flagged not fixed: the shipped `bundle_config.json` does not
pass `ConfigManager.validate()` — `global_settings.ui_layout` is empty and the
validator rejects the absent `buttons_position`. It predates Build 114 and is
latent because nothing calls `validate()` on the load path.

## 9. Evidence

```
1378 passed in 76.69s
Required test coverage of 85.0% reached. Total coverage: 91.29%
src\ui\workspace_model.py       449 stmts  14 miss  95%
src\ui\rule_editor.py           218 stmts   9 miss  93%
src\ui\selection_workspace.py   354 stmts  41 miss  85%
src\core\service.py             261 stmts   5 miss  98%
```

209 new tests: 63 view-model, 31 workspace Tk, 43 dialog flows, 10 progress-arity guards, 20 rule editor,
20 cross-surface parity, 7 performance and accessibility, 15 incremental-replan
equivalence.

Governed config digest `100fdca1…`; manifest `561f5008…`; helper block
`380037a3…` verified before assembly and re-hashed after.

## 10. Supersession and the matrix

Gate A0 accepts `2.1.105` through `2.1.115`. Payload is a strict superset of the
106–114 kits. Gate E gains a WP4 import check and a headless workspace
construction before the suite gate.
