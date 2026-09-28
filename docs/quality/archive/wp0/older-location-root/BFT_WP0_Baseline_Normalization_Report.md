# BFT v2.1 Build 100 — WP0 Baseline Normalization Report

**Prepared by:** Paul, Lead Analyst
**Date:** 2026-07-23
**Authorization:** Ringo authorized WP0 — Ratification and baseline normalization
**Repository:** `C:\Users\mpw\Python\bundle_file_project\bundle_file_tool_v2`
**Entry branch/commit:** `master` at `b88d67c36c4f2ff97837a0fbee24e907e691fba5`
**Technical status:** Normalized and green; local branch/commit blocked by repository ACL

## Outcome

WP0 technical normalization is complete. The candidate baseline is fully cataloged, the source attachment is reconciled, ambiguous and local artifacts have explicit dispositions, governance paths resolve, obsolete production test shims are removed, and the complete configured quality gate passes.

The candidate is ready for George and John’s technical ratification. It is not yet an authoritative committed baseline because the execution account is explicitly denied write access to `.git`.

## Quality gate

| Check | Result |
|---|---|
| Complete configured suite | 474 passed, 0 failed |
| Coverage | 88.84% |
| Required coverage | 85% |
| Git whitespace check | Passed |
| Included untracked text whitespace scan | Passed |
| Governed JSON parsing | Passed |
| Active header-policy path | Passed |
| Code-catalog source preservation | 21 source files retained |
| Product callable preservation | Passed |

Python 3.11.5, pytest 9.0.2, and pytest-cov 7.1.0 were used. The final run completed in 7.51 seconds.

## Baseline normalization completed

- Classified the 65 tracked changes and the original 168 untracked paths.
- Reconciled all 21 attached Build 101 source files with the WP0 entry state.
- Recorded nine post-entry source deltas: three functional corrections and six whitespace-only cleanups.
- Removed the production monkeypatch of `builtins.all` and its test-only wrapper classes.
- Restored the structured logging completion/error contract and safe fallback behavior.
- Enforced non-empty bundle entry paths.
- Enabled strict Base64 validation.
- Standardized tests on canonical `core` and `cli` module identities.
- Corrected obsolete exception expectations and malformed test assertions.
- Proved replacement coverage for the 15 retired legacy verification harnesses.
- Moved the two catalog utilities to the governed `scripts` location.
- Removed machine-specific recent paths and window geometry from governed defaults.
- Restored the portable first-launch state.
- Renamed the active header policy to match the project manifest and normalized its governed keywords/status values.
- Expanded `.gitignore` to exclude backups, logs, sessions, generated output, emergency scripts, and out-of-scope transition aids.
- Retained the alternate proposed header policy as non-active design evidence.

## Permanent WP0 records added to the repository

- `docs/WP0_RATIFICATION_DECISION_RECORD.md`
- `docs/WP0_BASELINE_CATALOG.md`
- `docs/WP0_SOURCE_RECONCILIATION.md`
- `docs/WP0_VALIDATION_REPORT.md`

## Commit constraint

Creating `wp0/bft-build100-baseline` failed because Windows ACL entries explicitly deny the execution identity write access to `.git\refs\heads`. A narrow repository-metadata permission was requested and granted at the workspace layer, but it cannot override the host filesystem deny entry.

No ACL was altered, no commit was fabricated, and nothing was pushed remotely.

After the host ACL is corrected, the intended local preservation commands are:

```powershell
git switch -c wp0/bft-build100-baseline
git add -A
git commit -m "chore: ratify and normalize BFT Build 100 baseline"
```

The two excluded local files, `VALIDATE_regenerated_bundle.bat` and `deny_additions.json`, will not be staged because they are now explicitly ignored.

## Remaining ratification gates

The following decisions are recorded but remain unapproved by the named technical roles:

1. George and John accept the normalized candidate baseline.
2. Ringo confirms repository-awareness is deferred to Build 101.
3. Ringo, George, and John approve package-owned installed version `2.1.100`.
4. Ringo and George approve the safety deny-list filtering default.
5. George approves the filtering precedence contract.
6. George and John approve Flask on `127.0.0.1` as the local Web stack.

These approvals are intentionally not inferred from Ringo’s authorization to perform WP0.

