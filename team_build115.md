# BFT v2.1 Build 115 — Team Summary

**From:** John, Lead Developer · **To:** Ringo (Owner), George (Architect), Paul (Analyst)
**Date:** 2026-08-25
**Kit:** `INSTALL_BUNDLETOOL_v2_1_115_selection_workspace.zip`
**Delivers:** v2.2 Selection Workspace **WP4 — the desktop workspace**

---

## Bundle mode is now a plan you can inspect

All seven regions from spec §7.1 are built and bound to one plan: action bar,
summary band, tri-state folder tree, rules-in-effect, filtered decision list,
inspector, footer. Both persona renders describe the same window, and the same
window serves both.

**1,169 → 1,378 tests. Coverage 91.42% → 91.29%**, after adding about a thousand
lines of UI.

## The screenshot case, finished

`.venv312` is **one row** with the badge `Python env` and a count that reads
**"not enumerated"** rather than a number. Selecting it says:

> Excluded because .venv312 is a Python env (pyvenv.cfg, Scripts/python.exe).
> Its contents were never enumerated, so nothing inside it was read or listed.
> This works regardless of folder name.

The button offers **"Scan this folder anyway"**, because descending is a re-scan,
not a rule override.

One deliberate divergence from the render, for George and Paul: the mock shows
"3,898 excluded" because it enumerated the environment. We prune before descent,
so a file count would be an invention — §7.4 forbids implying we inspected what
we skipped. The summary names pruned roots instead.

## A GUI that is actually tested

The existing frames sit outside the coverage gate because they need a display.
WP4 does not add to that pile: every rule of the workspace lives in a view-model
that imports **no toolkit at all**, so tri-state, override scoping, filtering,
undo and bulk scope are all verified headlessly.

| | coverage |
|---|---:|
| `ui/workspace_model.py` | **95%** |
| `ui/rule_editor.py` | **93%** |
| `ui/selection_workspace.py` | **85%** |

Thirty-one Tk tests run against the session-scoped root, none skipped — §18.3
is explicit that a skipped Tk test cannot count as acceptance.

## Two Ringo found while driving the build

**Open Bundle has been broken for any bundle over 2 MB since Build 112.**

```
UnbundleFrame.open_bundle.<locals>.<lambda>() got an unexpected keyword
argument 'cancel'
```

Build 112 taught `run_with_progress` to pass `cancel` and updated three of the
four work callables. Open Bundle kept `lambda progress=None:` and raised
`TypeError` before parsing a byte.

It survived three builds because it **only failed above the threshold**. Small
bundles skip the progress path and worked fine, so every quick test passed. The
failure was reserved for real files.

There is now a guard that reads the keywords `run_with_progress` actually passes
out of its own source and checks every call site against them, parameterised so
a failure names the file and line. Mutation-tested: putting the old lambda back
fails it. A 4.1 MB, 2,000-entry bundle now parses end to end.

George — this is the second time in one build that a *producer* contract passed
while a *consumer* had quietly disconnected. Your Build 109 register verifies
that anything accepting a `progress` sink emits monotonic progress, and it did
its job both times. What neither it nor anything else checked was whether the
caller still spoke the same language. Both halves now have a guard, and I think
that pairing is worth making a habit.

**The review dialog gave no way to settle blocked items.** Create Bundle asked
*"28 path(s) blocked... Create the bundle anyway?"* — but blocked paths were
never going in, so "anyway" implied a risk that does not exist, and the same
dialog returned every single time with no way to resolve it. It now offers
*Exclude blocked and continue* / *Continue* / *Cancel*, and acknowledging writes
an explicit exclude that appears in the selection report as a deliberate choice.

## Ringo caught a third: the progress bar had drifted out of the workspace

**The progress bar and Cancel button had drifted out of the new workspace.**

Ringo asked whether the PyThermX integration had drifted away. It had: the first
draft of the Selection Workspace had *zero* references to `run_with_progress`.
A 4,000-file scan would have frozen the window with no bar and no way to stop -
undoing Builds 107 through 112 on the surface that had just become the default.

Worth understanding why no gate caught it. George's Build 109 register guards the
*service*: any facade method accepting a `progress` sink must prove a monotonic
sequence, and `plan_bundle` does. The regression was one level up - the UI never
passed a sink. **A contract test on the producer says nothing about whether the
consumer connected it.** There is now an AST guard on the consumer side too.

Both long operations run behind the dialog with Cancel, honouring the Build 108
threshold. A cancelled scan leaves the previous plan untouched; a cancelled
bundle reports how far it got and what was left on disk.

## The defect I most want on the record

**The GUI hung on a modal dialog whenever the governed config drifted.**

`_report_config_integrity` carried the docstring *"never blocks startup"*
directly above a `messagebox.showwarning()` call, which blocks until someone
clicks it. One test run spent **265 seconds** waiting on that dialog. In the
field it is a hang, not a slow test — an unattended launch never returns.

Ringo hit the drift warning himself mid-build, which is what led me to it.

George: your Build 109 ruling that the alert must reach the GUI still stands,
and I think a **persistent banner** honours it better than a modal did. A modal
is dismissed once and forgotten; a banner stays while the drift does. stderr and
the status bar are unchanged. Flag it if you read the ruling differently — it is
one method, and two tests now guard that no blocking dialog returns to that path.

## Four more, all caught by gates

- **A checkbox took 478 ms on 4,000 paths.** A full re-decide costs ~430 ms and
  that is inherent, so the fix was to decide *less*: when only Layer 1 changed,
  only paths matched by an added or removed override can move. **478 → 128 ms.**
  Nine tests compare the fast path against the full one so the reasoning cannot
  quietly go wrong.
- **Uncheck a folder, re-check a child, nothing happened.** Layer 1 emitted every
  include before every exclude, so exclusion won every conflict no matter what
  the operator did last. Layer 1 is now ordered by action order.
- **Every folder override came out as "include."** The frame compared a folder's
  *tri-state* against the string `"Included"`, which is a *decision* state.
- **The safety confirmation never appeared.** It consulted `confirm_required`,
  which is only set once an override has already won — so before acting it was
  always False, and force-including a wheel never prompted.

The last three were all found by the dialog-flow tests on their first run.

## For Paul — SEL-X-001 is enforced

Seven flag combinations driven through the service, a real CLI subprocess and
the workspace, with ordered decisions compared. Plus: a selection built by
clicking is asserted to be reproducible by flag — the workspace's
`('exclude', 'docs/**')` equals `--force-exclude docs/**` — because §6 promises
scripts the same power as the desktop.

SEL-X-002 is structural: an AST check over all four adapters fails if any of
them constructs a `SelectionEngine`, assembles a governed rule stack, or walks
the filesystem itself.

SEL-GOV-001 is asserted by hashing the governed config before and after a full
session of overrides, presets, groups, bulk actions, undo/redo and a re-scan.

## Numbers

| | Build 114 | Build 115 |
|---|---|---|
| Tests | 1,169 | **1,378** |
| Coverage | 91.42% | **91.29%** |
| Checkbox toggle, 4,000 paths | — | **128 ms** vs 150 ms budget |
| Collapsed tree rows for 4,000 files | — | **41** |
| Install matrix | 4/4 | **4/4** |

## Scope held

WP5 (preview cache) and WP6 (preset persistence) are not in this build. The
footer deliberately says only *"selection plan computed without reading
content"* — the render's "Preview cache: 183 unchanged" is a WP5 figure, and
displaying a cache metric we do not have would be the same sin as inventing a
descendant count.

`ui.bundle_mode` in the governed config selects `workspace` (default) or
`classic`, so the Build 114 bundle frame remains reachable if anything is wrong
in the field.

## One thing I flagged rather than fixed

The shipped `bundle_config.json` does not pass its own validator —
`global_settings.ui_layout` is empty and `_validate_buttons_position` rejects the
absent key. It predates Build 114 and is latent because nothing calls
`validate()` on the load path. Out of WP4's scope; worth its own small build.

## Next

**WP5**, the incremental preview cache. The seam is ready: `metadata_scan`
returns plain data, planning is stateless, and there is already a gate asserting
that re-planning does not get slower — so the cache has something to prove
itself against.
