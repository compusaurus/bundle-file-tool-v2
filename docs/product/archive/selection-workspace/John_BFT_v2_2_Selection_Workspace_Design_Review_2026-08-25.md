# Developer Design Review — BFT v2.2 Selection Workspace

**Document Ref:** `BFT-DEV-REVIEW-2026-08-25-01`
**From:** John, Lead Developer
**To:** George (Lead Architect) — *four rulings need revisiting* · Paul (Lead Analyst) — *spec verified* · Ringo (Product Owner) — *recommendation in §6*
**Date:** 2026-08-25
**Responds to:** `ARCH-RULING-2026-08-25-01` (George) and `BFT_SELECTION_WORKSPACE_DESIGN_SPEC.docx` (Paul)
**Baseline:** BFT v2.1 Build 112, 897 tests, PyThermX 0.5.0
**Recommendation:** **One short, targeted design round** — six decisions, no redesign. See §6.

---

## 1. Disposition

**Paul's specification is the right architecture, and its evidence is accurate.** I verified all
five cited defects against the live Build 112 tree, not against the Build 112 the spec was
written on — three builds have landed since, and every claim still holds at the exact line
numbers given. That is unusually good analytical hygiene and it saved me a day.

**George's 3-tier separation and precedence ladder are sound in shape.** I am not asking for a
different design.

What I am asking for is a short round on **six items**, because four of them sit inside the two
work packages George cleared for immediate implementation. The clearance and the open questions
overlap almost exactly:

> **WP1 (Selection Core)** cannot be built until the ladder distinguishes governed *safety* from
> governed *defaults* (§3.2, §3.3). **WP2 (Detectors)** cannot be built until the environment
> signature is settled, because the two source documents currently specify **opposite** rules
> (§3.1).

Neither is a research question. Both are decisions that take an afternoon and then unblock real
implementation.

## 2. Paul's evidence, re-verified against Build 112

| Claim | Cited | Status on Build 112 |
|---|---|---|
| GUI constructs `BundleCreator()` directly | `bundle_frame.py:72` | **Confirmed**, same line. `BundleToolService` appears nowhere in the frame |
| Environment names are literal | `writer.py:618` | **Confirmed**. Deny list has `**/.venv/**`, `**/.venv`, `**/venv/**`; `.venv312/x.py` is matched by **nothing** |
| CLI flags replace configured defaults | `cli.py:309-310` | **Confirmed**: `args.exclude if args.exclude else config…` |
| Every toggle rebuilds the preview | `bundle_frame.py:522-570` | **Confirmed** at `:537 → :539 → :569` |
| Pruning is literal-name based | `writer.py:88`, `:761` | **Confirmed**. `prunable_dir_names()` returns exact names |

The `.venv312` screenshot is fully explained: `**/.venv/**` cannot match `.venv312`, so the
directory is never pruned, never denied, and its whole tree is walked and ingested.

---

## 3. Findings that need a decision

### 3.1 The two documents specify **opposite** environment detectors — blocks WP2

**Severity: High.** This is a direct contradiction between the ruling and the spec it ratifies.

Paul, §5.4 — a **conjunction**:

> classify a directory as a Python environment when `pyvenv.cfg` exists **and** at least one
> expected interpreter layout is present

George, R2 — a **disjunction**, explicitly broadening Paul to cover conda and legacy virtualenv:

```python
PYTHON_ENV_SIGNATURES = [
    ("pyvenv.cfg",), ("conda-meta",), ("Scripts", "python.exe"), ("bin", "activate"),
]
```

Any one signature classifies. So a repository that merely contains `bin/activate` — a
checked-in helper script, which is common — has its **entire subtree pruned before descent**,
with no `pyvenv.cfg` anywhere. Paul's rule includes that tree; George's silently excludes it.

Silent exclusion is precisely what this feature exists to abolish. Worse, pruning happens
*before* descent, so the files never enter the metadata index and never appear in the decision
list — the user cannot even see what was dropped, let alone override it.

**Proposed resolution.** Keep George's broader *coverage* but restore Paul's *conjunction*, with
per-family signature pairs rather than a flat list:

| Family | Required marker | Plus one corroborating layout |
|---|---|---|
| venv / virtualenv | `pyvenv.cfg` | `Scripts/python*.exe` or `bin/python*` |
| conda | `conda-meta/` | `conda-meta/history` |
| node | `node_modules/` | `package.json` at the parent |

A single ambiguous marker (`bin/activate` alone) yields **Unknown**, not Excluded — the state
Paul already defined for exactly this case, which surfaces in the report instead of vanishing.

### 3.2 The ladder makes governed *safety* overridable by a checkbox — blocks WP1

**Severity: High.**

Ruling 3.2 permits a Priority 1 session override to beat Priority 5 governed baseline. The
governed baseline is `safety.deny_globs`, and it currently holds **two different kinds of rule**
in one list:

**Safety class** — ratified as D-005, extended in Build 107, and defended by the Layer A digest
and Layer C write-protection that Build 109 was largely spent building:

```
**/*_bundle_*.txt   **/*.zip   **/*.tar   **/*.tar.*   **/*.whl   **/archives/**
```

**Convenience class** — 31 entries of noise reduction: `__pycache__`, `.pytest_cache`,
`htmlcov`, `.idea`, `*.pyc` …

The ladder treats all 37 identically at Priority 5. As ratified, a single click force-includes a
`.zip` or a nested bundle — the recursion hazard `assert_bundle_clean` exists to prevent — and
demotes a governed safety invariant to ordinary policy without anyone saying so out loud.

**Proposed resolution.** Split the baseline into two layers, which costs one config key and no
new concepts:

- **Priority 0 (hard safety):** the archive/nested-bundle class, joining traversal and
  self-ingestion. Non-overridable.
- **Priority 5 (governed defaults):** the convenience class. Overridable exactly as ruled.

This keeps George's user-empowerment intent fully intact — everything a user would actually want
to force-include stays overridable — while not quietly unpicking Build 109.

### 3.3 A path can be `Included` in the plan and still fail at create time — blocks WP1/WP3

**Severity: High.** Closely related to §3.2 but a distinct defect.

Priority 0 in the spec is: outside base, traversal target, self-ingestion, invalid/unreadable.
`assert_bundle_clean()` is **not** in that list, yet it raises `ValidationError` *before any
output* when a nested bundle or archive reaches the payload.

So today's design permits: plan says **Included** → user sees green → Create Bundle → hard
failure from a gate the plan never modelled. The plan would be authoritative about everything
except the thing that actually stops the build.

**Proposed resolution.** Every gate that can refuse to emit must be represented as a
`Blocked` decision at plan time. If §3.2 is adopted this falls out naturally, because the
archive class becomes Priority 0 and is evaluated during planning.

### 3.4 The preview has an unbudgeted O(N) step — measured, not theorised

**Severity: High.** This is the one I would most want settled before WP4/WP5 are designed in
detail.

SEL-PERF-001 requires a single uncheck to perform *zero content reads* and update counts within
50 ms. Both are achievable. But **reads are not the only cost.** BFT formats the whole bundle
text, and `plain_marker` derives its boundary token from the *entire emitted payload*
(`_derive_boundary_token`, Build 103 bounded transport grammar). Remove one file and the token
changes, so everything re-formats.

Measured on this machine, zero reads, formatting only:

| Files | Payload | Format p50 | Format p95 |
|---:|---:|---:|---:|
| 500 | 1.1 MB | 125 ms | 138 ms |
| 1,000 | 2.1 MB | 250 ms | 264 ms |
| 2,000 | 4.3 MB | 502 ms | 521 ms |
| **4,000** | **8.6 MB** | **1,084 ms** | **1,342 ms** |

At the spec's own reference size the formatting job is **~4× the 250 ms debounce window**. The
generation-counter design in R3 will then spend most of its time discarding work that completed
too late — correct behaviour, and a treadmill.

The gate is satisfied by the letter (formatting is not a read) while the interaction it
describes cannot feel responsive.

**Proposed resolution — and this may be a simplification, not just a mitigation.** Ask whether
the preview pane needs to show *formatted bundle text* at all. What the user is choosing is
**which files and in what order**; that is the decision list and the group ordering, both of
which are already in the plan and cost nothing to render. Formatting could happen once, at
Create Bundle.

If a text preview is genuinely wanted, the workable form is a bounded window — format the first
N entries — rather than the whole artifact. Either way the acceptance gate should get an
explicit budget for *plan-to-visible-preview*, not only for reads.

### 3.5 A glob force-include over a pruned root is unbounded — WP2

**Severity: Medium.** R1 solves this for an explicit path (`--force-include .venv312/Lib/…/x.py`)
via an on-demand subtree scan. But §11.1 defines `--force-include PATH_OR_GLOB`.

`--force-include ".venv312/**/pytest/**"` cannot be resolved without walking the pruned tree —
which is the exact cost the pruning exists to avoid, reintroduced by a single flag.

**Proposed resolution.** Define the rule rather than leave it to implementation: a glob
force-include matches **only within the un-pruned metadata index**. Reaching inside a pruned
root requires either an explicit path or an explicit un-prune (`--include-root .venv312`), which
is a visible, costed choice. The report should state when a glob was scoped this way.

### 3.6 `--exclude` changes meaning for existing automation — WP3

**Severity: Medium.**

Today `--exclude` **replaces** the configured deny list (`cli.py:310`). §11 changes it to
**append**. I agree the new behaviour is correct — replacement is how one custom exclusion
silently discards baseline safety — but it is a breaking change to any script that relies on the
current semantics, and the spec presents it as a "compatibility correction" without a migration
note.

It also leaves the two flags **asymmetric**: `--include` keeps allow-list replacement, `--exclude`
becomes additive. Same-looking flags, opposite layering.

**Proposed resolution.** Ship the change, but announce it as breaking, and have the CLI emit a
one-line stderr notice the first time `--exclude` is used with a configured baseline present,
naming `--no-default-rules` as the way to get the old behaviour. Cheap, and it turns a silent
semantic change into a visible one.

---

## 4. Smaller items — worth a decision, not a round

| Ref | Item | Note |
|---|---|---|
| S-07 | **Virtualization vs accessibility.** §10.3 mandates virtualising beyond 5,000 rows; §14 requires state exposed to assistive technology. A viewport-only Tk tree cannot expose rows it has not created. These need reconciling — most likely by keeping the *model* fully addressable and providing search/filter as the AT navigation path rather than raw scrolling |
| S-08 | **Rule files have no integrity story.** Presets and `.bft-selection.json` are policy that changes what enters a bundle, living outside the governed config precisely so they can be edited. That is right — but Build 109 exists because unattributed policy change cost us four incidents. The selection report should record a digest of every rule source that contributed to the plan |
| S-09 | **"Estimated bytes" will be wrong for binary trees.** Estimated from `stat` size, but binaries are base64 (≈ +33%) and text gains a provenance header. Either label it "source bytes" or apply the encoding factor |
| S-10 | **`plan` on stdout.** §11.4 puts human plan output on stdout. That is fine — `plan` emits no artifact — but Build 105's purity rule and its test are mine, and I would rather have the exemption ruled explicitly than weaken the test to accommodate it |

---

## 5. What I am *not* raising

To keep the round narrow, I have no objection to and no questions about: the 3-tier separation;
`SelectionPlan` as an immutable authoritative handoff; decision states; typed matchers; the
intra-layer last-match-wins rule; group evaluation strictly after inclusion; transport-grammar
invariance in v2.2 (Ruling 3.3 — correct and I would defend it); the WP1–WP6 breakdown; the
service surface shape in §13.1; or the R3 generation-counter and R6 POSIX-normalisation
mitigations, both of which are right.

The feature is also a good fit for what Build 106–112 already built: `OperationProgress` gives
the scan/plan/read/format phases their event stream, and Build 112's cancellation predicate is
already the shape §13.1 asks for.

---

## 6. Recommendation

**One short design round, scoped to the six items in §3, then implement.**

Not a redesign. The architecture is right, and a second full specification would waste Paul's
work. But I do not think WP1 and WP2 should start today, and the reason is specific rather than
cautious:

- **WP2 is the detector.** The two documents currently specify opposite detectors (§3.1). Whichever I implement, one of them is wrong.
- **WP1 is the ladder.** The ladder as ratified makes governed safety overridable and lets the plan disagree with the integrity gate (§3.2, §3.3). Those change the evaluation model, not a detail inside it.

Building either now means building it twice.

**Proposed sequence:**

1. **George** rules on §3.1, §3.2, §3.3 and §3.5 — four decisions, all bounded, no new analysis required.
2. **Ringo** rules on §3.4: does the preview pane show formatted bundle text, or the decision list? That is a product question about what the workspace is *for*, and it materially changes WP4 and WP5.
3. **Paul** folds the outcomes into the spec as a revision, and — as George already asked — formalises the rule-file schema and the two persona fixtures.
4. **I start WP1 and WP2 immediately on the revised text**, and I will bring the reference tree and the SEL-PERF measurements with me so the gates are calibrated against real numbers rather than estimates.

I can have a measurement harness for the performance gates ready while the round runs, since it
depends on none of the open questions. If Ringo would rather see motion in the code, that is the
piece I would start on today.

---

**John**
Lead Developer
