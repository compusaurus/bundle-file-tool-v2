# BFT v2.1 Build 100 — Request for John's Final Gate 1 Review

**Prepared by:** Paul, Lead Analyst  
**Date:** 2026-07-24  
**Decision owner:** John, Lead Developer  
**Gate:** Gate 1 — Accept normalized candidate baseline  
**Status requested:** Unconditional technical acceptance or an exact statement of remaining evidence

## 1. Why this review is ready

John's 2026-07-23 review conditionally accepted Gate 1 pending explicit test arithmetic, defect-level traceability, access to the authoritative records and source, safety-file clarification, governed-path confirmation, and canonical QC vocabulary mapping.

All six requests are now answered in the governed WP0 records. Ringo also made and implemented the five outstanding policy decisions after John's review.

## 2. Evidence mapped to John's requests

| John's request | Completed evidence |
|---|---|
| Test-count arithmetic | `WP0_VALIDATION_REPORT.md` §2 records 474 entry items, zero pytest items represented by the 15 retired standalone scripts, zero collected-item change during normalization, six ratification contract tests added, and 480 final items. |
| Three functional corrections | `WP0_VALIDATION_REPORT.md` §3 identifies `BFT-WP0-DEF-001` through `BFT-WP0-DEF-003`, with before/after behavior and named executable tests for writer, logging, and model invariants. |
| Source access and reconciliation | `WP0_SOURCE_RECONCILIATION.md` records the exact 21-file entry match, normalization and ratification deltas, current hashes, and the 22-file governed source inventory. |
| `deny_additions.json` | `WP0_TEAM_REVIEW_DISPOSITION.md` §3 and `WP0_VALIDATION_REPORT.md` §5 record it as governed traceability evidence; all five patterns are synchronized in code and shipped configuration. |
| Governed-files check | `WP0_TEAM_REVIEW_DISPOSITION.md` §4 and `WP0_VALIDATION_REPORT.md` §5 confirm that assets, manifest, required project specification, `.pyprojectmgr/`, and `updates/` are not excluded. |
| QC vocabulary mapping | `WP0_VALIDATION_REPORT.md` §6 maps each supplemental check to the canonical QC framework without representing supplemental evidence as canonical QC. |

## 3. Current validated candidate

- Full configured suite: **480 passed, 0 failed**
- Coverage: **88.49%**, above the 85% gate
- Governed source inventory: **22 Python files**
- Installed package version: **2.1.102**
- Production `builtins.all` monkeypatch: **removed**
- Five archive/bundle safety denies: **synchronized**
- Required `.pyprojectmgr/project_spec.json`: **present**
- Git metadata ACL: **intentional and unchanged**
- Stager version increment/write: **removed**

## 4. Separate controlled blockers

1. Canonical pyprojectmgr strict QC is **TOOL-BLOCKED** by non-stabilizing schema remediation. A pyprojectmgr fix or explicit waiver remains required for authoritative WP0 closure.
2. The protected branch and commit must be created by an authorized interactive account. The intentional `.git` separation-of-duties ACL must remain in place.

Gate 1 may be technically accepted while these controlled closure actions remain tracked separately.

## 5. Decision requested from John

Please record one of the following:

- **Unconditional technical accept:** Gate 1 evidence is sufficient; canonical QC remediation/waiver and the authorized interactive commit remain separate closure actions.
- **Remain conditional:** identify the exact unsatisfied evidence item, affected file or behavior, and acceptance condition.

No additional Ringo decision is required unless a new issue changes approved product scope or governance policy.
