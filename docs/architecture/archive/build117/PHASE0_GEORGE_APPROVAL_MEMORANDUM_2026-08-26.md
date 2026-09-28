# Phase 0 Architecture and BFT Governance Approval Memorandum

**Package ID:** BFT-CONFIGEDITOR-PHASE0-2026-08-26  
**Status:** Submitted draft for George's architectural approval  
**Prepared by:** Paul, Lead Developer / Lead Analyst  
**Approval authority:** George, Lead Architect  
**Product acceptance:** Ringo  
**Consulted reviewer:** John, Lead Developer

## 1. Approval requested

Approve the five central-setup architecture decisions and conditionally approve the BFT governance reconciliation plan.

The recommended disposition is:

1. **Approve ADR-SETUP-001 through ADR-SETUP-005 as the Phase 0 architecture baseline.**
2. **Authorize pyprojectmgr Gate A contract repair and a staged BFT reconciliation proposal.**
3. **Do not authorize live BFT governed-metadata mutation yet.** Live mutation remains contingent on canonical pyprojectmgr producer/validator agreement, George's approval of the exact staged diff, and recoverable execution evidence.

## 2. Executive finding

George's central-hub direction is technically aligned and should proceed with this ownership boundary:

- applications own setting meaning and versioned contributions;
- ConfigEditor owns modular application/section presentation, working copies, validation feedback, and review;
- `pyprojectmgr` alone authenticates, authorizes, mutates, recovers, verifies, and audits governed configuration;
- governed delivery configuration remains separate from user-local state.

BFT is the right first reference application because it already enforces read-only governed runtime configuration and separate mutable `UserStateStore` behavior.

## 3. Evidence summary

The current BFT baseline has both strengths and unresolved governance drift:

- Version `2.1.116` is synchronized across the inspected release/configuration surfaces.
- `bundle_config.json` SHA-256 matches `governance.governed_config_sha256` exactly.
- `ConfigManager.save()` remains intentionally prohibited.
- `project_spec.json` declares three entry points; the manifest declares none.
- Infrastructure patterns and scanning exclusions differ between spec and manifest.
- The profile-driven `external_governed` validator passes with one migration-history warning and one legacy-metadata info finding.
- The separate governance-schema validator fails because `static_asset_categories` and `configuration_paths` are arrays rather than objects.
- Current pyprojectmgr initialization code still contains array defaults for those fields, exposing a producer/validator contract mismatch that must be resolved before BFT is changed.

## 4. Package contents

| Document | Approval purpose |
|---|---|
| [ADR-SETUP-001: Component Ownership](ADR-SETUP-001_COMPONENT_OWNERSHIP.md) | Establish application, ConfigEditor, pyprojectmgr, runtime, and installer authority |
| [ADR-SETUP-002: Contribution Discovery and Trust](ADR-SETUP-002_CONTRIBUTION_DISCOVERY_AND_TRUST.md) | Establish governed registry discovery, stable identity, descriptor/schema authentication, and fail-closed behavior |
| [ADR-SETUP-003: Governed Transaction and Recovery](ADR-SETUP-003_GOVERNED_TRANSACTION_AND_RECOVERY.md) | Require sessions, locks, digest CAS, staged validation, journaling, recovery, postflight, and receipts |
| [ADR-SETUP-004: Governed Config and User State](ADR-SETUP-004_GOVERNED_CONFIG_AND_USER_STATE.md) | Preserve BFT's delivery-policy/user-preference separation and legacy-key deprecation path |
| [ADR-SETUP-005: Hook Isolation and Trust](ADR-SETUP-005_HOOK_ISOLATION_AND_TRUST.md) | Constrain application validators, migrators, postflight, reload, and location-provider hooks |
| [BFT Governance Reconciliation Proposal](BFT_GOVERNANCE_RECONCILIATION_PROPOSAL_2026-08-26.md) | Record baseline hashes, validation evidence, exact field dispositions, execution gates, and rollback conditions |

Supporting suite documents:

- [Central Setup Architecture](../CONFIGEDITOR_CENTRAL_SETUP_ARCHITECTURE_2026-08-26.md)
- [Setup Contracts](../CONFIGEDITOR_SETUP_CONTRACTS_2026-08-26.md)
- [Implementation Plan](../CONFIGEDITOR_IMPLEMENTATION_PLAN_2026-08-26.md)
- [Gaps, Risks, and Recommendations](../CONFIGEDITOR_GAPS_RISKS_RECOMMENDATIONS_2026-08-26.md)

## 5. Decisions requested from George

### Architecture decisions

- [ ] ConfigEditor is the shared presentation/staging layer, not the governed writer.
- [ ] `pyprojectmgr` is the sole governed setup/mutation authority.
- [ ] Applications publish authenticated versioned contributions; application tabs are not hard-coded.
- [ ] Registry discovery is governed and identity-based; scanning alone is not authority.
- [ ] Governed writes require session locks, digest compare-and-swap, non-mutating staged validation, journaled recovery, strict postflight, and audit receipts.
- [ ] Governed delivery configuration and per-user state remain separate.
- [ ] Application hooks are governed, allowlisted, capability-limited, and fail closed.

### BFT reconciliation decisions

- [ ] BFT uses the `external_governed` validation profile.
- [ ] BFT remains on manifest `3.0.4` for reconciliation; `3.1.x` migration is separate.
- [ ] Existing BFT machine name is preserved until a stable project UID is bound.
- [ ] The three declared entry points are adopted.
- [ ] Infrastructure semantics are reviewed and the overly broad `src/` candidate is not retained without justification.
- [ ] Scan exclusions are synchronized through an approved scope decision.
- [ ] pyprojectmgr producer/validator agreement is repaired before schema-shaped fields are changed.
- [ ] The structured retired-UID policy and approved team role map are adopted.
- [ ] The legacy `meta` block is retained for `3.0.4`, with migration history added.
- [ ] `bundle_config.json` remains byte-identical during reconciliation.

## 6. Approval conditions recommended by Paul

The approval should carry these conditions:

1. **Canonical schema condition:** pyprojectmgr must identify one external-governed schema/profile and make initialization, validation, and export agree on it.
2. **No blind upgrade condition:** BFT manifest `3.0.4` reconciliation and migration to `3.1.x` are separate reviewed changes.
3. **Exact-diff condition:** George approves an exact staged before/after diff before live mutation.
4. **Config preservation condition:** `bundle_config.json` and its SHA-256 do not change in the reconciliation package.
5. **Infrastructure semantics condition:** the pyprojectmgr owner confirms what `infrastructure_patterns` exclude or seed before the final list is approved.
6. **Identity condition:** a stable external project UID mechanism is ratified before ConfigEditor registration.
7. **Recovery condition:** backups cover the complete manifest/generated-artifact set and rollback is verified.
8. **No auto-heal condition:** staging and postflight run without unapproved remediation.

## 7. What approval authorizes

Approval of this memorandum authorizes:

- recording the ADRs as the Phase 0 architectural baseline;
- correcting pyprojectmgr's producer/validator contract under its own governed change process;
- preparing BFT schema/metadata changes in an isolated staging copy;
- generating exact diffs and validation evidence for George's final implementation approval;
- preparing the read-only ConfigEditor/BFT contribution prototype after the contract is frozen.

## 8. What approval does not authorize

It does not authorize:

- live modification of BFT governed metadata before the Gate A and staged-diff conditions pass;
- any direct ConfigEditor write to BFT configuration;
- changing `bundle_config.json` values;
- weakening `ConfigManager.save()` protection;
- removing legacy user-state keys without a separate versioned migration;
- auto-heal or export changes outside an approved transaction plan;
- ThermX/SplashX production registration;
- a BFT manifest `3.1.x` migration.

## 9. Phase 0 completion gate

Phase 0 is complete only when:

1. all five ADRs have an approved or approved-with-conditions disposition;
2. all conditions are recorded in a decision register;
3. pyprojectmgr canonical producer/validator behavior is proven by tests;
4. BFT's exact staged reconciliation diff passes all canonical validators;
5. BFT identity, entry points, infrastructure semantics, scan scope, configuration paths, and team metadata are approved;
6. the config digest is unchanged and verified;
7. George approves controlled implementation and Ringo accepts the baseline;
8. final hashes and validation evidence are attached to the implementation receipt.

## 10. Proposed immediate assignment after approval

| Sequence | Owner | Assignment | Output |
|---:|---|---|---|
| 1 | George | Record ADR dispositions and conditions | Approved Phase 0 decision baseline |
| 2 | pyprojectmgr owner / Paul | Reconcile schema producer and validators for external manifests | Passing contract tests and canonical schema declaration |
| 3 | Ringo / George | Confirm project identity display, team roles, maintainer/license, and infrastructure semantics | Completed decision register |
| 4 | Paul | Prepare isolated BFT exact diff and execute read-only/staged validation | Staged reconciliation evidence package |
| 5 | George | Approve or return exact BFT diff | Controlled mutation authority or revision |
| 6 | Paul | Execute governed reconciliation, postflight, regression, and receipt | Reconciled BFT baseline |

## 11. Overall approval record

### George — architecture and controlled-work authorization

- [ ] Approved as recommended
- [ ] Approved with conditions below
- [ ] Returned for revision
- [ ] Rejected

**Conditions / rationale:**

> 

**Name/signature:** ____________________  **Date:** __________

### Ringo — product/governance acceptance

- [ ] Accepted
- [ ] Accepted with conditions below
- [ ] Returned for revision

**Conditions / rationale:**

> 

**Name/signature:** ____________________  **Date:** __________

### John — consulted technical review

- [ ] Reviewed — no objection
- [ ] Reviewed — comments attached
- [ ] Not reviewed due to availability

**Comments:**

> 

**Name/signature:** ____________________  **Date:** __________

## 12. Recommendation

Approve the architecture ADRs and authorize only the contract-repair and staged-reconciliation work at this time. This gives the team a clear start while preserving the BFT integrity boundary and ensuring that pyprojectmgr's own schema tools agree before they are used to rewrite BFT's governed baseline.
