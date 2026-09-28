# Developer Response — Disposition Accepted, Harness Baseline, Two Items Still Open

**Document Ref:** `BFT-DEV-RESPONSE-2026-08-25-02`
**From:** John, Lead Developer
**To:** Paul (Lead Analyst) · George (Lead Architect) · Ringo (Product Owner)
**Date:** 2026-08-25
**Responds to:** `BFT-ANALYSIS-2026-08-25-02` (Paul), `ARCH-RULING-ADDENDUM-2026-08-25-01` (George)
**Baseline:** BFT v2.1 Build 112, 897 tests, PyThermX 0.5.0
**Status:** **Accepted — proceeding with the harness, WP1 and WP2.** Two items need one more word from George.

---

## 1. Disposition

**Accepted. The hold is lifted and I am proceeding.** George's addendum resolves all six of my
findings, and Paul's four clarifications improve three of them further. I have no remaining
architectural objection.

I did three things before replying, and they are the substance of this note:

1. **Verified Paul's four clarifications against Build 112.** Three make claims about behaviour I
   own; all three are correct, and I now have the evidence rather than the assumption (§2).
2. **Produced the harness baseline** Paul asks for in §9, which turns SEL-PERF-002 from a
   self-referential gate into a number (§4).
3. **Found two places where the record now disagrees with itself**, plus three smaller
   scoping gaps (§3). None of them justifies delaying code, and I am not proposing another round.

## 2. Paul's clarifications, verified rather than assumed

| Ref | Paul's claim | Verified on Build 112 |
|---|---|---|
| §4.3 | Rule digests can live in `BundleManifest.metadata` without touching transport bytes | **Correct.** A digest planted in `metadata` appears in neither `plain_marker` nor `md_fence` output. Transport invariance holds |
| §4.4 | `bundle --output` leaves stdout empty; without `--output` stdout carries the artifact and nothing else | **Correct.** Measured 0 bytes with `--output`, 2,610 bytes beginning `#` without |
| §8 / S-09 | Exact Base64 expansion `4·⌈n/3⌉`, not a rounded 1.33× | **Correct, and exact.** 1,000 raw bytes → 1,336 encoded. Paul's formula gives 1,336; 1.33× gives 1,330. BFT does not wrap base64, so the formula is exact rather than approximate |

Paul's §4.2 snapshot-scoped `Included` invariant I accept without reservation — it is the only
version of that guarantee that can survive a file being deleted between plan and create.

## 3. Items still open

### 3.1 Two rulings where Paul corrected George, silently — George should say which controls

Both corrections are **right**, and I verified both. My concern is only that the record now
contains two different rulings on the same reference with nothing saying which supersedes.

- **S-09 payload estimation.** Addendum §3 mandates *"a 1.33x multiplier"*. Paul §8 mandates
  *"exact Base64 expansion (4 · ⌈n/3⌉) rather than a rounded 1.33 multiplier"*. Measured, Paul is
  exactly right and 1.33× is off by 6 bytes per KB. **Paul's should be recorded as controlling.**
- **S-10 output purity.** Addendum §3 says *"create and bundle commands retain strict zero-stdout
  purity"*. That is not true of `bundle` without `--output`, which is the ratified Build 105
  contract. Paul's three-way wording in §4.4 matches observed behaviour. **Paul's should be
  recorded as controlling.**

This matters more than pedantry: both are about to become binding tests that I write, and I would
rather implement a ruling than pick between two.

### 3.2 `--include` at Priority 2b would silently broaden output — the one substantive gap

**Severity: High. This is the only item I would want settled before the WP3 CLI contract freezes.**

Paul §4.1 places legacy `--include` at Priority 2b as an ordinary rule under last-match-wins.
But `--include` is not an ordinary rule today — it is an **allow-list**. Measured on Build 112:

```
bundle --include "src/**"   ->  src/app.py, src/util.py
                                docs/readme.md   NOT included
                                notes.txt        NOT included
```

Everything that does not match is dropped. Under the new ladder, an ordinary Priority 2b *include*
rule sitting above a Priority 6 base action of *include by default* would leave `docs/readme.md`
and `notes.txt` **included** — the output silently broadens.

That is precisely what spec §11 promises will not happen: *"Existing `--include` retains
allow-list behavior when present so automation does not silently broaden output."* As currently
laddered, the mechanism contradicts the promise.

**Proposed resolution.** `--include` is not a rule, it is a **base-action switch**. When any
`--include` is supplied, the effective Priority 6 base action becomes *exclude*, and each
`--include` is an ordinary Priority 2b include rule above it. That reproduces today's allow-list
semantics exactly, keeps the ladder intact, and needs no new layer — one sentence in the spec.

### 3.3 Priority 0 archives would make our own delivered wheel permanently un-bundleable

**Severity: Medium, but it lands on something I wrote.**

Addendum §2.2 puts `**/*.zip`, `**/*.tar*`, `**/*.whl` and `**/archives/**` at Priority 0,
**non-overridable by any means**. I should flag the provenance: **I added `**/*.whl` in Build 107**,
and I described it then as completing an existing hygiene rule so self-bundles would stop
absorbing an 11 KB base64 blob. It was never characterised as a recursion hazard.

The concrete casualty is in this repository:

```
vendor/pythermx-0.5.0-py3-none-any.whl     <- a delivered payload file of BFT itself
```

Under §2.2, no user, preset, flag or session override could ever place that file in a bundle —
including us, bundling our own source.

The genuine recursion hazards are different in kind: **nested bundle text** (`**/*_bundle_*.txt`),
**self-ingestion** of the active output, and **path traversal**. Those break the tool and belong at
Priority 0 permanently. An archive sitting in a source tree does not break anything; it makes the
bundle large.

**Proposed resolution.**

| Priority 0 — non-overridable | Priority 5 — overridable, with confirmation |
|---|---|
| `**/*_bundle_*.txt` (recursion) | `**/*.zip`, `**/*.tar*`, `**/*.whl`, `**/archives/**` |
| self-ingestion of the active output | |
| path traversal outside base | |
| unreadable / invalid paths | |

Keeping archives overridable-but-confirmed preserves the hygiene intent without making a
convenience rule permanent. If George prefers them at Priority 0, that is a defensible call — but
it should be made knowing it forecloses bundling our own vendored wheel.

### 3.4 Three smaller scoping gaps

- **`Stale` is a sixth decision state.** Paul §4.2 introduces `Stale` as a create-time outcome, but
  spec §5.2 defines exactly five (`Included`, `Excluded`, `Blocked`, `Skipped`, `Unknown`). It needs
  adding to the model with its transitions, and it interacts with Build 112 cancellation and the
  Build 103 reconciliation gate. I will assume `Stale` exists and is non-terminal unless told
  otherwise.
- **"An expand … creates a new plan generation" needs scoping.** Paul §9 says an expand, explicit
  child override, or `--include-root` yields a new snapshot and plan. That must mean expanding a
  **pruned root** only. If expanding any ordinary folder regenerated the plan, a user browsing a
  tree would trigger a rescan per click. I will implement pruned-root-only.
- **SEL-PERF-002 is currently self-referential** — *"within the measured budget set by John's
  harness"*. §4 below supplies the number so it can become a fixed target.

## 4. Harness baseline — the numbers Paul asked me to reconcile

Metadata-only scan: `os.walk` plus `stat`, **zero file reads**, three runs each, real trees.

| Tree | Mode | Files | Dirs | p50 | p95 |
|---|---|---:|---:|---:|---:|
| BFT whole tree | full | 3,847 | 559 | 280 ms | 455 ms |
| BFT whole tree | **pruned** | 520 | 35 | **31 ms** | 33 ms |
| pyprojectmgrV2 | full | 17,263 | 2,050 | 1,299 ms | 1,964 ms |
| pyprojectmgrV2 | **pruned** | 1,276 | 516 | **140 ms** | 149 ms |

**Directory pruning removes 89% of scan time on both real trees.** That is the Build 110 result
holding up under a second, independent measurement, and it is the strongest evidence that the
metadata-first architecture is the right shape.

Derived budget:

- Pruned metadata scan costs **~85 ms per 1,000 files**.
- A 4,000-path plan therefore scans in **~340 ms**.
- Full transport formatting of the same 4,000 paths was **1,084 ms p50** (previous review).

**Proposed SEL-PERF-002, as a real gate:**

> A 4,000-path SelectionPlan is delivered within **500 ms p95** after pruning, and the first
> usable viewport renders within **150 ms** of plan delivery.

500 ms gives ~45% headroom over the measured 340 ms, which is the right margin for a
one-off action triggered by an explicit Select Source or Rescan. Two consequences worth stating:
the initial plan is **not** instant and must report progress — BFT already emits the phase events
for that — and the ~340 ms is classification only, so any per-file work added inside the scan loop
comes straight out of that headroom.

## 5. Confirmations to Paul

- **Pruned roots modelled explicitly**, with expand / explicit child override / `--include-root`
  producing a **new immutable plan generation** rather than mutating the previous one. Agreed, and
  scoped to pruned roots per §3.4.
- **Emit-blocking evaluation stays in core**; GUI and CLI adapters stay policy-free. Agreed — that
  is the same rule the AST layering test already enforces for renderers, and I will extend it to
  cover selection policy.
- **§§6–7 as the interim contract** pending Revision 1.1. Agreed. The rule-file schema in §6 is
  implementable as written; the `block` action being reserved to Priority 0 is the right call and
  falls out naturally if §3.3 is settled.
- **Fixtures.** The application-developer fixture in §7.1 is exactly the shape I need, and the
  ambiguous `bin/activate`-only subtree is the case I would have asked for. I will write my WP2
  detector tests against those names so our fixtures converge rather than diverge.

## 6. Ringo — the viewport model

I support Paul's §5 recommendation and George's §2.4, on the evidence rather than on preference:
a full text preview on every toggle costs **1,084 ms** at 4,000 files with zero content reads. It
would preserve the old coupling under a new cache — the same defect in different clothing.

The bounded on-demand preview (10 files / 50 KB) is cheap by construction. The one thing I would
ask is that the truncation boundary be **visible in the pane itself**, not only in the report — a
preview that silently stops at 10 files invites the same "why is my file missing" question this
whole feature exists to eliminate.

## 7. What I am starting now

1. **Performance harness**, extended from the two baselines above into a repeatable fixture that
   emits the SEL-PERF numbers on demand. It depends on none of the open items.
2. **WP1 Selection Core** — models, rule evaluation, decision chains, deterministic plan. I will
   build the ladder with the safety/default split parameterised, so a ruling on §3.3 changes a
   table rather than the engine.
3. **WP2 Detectors** — conjunctive per-family signatures exactly as ratified in addendum §2.1,
   with `Unknown` for ambiguous single markers and evidence codes in the report.

I will bring measured numbers to the WP1/WP2 exit gate rather than estimates, and a disposition
table from each of these findings to the test or spec clause that closes it.

---

**John**
Lead Developer
