# BFT v2.1 Build 100 — WP0 Technical Review and Gap Analysis

**Prepared by:** John, Lead Developer
**Date:** 2026-07-23
**Reviewing:** Paul's *WP0 Baseline Normalization Report* and George's *Architectural Assessment* (both dated 2026-07-23)
**Status:** Design/governance review only — no code executed or changed against the live repository in this round.

---

## 1. Executive Summary

Paul's WP0 work is disciplined and the outcome is strong: 474/474 tests passing, 88.84% coverage against an 85% floor, and a set of real architectural liabilities closed out (test-shim removal, strict Base64 validation, portable first-launch state, header-policy normalization). George's architectural response correctly endorses the technical substance of that work.

This review raises five items before I add my own technical sign-off:

1. **Gate ownership is being conflated.** Several ratification gates require *both* Ringo and George (or George and me) by Paul's own gate definitions. George's assessment marks them fully "Ratified" on his signature alone. That overstates the approval status — his ratification should be read as *George's half* of a two-party gate, not gate closure.
2. **The `.git` ACL deny entry may be an intentional control, not a misconfiguration.** Before anyone removes it, we should confirm it wasn't placed deliberately (e.g., a service/automation account deliberately barred from writing refs directly, as a separation-of-duties control).
3. **`deny_additions.json` being gitignored is worth a second look**, given the team is simultaneously ratifying "safety deny-list filtering default" (Gate 4) as governance policy. A file with that name sounds safety-relevant, not disposable.
4. **The `.gitignore` expansion needs a governed-files check.** It excludes backups, logs, sessions, generated output — good — but I want written confirmation that `assets.db`, `updates/`, and `project_spec.json` (all required by the pyprojmgr lifecycle) were not caught in that expansion.
5. **The quality-gate check names don't map cleanly onto the team's documented QC checks.** "Governed JSON parsing" and "Product callable preservation" aren't among the four canonical `pyprojmgr qc` checks (lifecycle compliance, signature drift, contract adherence, orphan detection) in the team directives. I'd like these named and mapped explicitly so QC stays a single documented framework rather than growing ad hoc gate names project-by-project.

I'm also flagging, for the record, that the project files I have direct access to in this session still reflect the **pre-WP0** state — the `builtins.all` monkeypatch is still present in the `writer.py` I can see, and `config.py`'s default is still the directory-based allow-list. That's expected (WP0 hasn't been committed yet, per the ACL blocker), but it means my technical sign-off below is conditional on reviewing the actual normalized source once it's available to me, not just the report describing it.

---

## 2. Gate-by-Gate Status

Paul's report lists six gates and is explicit that none of them are to be inferred from Ringo's WP0 authorization. George has now weighed in. Here is the accurate state of each, including where John's position is required:

| Gate | Requires | George's position | John's position (this document) | Status |
|---|---|---|---|---|
| 1. Accept normalized candidate baseline | George **and** John | Ratified | **Conditional accept** — see §4.1 | Open pending source review |
| 2. Repository-awareness deferred to Build 101 | Ringo | Not addressed (correctly — not his gate) | N/A | Open — Ringo |
| 3. Approve package-owned installed version 2.1.100 | Ringo, George, **and** John | Ratified | **Concur** — matches Build 100 spec's version rule | Open — needs Ringo |
| 4. Approve safety deny-list filtering default | Ringo **and** George | Ratified | N/A (not a John gate) — see §4.3 for a related flag | Open — needs Ringo |
| 5. Approve filtering precedence contract | George | Ratified | N/A (not a John gate) | **Closed** |
| 6. Approve Flask on 127.0.0.1 as local Web stack | George **and** John | Ratified | **Concur** — see §4.2 | **Closed** |

Two gates (3 and 4) are effectively still open because they name Ringo as a required approver and Ringo hasn't yet responded to this specific report. George's ratification is necessary but not sufficient to close them. Recommend the gate table above (or equivalent) be what actually gets tracked in `assets.db`, rather than "Ratified" language that could be read as full closure.

---

## 3. What I Can and Cannot Verify Directly Right Now

Per standing team practice, I don't sign off on claims about source changes without seeing the source. Current state:

- **Cannot yet verify:** the three functional corrections, the six whitespace-only cleanups, the header-policy rename, and the strict Base64/non-empty-path enforcement — these all require the actual post-WP0 files or `WP0_SOURCE_RECONCILIATION.md`, neither of which is in front of me yet.
- **Can confirm independently:** the pre-WP0 baseline I do have access to is consistent with the report's starting-point description — the `builtins.all` monkeypatch (writer.py lines ~69–86) and the directory-based `allow_globs` default (config.py) are both still present exactly where the report says they were before cleanup. This gives me reasonable confidence the report is describing real, not fabricated, before/after state — but it's corroboration of the "before," not verification of the "after."

**Request to Paul:** please attach or route the four WP0 doc records (`WP0_RATIFICATION_DECISION_RECORD.md`, `WP0_BASELINE_CATALOG.md`, `WP0_SOURCE_RECONCILIATION.md`, `WP0_VALIDATION_REPORT.md`) into this project's file set so I can complete the review against source rather than against the summary.

---

## 4. Findings and Recommendations

### 4.1 Gate 1 — Accept the normalized baseline (John's gate)

**Position: conditional accept.** The quality-gate table is strong on its face (474/474, 88.84% coverage, whitespace/JSON/header checks all passing). Two things I want closed before this becomes an unconditional accept:

- A short accounting of the test-count change. The report states 474 passing, 0 failing, and separately that 15 legacy verification harnesses were retired with "proved replacement coverage." I'd like the arithmetic shown explicitly (previous total → retired → replaced → net new → final total) in `WP0_VALIDATION_REPORT.md`, consistent with acceptance-matrix item BFT-B100-015 ("no unreviewed deletions... in code catalog comparison") which I'd extend in spirit to test deletions too.
- Confirmation that the three *functional* corrections (as opposed to the six whitespace-only ones) are each traceable to a specific defect with before/after behavior noted — not because I doubt Paul's work, but because that's the standing checklist for any change touching runtime behavior, and "baseline normalization" shouldn't become a channel for undocumented functional changes even when they're improvements.

Once those two items are visible, I'd expect to move this to a full accept without further discussion — nothing in the summary suggests a real problem, I just haven't seen the artifact yet.

### 4.2 Gate 6 — Flask on 127.0.0.1 (John's gate)

**Position: concur, closed.** This matches Paul's original recommendation in the Build 100 spec (§14, "To George") and George's loopback-binding rationale is the correct default security posture for a local desktop tool. No open concerns. Recommend `web.host` in the config schema stay defaulted to `127.0.0.1` and that any future change to `0.0.0.0` or a non-loopback bind require its own explicit gate, not a silent config edit.

### 4.3 The `.git` ACL deny entry — recommend confirming intent before removal

George's proposed fix is to manually clear the Windows ACL deny entry on `.git\refs\heads` via Explorer or an elevated shell, then run Paul's prepared `git switch` / `git add` / `git commit` sequence. Before doing that, I'd like one question answered: **was that deny entry set deliberately** — for example, is the execution account WP0 ran under intentionally restricted from writing refs directly, as a separation-of-duties control between "an automated/analysis pass proposes a baseline" and "a human explicitly commits it"? If so, the correct fix might be "run the three git commands under an authorized interactive account," not "remove the control." If the deny entry really is accidental (leftover from a prior sandbox policy, unrelated tooling, etc.), George's fix is right as written. Either way this is a one-line question to whoever manages the host ACLs, and worth asking before altering a security boundary we didn't set ourselves.

### 4.4 `deny_additions.json` being excluded — needs a one-line clarification

The report notes two local files are now gitignored and won't be staged: `VALIDATE_regenerated_bundle.bat` and `deny_additions.json`. The `.bat` file reads as a plausible local/dev artifact. `deny_additions.json`, by name, sounds like it holds deny-glob or deny-extension entries — exactly the subject of Gate 4 (safety deny-list filtering default) and the filtering design discussed in the Build 100 addendum. If it's genuinely a scratch/experimental file distinct from the shipped default deny list (which lives in `bundle_config.json` / `ConfigManager.DEFAULT_CONFIG`), fine — but I'd like that confirmed in one sentence rather than assumed, since excluding a file that *sounds* safety-relevant from version control, in the same report where we're ratifying a safety deny-list default, is the kind of thing the team directive asks us to call out immediately rather than let pass quietly.

### 4.5 `.gitignore` expansion — governed-files check requested

The expansion (backups, logs, sessions, generated output, emergency scripts, out-of-scope transition aids) is sensible and matches what should *not* be tracked. Before this becomes permanent, I want written confirmation that the following pyprojmgr-governed paths were **not** swept up in the expansion, since several of them use naming patterns (e.g., anything under `backup/`, or output-like directories) that a broad glob could accidentally catch:

- `assets.db`
- `project_spec.json`
- `updates/` (the proposed-file staging directory itself, as opposed to its generated *contents*)
- `.pyprojectmgr/` config

This is a five-minute check against the actual `.gitignore` diff, not a deep investigation — just needs to happen before ratification, per the same "confirm collateral damage didn't occur" instinct that applies to code changes.

### 4.6 QC check-name mapping

The quality-gate table lists "Governed JSON parsing," "Active header-policy path," "Code-catalog source preservation," and "Product callable preservation" as passing checks. The team directive defines `pyprojmgr qc` as enforcing four named checks: lifecycle compliance, signature drift, contract adherence, and orphan detection. I'd like a short mapping (even a one-line table) showing which of the four canonical checks each of these new-sounding names corresponds to, or — if they're genuinely new checks — a note that they've been formally added to the QC framework and documented as such. This isn't a correctness concern with WP0's actual results; it's about keeping one documented QC vocabulary across projects rather than each report introducing its own check names.

### 4.7 Minor items, no action needed now

- Python 3.11.5 / pytest 9.0.2 satisfy the team's "Python 3.10+" floor — no conflict.
- Branch name `master` vs. `main` isn't governed by any current team directive; flagging only as a naming-convention item worth a one-time team decision across projects (BFT, pyprojectmgr, and others), not specific to WP0.

---

## 5. Recommendations Summary

1. Track the six gates using the ownership table in §2, not "Ratified" as a single global status — Gates 3 and 4 remain open pending Ringo.
2. Before touching the `.git` ACL: confirm with whoever manages host permissions whether the deny entry was intentional. If intentional, run the preservation commands from an authorized interactive account instead of removing the control.
3. Route the four WP0 doc records into shared project files so John (and George, if not already done) can review the actual functional-correction diffs, not just the summary, before Gate 1 becomes unconditional.
4. Get a one-line clarification on `deny_additions.json`'s purpose before finalizing the `.gitignore` change.
5. Get written confirmation that `assets.db`, `project_spec.json`, `updates/`, and `.pyprojectmgr/` are unaffected by the `.gitignore` expansion.
6. Map the four new quality-gate check names to the team's canonical `pyprojmgr qc` checks, or formally document them as additions.
7. On John's own authority: Gates 1 (conditional) and 6 (closed) are recorded above.

---

## 6. Change Log

| Date | Author | Change type | Description |
|---|---|---|---|
| 2026-07-23 | John (Lead Dev) | analysis/governance review | Reviewed Paul's WP0 Baseline Normalization Report and George's Architectural Assessment; recorded gate-ownership corrections, an ACL-removal caution, a deny-list file question, a .gitignore governed-files check, and a QC-naming mapping request. No repository code or config files changed. |
