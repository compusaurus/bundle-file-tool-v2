# BFT v2.1 Build 100 — WP0 Team Review Disposition

**Record ID:** BFT-WP0-TRD-001
**Prepared by:** Paul, Lead Analyst
**Date:** 2026-07-23
**Last updated:** 2026-07-24
**Reviews dispositioned:** George's Architectural Assessment and John's Technical Review and Gap Analysis

## 1. Approval state

George's ratifications are recorded as George's portion of each shared gate. They are not treated as Ringo's or John's approval.

| Gate | Status after team review |
|---|---|
| 1. Accept normalized baseline | George ratified; John accepts substantive evidence as represented but remains conditional on clean canonical QC or a bounded waiver |
| 2. Defer repository awareness to Build 101 | Closed — Ringo confirmed |
| 3. Package-owned installed version `2.1.102` | Closed — Ringo approved updated value; George ratified; John concurred |
| 4. Safety deny-list filtering default | Closed — Ringo confirmed; George ratified |
| 5. Filtering precedence | Closed — George ratified |
| 6. Flask on `127.0.0.1` | Closed — George ratified and John concurred |

## 2. Actions completed from John's review

1. Added exact test-count arithmetic to `WP0_VALIDATION_REPORT.md`: 474 entry items, 15 retired standalone verification scripts representing zero pytest items, zero collected items added/deleted during normalization, and 474 final items.
2. Added defect IDs, before/after behavior, and named tests for the three functional source corrections.
3. Removed `deny_additions.json` from `.gitignore` and reclassified it as governed transition evidence.
4. Confirmed `.gitignore` does not exclude `.pyprojectmgr/assets.db`, `.pyprojectmgr/project_manifest.json`, `project_spec.json`, or content beneath `updates/`.
5. Recorded the initial `project_spec.json` lifecycle gap, then resolved it after Ringo confirmed the specification is required.
6. Mapped every supplemental WP0 check to the canonical pyprojectmgr vocabulary without claiming that supplemental evidence is a canonical QC result.
7. Attempted canonical strict QC, restored the one live file rewritten by pyprojectmgr, and reproduced the remaining schema-stabilization failure against a disposable mirror.
8. Left Gate 1 conditional for John's explicit final review at that stage; no approval was inferred.

## 3. `deny_additions.json` clarification

The file contains five archive/bundle deny patterns:

- `**/*_bundle_*.txt`
- `**/*.zip`
- `**/*.tar`
- `**/*.tar.*`
- `**/archives/**`

All five are now present in both `ConfigManager.DEFAULT_CONFIG` and shipped `bundle_config.json`. The file remains governed traceability evidence for the discrepancy and its resolution.

## 4. Governed-files check

| Path | Ignored? | Present? | Disposition |
|---|---:|---:|---|
| `.pyprojectmgr/assets.db` | No | Yes | Governed candidate |
| `.pyprojectmgr/project_manifest.json` | No | Yes | Governed candidate |
| `.pyprojectmgr/` | No | Yes | Only explicit backups/reports beneath it are ignored |
| `updates/` | No | Yes, empty | Governed staging location |
| `.pyprojectmgr/project_spec.json` | No | Yes | Required standardized family-app configuration |

## 5. Canonical QC result

The local pyprojectmgr CLI was found and invoked with strict QC.

- The live run attempted auto-remediation, rewrote `src/database/schema_ids.py`, and then failed on a Windows console-encoding error.
- Paul restored the exact pre-run WP0 file and verified SHA256 `b2db1b55cc0e12d9822805c75c0616b0f9df1712bebc0b881a4ed1a0ed82fe57`.
- A second run against a disposable mirror forced UTF-8. Artifact generation succeeded, but schema drift still failed to stabilize and QC aborted before any of the four canonical rule results were returned.

Canonical QC status is **TOOL-BLOCKED**. Supplemental WP0 checks remain valid evidence but are not represented as lifecycle-compliance, signature-drift, contract-adherence, or orphan-detection passes.

## 6. ACL disposition

Ringo confirmed the `.git` deny entry is intentional. It has not been removed or weakened. `.pyprojectmgr/project_spec.json` now records a separation-of-duties policy under which automated agents are denied and authorized interactive accounts are allowed, enforced by the host ACL.

## 7. Ringo decisions implemented

1. Repository awareness is deferred to Build 101.
2. Package-owned installed version is `2.1.102`.
3. The safety deny-list default is active and its five archive/bundle patterns are synchronized.
4. The `.git` ACL is an intentional separation-of-duties control and is recorded in project configuration.
5. `.pyprojectmgr/project_spec.json` is required and follows the pyprojectmgr family-app structure.

The post-decision suite passes 480 tests with 88.49% coverage. John has completed his conditional re-review; direct primary-evidence audit, canonical QC remediation/waiver, and the authorized interactive commit remain open.

## 8. Final Gate 1 routing

On 2026-07-24, Paul confirmed that the attached George and John review documents predate Ringo's decisions and the 480-test ratification candidate. `WP0_REQUEST_FOR_JOHN_FINAL_GATE1_REVIEW.md` maps every condition from John's review to the completed evidence and requests an explicit final disposition. George's earlier recommendation to remove the `.git` deny ACL is superseded by Ringo's confirmation that the ACL is intentional.

## 9. John's final review disposition

John responded on 2026-07-24:

- all six earlier evidence conditions are satisfied as represented;
- the primary records still require direct audit because they were not included in his review set;
- canonical strict QC remains part of Gate 1 and cannot be replaced by the supplemental checks;
- Gate 1 can close through either a clean canonical run on the exact candidate or a named, scoped, time-bounded waiver;
- the protected commit is a separate publishing control and must not weaken the intentional `.git` ACL.

Paul recorded blocker `BFT-WP0-QC-001` and prepared the six requested primary records for routing. Gate 1 remains open; no John approval is inferred beyond his written conditional acceptance.
