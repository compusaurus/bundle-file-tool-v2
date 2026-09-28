# BFT v2.1 Build 113 — Build Record

**Kit:** `INSTALL_BUNDLETOOL_v2_1_113_selection_core.zip`
**Prepared by:** John, Lead Developer
**Date:** 2026-08-25
**Delivers:** v2.2 Selection Workspace **WP1 (Selection Core)** and **WP2 (Detectors)**, plus the SEL-PERF harness
**Authority:** `ARCH-RULING-2026-08-25-01`, `ARCH-RULING-ADDENDUM-2026-08-25-01`, `BFT-ANALYSIS-2026-08-25-02`, and Ringo's rulings of 2026-08-25
**Supersedes for installation:** Builds 106 through 112. See §8.

---

## 1. What Ringo settled, and what I built to it

Two decisions closed the design round:

1. **Paul's corrections supersede the addendum** on S-09 (exact Base64 expansion) and S-10
   (three-way stdout wording).
2. **The archives question goes my way.** Priority 0 holds only hazards that break the tool.

**897 → 983 tests. Coverage 90.17% → 90.73%.**

## 2. Priority 0 is now recursion hazards only

This is the ruling with the most consequence, so the reasoning is recorded in the code as well
as here.

| Priority 0 — non-overridable | Priority 5 — overridable, confirmation flagged |
|---|---|
| `**/*_bundle_*.txt`, `**/*_src_bundle*.txt`, `**/self_build*.txt` | `**/*.zip`, `**/*.tar`, `**/*.tar.*`, `**/*.whl`, `**/archives/**` |
| self-ingestion of the active output | 31 noise-reduction defaults |
| traversal outside the source base | |
| unreadable / invalid paths | |

A nested bundle is a genuine recursion hazard. An archive in a source tree is not — it makes
the bundle large. `**/*.whl` entered the deny list in **Build 107**, where I described it as
completing a hygiene rule so self-bundles would stop absorbing a vendored wheel. At Priority 0
this project could never have bundled its own `vendor/pythermx-0.5.0-py3-none-any.whl`.

Overriding an archive default is legitimate but should be deliberate, so the decision carries
`confirm_required=True` and an adapter can ask before proceeding. Two tests hold the line: one
proves a session force-include *cannot* defeat a recursion block, the other proves it *can*
carry a wheel through with confirmation.

## 3. WP1 — the selection core

`src/core/selection.py`. No renderer, no Tk, no CLI; the AST layering test covers it.

- **`SelectionRule` / `SelectionDecision` / `SelectionGroup` / `SelectionPlan`** as specified.
- **Eight-layer ladder**, `LADDER` evaluated highest-first, last-match-wins within a layer.
- **Every decision carries its chain** — every rule consulted, with the winner marked. That is
  what turns "4,084 files and I don't know why" into something inspectable.
- **Groups are evaluated strictly after inclusion** and only affect emission order.
- **Digests** (`S-08`): per-source and one ordered `rule_stack_digest`, over canonical JSON with
  sorted keys and no clock. Verified to stay **out of transport** — a digest planted in
  `BundleManifest.metadata` appears in neither profile's output.

### 3.1 A defect in my own enum, caught by the layer tests

The first `Layer` enum mixed two numbering schemes: 2a/2b became 20/25 while the other layers
kept the specification's 3–6. Numeric comparison then ran backwards — `PROJECT_RULES` compared
as *lower* priority than `USER_PRESET`.

The parameterised "every layer outranks every lower layer" test caught it immediately. It also
silently corrupted `confirm_required`, which asks whether an explicit user action won. Values
are now strictly increasing along the ladder and a `display` property carries the "2a"/"2b"
labels so the documents and the code still agree.

### 3.2 The `--include` allow-list correction, implemented

`base_action_for()` treats an allow-list as a **base-action switch**, not an ordinary rule.
`--include src/**` therefore drops everything else, exactly as Build 112 does today. Modelled
as a rule over an include-by-default base, every non-matching file would have survived and the
output would have silently broadened — which spec §11 promises will not happen.

## 4. WP2 — detectors

`src/core/detectors.py`. Conjunctive per family, as ratified:

| Family | Primary marker | Corroboration |
|---|---|---|
| `python-venv` | `pyvenv.cfg` | `Scripts/python*.exe` or `bin/python*` |
| `conda-env` | `conda-meta/` | `conda-meta/history` |
| `node-modules` | the directory | `package.json` at the parent |

`.venv`, `.venv312`, `env-app`, `venv313` and `myenv` all classify identically, because the
signature is authoritative and the name is not.

**A lone `bin/activate` yields `Unknown`, is traversed, indexed, and reported.** That case
decided the design: under the original disjunction, a repository with a checked-in activate
script would have had its entire subtree pruned before descent, so its files never reached the
index and the user could not see what was dropped. A guard test now fails if any family is ever
made confirmable by a single marker.

`DetectorLedger` carries pruned roots and ambiguous directories into the selection report with
evidence codes, because a pruned directory hides everything beneath it and the reason has to
survive.

## 5. The harness — and the gate it caught me failing

`tests/integration/test_selection_performance.py` makes `SEL-PERF-002` a real gate. Paul had
written it as *"the budget set by John's harness"*, which is not a gate until the number exists.

**My first implementation missed it by 8.6×.**

| | Before | After |
|---|---:|---:|
| 4,000-path plan (p50) | **4,306 ms** | **425 ms** |
| Single re-decision (p50) | 1.026 ms | **0.103 ms** |

Two causes, both mine. `decide()` called `_layer_rules()` per layer per path, and that sorted
the whole rule list every time — 32,000 sorts for one plan. And `matches()` expanded `**/` by
trying up to twelve generated patterns through `fnmatch`, so one rule cost twelve regex
operations. Rules are now bucketed once at construction, and each glob compiles to a single
cached regex with correct `**` semantics. **75 tests passed before and after**, which is the
evidence the rewrite preserved behaviour rather than merely getting faster.

Proposed and now enforced: **a 4,000-path plan within 500 ms p95** — 425 ms measured, ~18%
headroom.

### 5.1 A wall-clock gate under a line tracer measures the tracer

The gate passed standalone at 427 ms and failed inside the suite. Measured cause: `coverage`
line tracing costs **4.3×** on this workload (429 ms → 1,848 ms).

Relaxing the budget would have left no real gate; skipping under coverage would have meant it
never ran in the normal suite. Instead the untraced budget is authoritative, and the same
assertion runs against a scaled budget when `sys.gettrace()` is set — so the gate still fails
on a genuine regression in either mode. The factor and its measurement are recorded in the
file.

I also caught an `os.chdir()` in one timing test that would have leaked into every test after
it; it is now `monkeypatch.chdir`, which restores at teardown.

## 6. Two more test defects worth recording

Both were my expectations, not product faults, and both taught something:

- **`statted == 21` should have been 20.** I expected `pyvenv.cfg` to be counted — but the
  directory is classified from its markers *before* descent, so nothing inside it is ever
  statted. The corrected assertion is a better statement of what pruning means.
- **A group-reorder test proved nothing.** Overlapping patterns meant both orderings produced
  identical output, so it would have passed while testing nothing. Rewritten with disjoint
  groups that genuinely invert.

## 7. What is not in this build

WP3 (service and CLI), WP4 (desktop workspace), WP5 (incremental cache), WP6 (presets and
groups persistence). The plan engine is deliberately I/O-free, which is what will let WP5's
cache sit above it without re-planning.

Also unresolved and worth a ruling before WP3: **the package version identity for v2.2.** This
build is `2.1.113` because build numbers are monotonic and D-004 makes the payload own the
version. The feature program is called v2.2. Someone should say whether the workspace ships as
`2.2.0` and, if so, at which work package the minor version turns over.

## 8. Supersession and the matrix

Gate A0 accepts `2.1.105` through `2.1.113`. Payload is a strict superset of the 106–112 kits.
The installer gains a WP1/WP2 import smoke check before the suite gate.

Representative predecessors exercised end to end: **2.1.105, 2.1.108, 2.1.111, 2.1.112** — the
oldest supported, the Layer C boundary, the pre-cancellation build, and the immediate
predecessor.

## 9. Payload — 47 files

New: `src/core/selection.py`, `src/core/detectors.py`,
`tests/unit/test_selection_core.py`, `tests/unit/test_detectors.py`,
`tests/integration/test_selection_performance.py`. Plus every version surface and the Build
106–112 superset.

## 10. Evidence

```
983 passed in 33.46s
Required test coverage of 85.0% reached. Total coverage: 90.73%
src\core\selection.py   244 stmts  11 miss  94%
src\core\detectors.py    90 stmts   2 miss  98%
```

- 86 new tests: 55 selection core, 20 detectors, 7 performance gates, 4 carried adjustments.
- WP1 exit gate — deterministic precedence across **100% of rule layers** — met by a
  parameterised test that asserts each layer beats every layer beneath it.
- WP2 exit gate — `.venv312` pruned before descent with **zero content reads** — met; the
  300-file `site-packages` subtree is never statted.
- Governed config digest `0458fbca…`; manifest `6e2860e2…`; helper block `380037a3…` verified
  before assembly and re-hashed after.
