# BFT Governance Reconciliation Proposal

**Status:** Proposed; approval package only — no governed metadata changed  
**Date:** 2026-08-26  
**Approval owner:** George, Lead Architect  
**Implementation owner after approval:** Paul, Lead Developer / Lead Analyst  
**Product acceptance:** Ringo  
**Consulted:** John, Lead Developer

## 1. Purpose

Establish one coherent, validated BFT governance baseline before BFT becomes the reference application for ConfigEditor setup. This proposal records observed evidence, recommended field dispositions, a controlled mutation sequence, validation gates, rollback conditions, and decisions requiring George's approval.

This document is not an executable patch and does not authorize direct hand-editing of `.pyprojectmgr/project_manifest.json`.

## 2. Scope

### In scope

- `.pyprojectmgr/project_spec.json` and `.pyprojectmgr/project_manifest.json` alignment;
- entry points, infrastructure patterns, scan exclusions, configuration path representation, schema-shaped empty values, migration evidence, and project identity metadata;
- preservation and verification of the `bundle_config.json` integrity binding;
- selection of the canonical pyprojectmgr validation profile/schema and controlled export/preflight sequence;
- evidence required before ConfigEditor registration.

### Out of scope

- changing BFT application behavior or governed setting values;
- removing legacy BFT user-state seed keys;
- implementing ConfigEditor or the pyprojectmgr setup transaction service;
- upgrading BFT's manifest to `3.1.5` in the same change;
- registering BFT as writable in ConfigEditor;
- changing ThermX or SplashX.

## 3. Baseline snapshot

Observed in the BFT workspace on 2026-08-26:

| Artifact | SHA-256 |
|---|---|
| `.pyprojectmgr/project_spec.json` | `a7db28e5140634f9b7abcf361c4a807fce24a594322f92e5610f9c1689ea3a2b` |
| `.pyprojectmgr/project_manifest.json` | `ba59c4b0a1473f6ff8073db3a0b74b701f0b9e65ce87ac4a0499729ac2df0126` |
| `bundle_config.json` | `7ac770bcc0b906a6e60920202a6aec7ddd88a140ac146e9243df70823a9ea0c4` |

The manifest's `governance.governed_config_sha256` is also:

```text
7ac770bcc0b906a6e60920202a6aec7ddd88a140ac146e9243df70823a9ea0c4
```

Therefore, the current governed-config content and manifest digest are synchronized. This package must not change `bundle_config.json`; its digest should remain unchanged through reconciliation.

The release identity is aligned at `2.1.116` across:

- `.pyprojectmgr/project_spec.json`;
- `.pyprojectmgr/project_manifest.json` `project_meta.version`;
- `.pyprojectmgr/project_manifest.json` legacy `meta.version`;
- `bundle_config.json`;
- `pyproject.toml`;
- `VERSION.txt`;
- `src/core/version.py` fallback.

## 4. Current validator evidence

### 4.1 Profile-driven manifest validator

Command executed read-only using the current pyprojectmgr codebase:

```powershell
python -B scripts/validate_project_manifest.py `
  --manifest <BFT>/.pyprojectmgr/project_manifest.json `
  --project-root <BFT> `
  --profile external_governed `
  --strict
```

Observed result:

- Status: **PASSED**
- Blockers: 0
- Errors: 0
- Warnings: 1 — `T2_MIGRATION_VERSION_MISSING`
- Info: 1 — `T4_LEGACY_BLOCK_PRESENT`

The warning states that manifest version `3.0.4` is absent from `migration_history`. The informational finding identifies legacy `meta` alongside `project_meta`.

### 4.2 Separate governance-schema validator

Command executed read-only:

```powershell
python -B scripts/validate_governance_schema.py `
  <BFT>/.pyprojectmgr/project_manifest.json
```

Observed result: **FAILED** with two errors:

1. `governance.static_asset_categories must be an object`
2. `governance.configuration_paths must be an object`

Both are currently arrays. The current pyprojectmgr `project_init.py` also contains list defaults for these fields, while `validate_governance_schema.py` requires objects. This is a pyprojectmgr producer/validator contract inconsistency, not merely a BFT content error.

### 4.3 Reconciliation consequence

The profile validator's PASS must not be treated as proof that every current governance surface agrees. George must designate the canonical target profile/schema, and pyprojectmgr must first make its producer and validators agree on the relevant field shapes.

## 5. Observed differences

| Area | `project_spec.json` | `project_manifest.json` | Assessment |
|---|---|---|---|
| Project name | `bundle_file_tool_v2` | `BFT_v2` | Identity ambiguity; do not rename casually |
| Application version | `2.1.116` | `2.1.116` | Aligned |
| Manifest version | `3.0.4` | `3.0.4` | Aligned; preserve during this reconciliation |
| Orphan entry points | `src/main.py`, `src/cli.py`, `src/ui/main_window.py` | empty | Material governance gap |
| Orphan infrastructure patterns | `src/core/`, `src/database/`, `src/ui/` | `src/core/`, `src/` | Material drift; broad `src/` weakens reachability coverage |
| Duplicate governance infrastructure patterns | not separately represented | `src/core/`, `src/` | Must match ratified orphan list while compatibility field exists |
| Scan exclusions | Includes `.venv`, `build`, `htmlcov`, `logs`, `sessions` | Omits those entries | Drift and scan-noise risk |
| Retired UID structure | structured object with domain arrays/rules | empty array | Type/contract drift |
| Team | not represented | empty array | Inadequate identity/governance metadata for suite registry |
| `static_asset_categories` | not represented | empty array | Fails current governance-schema validator; producer inconsistency exists |
| `configuration_paths` | not represented | empty array | Fails current governance-schema validator and does not bind BFT config locations |
| `entry_point_registry` | not represented | empty object | Semantics/type unresolved; current pyprojectmgr commonly uses a path string |
| Config integrity digest | not represented | matches actual BFT config | Correct; preserve |
| Legacy `meta` | not represented | present and version-aligned | Retain for 3.0.4 compatibility; plan major-version removal |
| Migration history | not represented | empty | Generates current validator warning |

## 6. Recommended decisions

### R-01 — Validation profile

Approve `external_governed` as BFT's canonical pyprojectmgr validation profile. BFT must not inherit the stricter `pyprojectmgr_native` policy simply because it is managed by pyprojectmgr.

### R-02 — Manifest version

Preserve BFT manifest version `3.0.4` for this reconciliation. Treat migration to the current pyprojectmgr `3.1.x` contract as a separate approved change after producer, metaschema, validator, and export compatibility are proven.

### R-03 — Project identity

Preserve existing `project_meta.name = "BFT_v2"` during this minimal reconciliation to avoid an unanalysed identity migration. Require pyprojectmgr to assign/bind a stable external-project UID before ConfigEditor registration. Use `Bundle File Tool v2` as display metadata, not identity.

After a stable UID exists, the team may separately decide whether to normalize the machine name to `bundle_file_tool_v2`.

### R-04 — Entry points

Set the manifest's canonical orphan-detection entry points to the three currently declared by BFT's project specification:

```json
[
  "src/main.py",
  "src/cli.py",
  "src/ui/main_window.py"
]
```

All three exist. `src/main.py` and `src/cli.py` are direct application surfaces; `src/ui/main_window.py` also contains a direct `main()`/`__main__` surface and is already explicitly declared by the BFT specification.

### R-05 — Infrastructure patterns

Adopt the project specification's narrower candidate list in both manifest locations while the duplicate compatibility field remains:

```json
[
  "src/core/",
  "src/database/",
  "src/ui/"
]
```

This is recommended over `src/` because the broader pattern can exempt the entire source tree from useful reachability analysis. Before approval, the pyprojectmgr owner must confirm the exact exclusion/coverage semantics; if whole-package entries disable meaningful orphan detection, George should narrow the list further rather than restore `src/`.

### R-06 — Scan exclusions

Use the `project_spec.json` exclusion set as the minimum synchronized set in both artifacts:

```text
__pycache__, .git, .idea, .vscode, .venv, venv, env, dist, build,
*.egg-info, htmlcov, logs, sessions
```

Before applying, explicitly decide whether generated `out/`, delivery bundles, governance backups, and archives belong in scan scope or need governed exclusions. Do not add broad exclusions merely to make findings disappear.

### R-07 — Schema-shaped governance values

After pyprojectmgr's producer/validator disagreement is resolved, use the canonical object shapes. Candidate BFT configuration-path representation:

```json
{
  "paths": [
    "bundle_config.json",
    "config/",
    ".pyprojectmgr/"
  ],
  "exclude": [
    ".pyprojectmgr/cache/",
    ".pyprojectmgr/logs/",
    ".pyprojectmgr/backups/"
  ],
  "path_type": "relative",
  "description": "BFT governed application configuration and governance metadata"
}
```

Candidate `static_asset_categories` value is `{}` until BFT declares actual categories. George should not approve these shapes as final until the canonical pyprojectmgr schema and generator accept and reproduce them.

### R-08 — Retired UIDs

Replace the empty manifest array with the structured object already declared by `project_spec.json`, preserving empty domain lists and the never-reuse/reason/replacement rules. This makes the policy explicit and avoids future type migration when the first UID is retired.

### R-09 — Project metadata

Change `project_meta.team` from an empty array to the schema-appropriate role map after Ringo confirms current assignments. Proposed map:

```json
{
  "ringo": "Owner",
  "george": "Lead Architect",
  "paul": "Lead Developer / Lead Analyst",
  "john": "Lead Developer Reviewer"
}
```

Maintainer and license remain open product/legal metadata decisions. They are not guessed in this package.

### R-10 — Migration evidence and legacy metadata

Add a `migration_history` record for the approved `3.0.4` reconciliation using the canonical schema fields and actual approval date. Retain legacy `meta` synchronized with `project_meta` during the `3.0.4` line; remove it only at an approved major manifest migration.

### R-11 — Empty entry-point registry

Do not invent a BFT maintenance registry merely to replace the current `{}`. pyprojectmgr must declare whether the field is optional/omitted or a required path string for external governed projects. Resolve it under the canonical schema before mutation.

### R-12 — Config integrity

Do not change `bundle_config.json` in this work package. Recompute its SHA-256 during the controlled process and require it to remain:

```text
7ac770bcc0b906a6e60920202a6aec7ddd88a140ac146e9243df70823a9ea0c4
```

If it differs, stop. That is configuration drift or a separate proposed configuration change, not manifest reconciliation.

## 7. Proposed field disposition matrix

| JSON pointer / area | Action | Approval condition |
|---|---|---|
| `/manifest_version` | Preserve `3.0.4` | R-02 |
| `/manifest_type` | Preserve current external-governed value during this change | Canonical external schema confirms |
| `/project_meta/name` | Preserve `BFT_v2` | Stable UID decision deferred |
| `/project_meta/full_name` | Normalize display metadata only if approved | Ringo confirms label |
| `/project_meta/team` | Convert to approved role map | R-09 |
| `/project_meta/maintainer` | Hold | Ringo supplies value |
| `/project_meta/license` | Hold | Product/legal decision |
| `/governance/orphan_detection/entry_points` | Set three declared entry points | R-04 |
| `/governance/orphan_detection/infrastructure_patterns` | Set approved narrow list | R-05 semantic confirmation |
| `/governance/infrastructure_patterns` | Mirror exact approved list while field exists | Avoid T4 drift |
| `/governance/scanning/exclusion_patterns` | Synchronize approved set | R-06 scope review |
| `/governance/retired_uids` | Convert to structured object | R-08/schema acceptance |
| `/governance/static_asset_categories` | Convert to canonical object | pyprojectmgr producer fixed/ratified |
| `/governance/configuration_paths` | Convert to ratified object | R-07/schema acceptance |
| `/governance/entry_point_registry` | Hold pending external-schema decision | R-11 |
| `/governance/governed_config_sha256` | Preserve/reverify | R-12 |
| `/migration_history` | Append reconciliation record | R-10 |
| `/meta` | Retain and synchronize | Remove only at major migration |
| `project_spec` overlapping governance fields | Synchronize to approved decisions | Manifest remains installed authority |

## 8. Source-of-truth rule

For the installed application, `.pyprojectmgr/project_manifest.json` remains the authoritative governed identity because both artifacts currently declare `identity_source = "manifest"`. `project_spec.json` is valuable desired-state/input evidence, but this review found no basis to assume that `manifest_manager --export` copies its values into the manifest.

Therefore:

- approved differences must be applied through the canonical pyprojectmgr mutation/generation process;
- `project_spec.json` must then be synchronized as required by that process;
- no operator should manually copy the whole spec governance object over the manifest;
- generated artifacts are refreshed only after the manifest proposal validates.

## 9. Controlled execution plan after approval

### Gate A — pyprojectmgr contract repair

1. Assign one canonical external-governed schema/profile for BFT `3.0.4`.
2. Reconcile `project_init.py`, governance-schema validation, metaschema expectations, and export behavior for `static_asset_categories` and `configuration_paths`.
3. Add pyprojectmgr tests proving new external manifests are generated in the same shape every canonical validator accepts.
4. Confirm the semantics and type of `entry_point_registry` for an external application without a maintenance menu.

No BFT governed mutation occurs before Gate A passes.

### Gate B — immutable baseline and proposal

1. Require a clean, approved BFT governance work package or explicitly catalog unrelated working-tree changes.
2. Recompute and record hashes for spec, manifest, config, and generated governance artifacts.
3. Create recoverable copies in the approved governance backup location.
4. Generate an exact before/after JSON diff containing only approved fields.
5. Verify `bundle_config.json` is byte-identical and its hash is unchanged.

### Gate C — staged validation

1. Apply the proposal to a staging copy, not the live BFT tree.
2. Run external-governed manifest validation in strict mode.
3. Run the canonical governance-schema validator.
4. Run referential/path checks with assets present.
5. Confirm entry-point files exist and infrastructure patterns have approved semantics.
6. Confirm duplicate infrastructure lists are identical.
7. Confirm no new errors, blockers, or unapproved warnings.
8. Run governance preflight with `auto_heal=False`.

### Gate D — authorized mutation/export

1. Obtain George's approval on the exact staged diff and evidence.
2. Apply through the canonical pyprojectmgr mutation mechanism.
3. Run `manifest_manager --export --project-root <BFT>` only after confirming the generated-artifact plan and backup coverage.
4. Do not allow export/remediation to broaden the approved change silently.
5. Recompute manifest and generated-artifact hashes.

### Gate E — postflight

1. Repeat strict external-governed manifest and governance-schema validation.
2. Run strict governance preflight without remediation.
3. Run BFT integrity-layer tests and full regression suite.
4. Prove `bundle_config.json` digest matches the manifest.
5. Prove `ConfigManager.save()` remains prohibited.
6. Produce an approval/implementation receipt and update the package with final hashes.

## 10. Stop and rollback conditions

Stop without committing, or restore the verified baseline, if:

- `bundle_config.json` changes;
- its SHA-256 differs from the approved baseline;
- canonical validators disagree on the staged manifest;
- entry-point or infrastructure semantics are unresolved;
- export changes fields/artifacts outside the approved plan;
- generated-artifact verification fails;
- any BFT integrity or regression test fails;
- file protection cannot be restored;
- the pre-change baseline cannot be proven.

Rollback must restore the full manifest/generated-artifact set, not only one JSON file.

## 11. Acceptance criteria for BFT reconciliation

1. One declared external-governed profile/schema is authoritative.
2. All canonical validators agree and pass.
3. Manifest and project specification contain the same approved entry points, infrastructure patterns, scan exclusions, and retired-UID policy.
4. All declared entry points exist.
5. `configuration_paths` explicitly binds BFT's governed configuration locations in the canonical shape.
6. The BFT config SHA-256 remains correct and unchanged.
7. Project identity and team metadata are sufficient for authenticated suite registration.
8. No runtime governed-write authority is introduced.
9. Strict postflight and the complete BFT regression suite pass.
10. George approves the final diff/evidence and Ringo accepts the reconciled baseline.

## 12. Approval record and decisions

George should record each decision rather than granting a blanket approval:

| Decision | Approve | Conditions / alternative |
|---|---:|---|
| R-01 external-governed validation profile | [ ] | |
| R-02 preserve manifest `3.0.4` for reconciliation | [ ] | |
| R-03 preserve current name pending stable UID | [ ] | |
| R-04 three entry points | [ ] | |
| R-05 narrower infrastructure candidate and semantic review | [ ] | |
| R-06 synchronized exclusion set and scope review | [ ] | |
| R-07 object-shaped configuration/static category fields after PPM repair | [ ] | |
| R-08 structured retired-UID policy | [ ] | |
| R-09 team role map | [ ] | |
| R-10 migration record and legacy-meta retention | [ ] | |
| R-11 hold entry-point registry pending schema ruling | [ ] | |
| R-12 preserve/reverify BFT config digest | [ ] | |

**Overall disposition:**

- [ ] Approved for controlled implementation after Gate A
- [ ] Approved with conditions
- [ ] Returned for revision
- [ ] Rejected

**Conditions / rationale:**

> 

**George:** ____________________  **Date:** __________  
**Ringo acceptance:** ____________________  **Date:** __________
