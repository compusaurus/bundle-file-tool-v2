# BFT v2.1 Build 113 — Team Summary

**From:** John, Lead Developer · **To:** Ringo (Owner), George (Architect), Paul (Analyst)
**Date:** 2026-08-25
**Kit:** `INSTALL_BUNDLETOOL_v2_1_113_selection_core.zip`
**Delivers:** v2.2 Selection Workspace **WP1 + WP2**, and the SEL-PERF harness

---

## The design round is closed and the foundations are built

Ringo settled both open questions, so I built to them:

- **Paul's corrections supersede the addendum** on payload estimation and stdout wording.
- **Priority 0 holds recursion hazards only.** Archives stay overridable.

**897 → 983 tests. Coverage 90.17% → 90.73%.** Installed cleanly over 2.1.105, .108, .111 and
.112 with all version surfaces unified.

## What now works

**A directory is recognised by what it is, not what it is called.** `.venv`, `.venv312`,
`env-app`, `venv313`, `myenv` — all classify as Python environments from `pyvenv.cfg` plus an
interpreter layout. The screenshot case is now a test.

**Nothing is excluded without a reason you can read.** Every path carries its state, the rule
that decided it, and the full chain of rules consulted on the way:

```
.venv312/Lib/site-packages/pytest/__init__.py: Included
  -> [1] session override: force-include (include .venv312/**)
     [4] shipped preset: python-env (exclude .venv312/**)
     [5] governed default: deny:**/__pycache__/** (exclude …)
```

**A lone `bin/activate` is reported, not pruned.** That single case decided the detector design.
A repository can legitimately check in an activate script; under the original any-marker rule
its whole subtree would have been skipped before descent, so its files never reached the index
and you could not see what was dropped — let alone override it.

## Ringo's archives ruling, and what it protects

Priority 0 now holds only what breaks the tool: nested bundle text, self-ingestion of the file
being written, traversal outside the source, unreadable paths.

Archives — `.zip`, `.tar*`, `.whl`, `archives/**` — sit at Priority 5, overridable, with the
override flagged as one worth confirming. The concrete case: `**/*.whl` entered the deny list in
Build 107 as hygiene, to stop self-bundles swallowing a vendored wheel. At Priority 0 this
project could never have bundled its own `vendor/pythermx-0.5.0-py3-none-any.whl`.

So: you can force-include a wheel, and the tool asks first. You cannot force-include a nested
bundle, ever.

## For Paul — SEL-PERF-002 has a number, and it caught me

You asked me to reconcile the gates with harness results. `SEL-PERF-002` read *"the budget set
by John's harness"*, which is not a gate until the number exists.

**My first implementation missed it by 8.6×.**

| | Before | After |
|---|---:|---:|
| 4,000-path plan | 4,306 ms | **425 ms** |
| Single re-decision | 1.026 ms | **0.103 ms** |

Both causes were mine: the engine re-sorted its whole rule list for every layer of every path
(32,000 sorts per plan), and the glob matcher fired up to twelve `fnmatch` calls per pattern.
Rules are bucketed once now, and each glob compiles to one cached regex. **75 tests passed
before and after** — that is the evidence the rewrite changed speed and not behaviour.

The gate is now **500 ms p95 for a 4,000-path plan**, enforced in the suite.

Your §7.1 fixture names are what I wrote the detector tests against, so our fixtures should
converge rather than diverge when Revision 1.1 lands.

## For George

Everything ratified in the addendum is implemented as ruled: conjunctive per-family detectors
with `Unknown` for ambiguous markers and evidence codes in the report; the two-tier ladder;
2a before 2b; digests that stay out of transport (verified — a digest planted in manifest
metadata appears in neither profile's output).

One item still needs a word, and it is not urgent: **the package version identity for v2.2**.
This build is `2.1.113` because build numbers are monotonic and D-004 makes the payload own the
version, but the feature programme is called v2.2. Someone should say whether the workspace
ships as `2.2.0`, and at which work package the minor turns over. Better decided before WP3
than during it.

## Four defects the process caught before you saw them

Recorded plainly, because all four would otherwise have shipped:

1. **My `Layer` enum compared backwards.** 2a/2b became 20/25 while other layers kept 3–6, so
   `PROJECT_RULES` ranked *below* `USER_PRESET`. The parameterised layer test caught it, and it
   had also been silently corrupting the confirm-on-override check.
2. **A timing gate under a line tracer measures the tracer.** The plan gate passed standalone at
   427 ms and failed in the suite; `coverage` costs a measured 4.3× on this workload. Relaxing
   the budget would have left no gate, so the untraced number is authoritative and the same
   assertion runs scaled when tracing is active.
3. **An `os.chdir()` in a timing test** would have leaked into every test after it.
4. **A group-reorder test proved nothing** — overlapping patterns made both orderings identical,
   so it passed while testing nothing. Rewritten with disjoint groups.

## Numbers

| | Build 112 | Build 113 |
|---|---|---|
| Tests | 897 | **983** |
| Coverage | 90.17% | **90.73%** |
| Upgrade paths proven | 7 | **4 representative** (105, 108, 111, 112) |
| Required dependencies | none | none |

`selection.py` 94%, `detectors.py` 98%.

## Next

WP3 (service facade and `plan` command) is the natural next step, and the plan engine was built
I/O-free specifically so WP5's cache can sit above it without re-planning. I would like the
version-identity question answered before WP3 starts.
