# ConfigEditor Setup Contracts

**Date:** 2026-08-26  
**Status:** Proposed contract set; requires architecture ratification before implementation  
**Scope:** ConfigEditor, `pyprojectmgr`, and contributing application projects

## 1. Purpose

This document defines the boundaries that turn ConfigEditor into a modular suite setup surface without weakening application governance. The contract has four layers:

1. an application contribution descriptor;
2. a setup-session protocol between ConfigEditor and `pyprojectmgr`;
3. an application validation/migration interface;
4. a governed transaction and evidence contract.

The descriptor example is illustrative. Field names become normative only after the team approves contract version `1.0` and publishes its metaschema.

## 2. Roles and authority

### 2.1 Application contribution

The application owns:

- stable application, document, section, and field IDs;
- configuration schemas and defaults;
- labels and help text;
- field classification and sensitivity;
- cross-field validation;
- schema migration;
- reload/restart semantics;
- application-specific post-apply health checks.

### 2.2 ConfigEditor

ConfigEditor owns:

- consistent tab/sub-tab presentation;
- typed controls and accessibility;
- in-memory working copies and dirty tracking;
- local schema feedback;
- redacted change review;
- submitting proposals and displaying authoritative outcomes.

ConfigEditor has no authority to write governed application files or manifests.

### 2.3 pyprojectmgr

`pyprojectmgr` owns:

- the authenticated application registry;
- manifest, descriptor, schema, and contract verification;
- session identities, locks, and baseline digests;
- authorization and approval policy;
- authoritative validation and path containment;
- journaled writes and recovery;
- integrity metadata synchronization;
- postflight validation and audit receipts.

## 3. Application contribution descriptor

### 3.1 Discovery

Recommended location:

```text
<project-root>/.pyprojectmgr/setup_contribution.json
```

The project manifest should reference and digest the descriptor. The descriptor should reference and digest each schema. A filesystem scan may locate candidates, but it must not establish trust. Only entries authenticated by `pyprojectmgr`'s governed registry and project manifest are presented.

### 3.2 Proposed descriptor shape

```json
{
  "contract_version": "1.0",
  "application": {
    "id": "bundle_file_tool",
    "label": "Bundle File Tool",
    "project_uid": "<governed-project-uid>",
    "application_version": "2.2.0",
    "order": 100
  },
  "documents": [
    {
      "id": "delivery_config",
      "path": "bundle_config.json",
      "format": "json",
      "schema": ".pyprojectmgr/schemas/bundle_config.schema.json",
      "governance_class": "governed_delivery",
      "edit_policy": "orchestrated",
      "manifest_digest_pointer": "/governance/governed_config_sha256"
    },
    {
      "id": "user_state",
      "location_provider": "bundle_file_tool.user_state:resolve_path",
      "format": "json",
      "schema": ".pyprojectmgr/schemas/user_state.schema.json",
      "governance_class": "user_preference",
      "edit_policy": "user_mutable"
    }
  ],
  "navigation": {
    "sections": [
      {
        "id": "bundle_defaults",
        "label": "Bundle Defaults",
        "order": 200,
        "fields": [
          {
            "id": "default_encoding",
            "document": "delivery_config",
            "pointer": "/app_defaults/encoding",
            "control": "choice",
            "help": "Encoding used for newly created bundles.",
            "restart": "next_operation"
          }
        ]
      }
    ]
  },
  "integration": {
    "validator": "bundle_file_tool.setup:validate_proposal",
    "migrator": "bundle_file_tool.setup:migrate_document",
    "postflight": "bundle_file_tool.setup:postflight",
    "reload": "restart_required"
  },
  "governance": {
    "preflight_profile": "application_setup_v1",
    "approval_policy": "standard",
    "post_apply_gates": ["manifest", "schema", "application"]
  }
}
```

For security, integration values are governed import references resolved from allowlisted installed packages. Arbitrary executable strings, shell commands, and URLs are forbidden.

### 3.3 Required descriptor fields

| Field | Requirement |
|---|---|
| `contract_version` | Exact supported major version; unsupported major versions are read-only and diagnostically visible |
| `application.id` | Stable lowercase identifier; unique in the registry |
| `application.project_uid` | Must match the authenticated project manifest |
| `application.order` | Deterministic top-level tab order |
| `documents[].id` | Unique within the application |
| `documents[].path` or approved provider | Must resolve through `pyprojectmgr`; never accepted directly from a UI request |
| `documents[].format` | Initially `json`; additional formats require an adapter contract |
| `documents[].schema` | Governed, digested schema compatible with the document format |
| `documents[].governance_class` | Determines authorization, write authority, backup, audit, and display behavior |
| `documents[].edit_policy` | `orchestrated`, `user_mutable`, or `read_only` |
| `navigation.sections[].id` | Stable section/sub-tab identifier |
| `navigation.sections[].fields[].pointer` | RFC 6901 JSON Pointer for JSON documents; no ambiguous dotted paths |
| `governance.preflight_profile` | An allowlisted `pyprojectmgr` policy profile |

### 3.4 Governance classes

| Class | Typical contents | Writer | Audit expectation |
|---|---|---|---|
| `governed_delivery` | Safety policy, application defaults, controlled feature policy | `pyprojectmgr` transaction service only | Full before/after digest, authorization, postflight, receipt |
| `user_preference` | Window geometry, remembered folders, view preferences | User-state service under the current user | Minimal event metadata; values may be omitted from central audit |
| `profile` | Named runtime profile selected by an application | Depends on declared policy; governed profiles use `pyprojectmgr` | Policy-dependent receipt and restart information |
| `runtime_override` | Command-line or environment-derived effective value | Not writable by ConfigEditor | Display source/effective value; no Apply control |
| `secret_reference` | Credential handle or vault reference | Approved secret provider | Never expose secret material in snapshots or receipts |
| `derived` | Calculated or discovered values | No writer | Read-only display only |

## 4. Navigation and field contracts

### 4.1 Application tabs

- Generated only from authenticated compatible contributions.
- Ordered by `application.order`, then stable `application.id` as a deterministic tie-breaker.
- Duplicate IDs, duplicate project UIDs, or conflicting registrations block the affected contribution.
- An unhealthy contribution is shown in a diagnostic state only if policy permits; it is never silently omitted in administrator mode.

### 4.2 Section sub-tabs

- Generated from `navigation.sections`.
- A section may contain fields from more than one document only when their commit policy is compatible and the review UI identifies each source.
- Hidden fields may not be used to bypass validation. Values omitted from navigation remain preserved and validated.
- Section labels are localizable presentation text; logic uses IDs.

### 4.3 Fields

Each field should declare or inherit:

- document ID and JSON Pointer;
- display label and help;
- control hint;
- editability and classification;
- sensitivity/redaction policy;
- restart or reload impact;
- optional visibility/enabling expressions expressed through a safe declarative grammar;
- optional elevated approval class.

The document schema remains the source of truth for data type, enum, minimum/maximum, pattern, required status, and object shape. UI hints may narrow presentation but may not weaken the schema.

Expressions must not execute application code in the UI process. The initial contract should support only comparisons, boolean composition, and references to fields in the same contribution.

## 5. Setup-session protocol

The protocol may be implemented as an in-process service first and exposed through a local API later. Its semantics must remain transport-independent.

### 5.1 Session states

```text
OPEN -> DIRTY -> VALIDATING -> VALIDATED -> COMMITTING -> APPLIED
  |       |           |            |             |
  +-------+-----------+------------+-------------+-> REJECTED/CLOSED
                                                +-> RECOVERING -> RECOVERED/FAILED
```

Only `VALIDATED` may advance to `COMMITTING`. A changed proposal invalidates the prior validation result.

### 5.2 Open-session result

The authoritative result contains:

- opaque session ID and expiry;
- actor/authority classification;
- application and descriptor versions;
- immutable document snapshots or redacted views;
- baseline digests;
- schema and navigation metadata;
- effective-value source information where available;
- write permissions and approval requirements;
- current governance diagnostics.

### 5.3 Proposal

ConfigEditor submits a bounded set of operations, preferably RFC 6902 JSON Patch for JSON documents, plus:

- session ID;
- application ID;
- descriptor digest/version;
- baseline document digests;
- user-visible justification when required;
- approval evidence token, never raw credentials.

Full-document replacement should not be the normal API because it obscures intent and increases lost-update risk.

### 5.4 Validation result

Diagnostics use stable machine-readable fields:

```json
{
  "severity": "error",
  "code": "BFT_SETUP_SAFETY_GLOB_INVALID",
  "application_id": "bundle_file_tool",
  "document_id": "delivery_config",
  "pointer": "/safety/deny_globs/2",
  "message": "Pattern is not valid for the configured matcher.",
  "remediation": "Correct or remove the pattern.",
  "source": "application_validator"
}
```

Severity values are `info`, `warning`, `error`, and `blocker`. `error` and `blocker` prevent commit. Warnings require acknowledgement when the policy profile says so.

### 5.5 Stale-session rule

Immediately before committing, `pyprojectmgr` recomputes every baseline digest. Any mismatch produces a stale-session rejection. ConfigEditor then offers reload and reapply; it does not auto-merge governed policy.

## 6. Application integration interface

The application hook interface must be pure or explicitly classified.

### 6.1 Validator

Inputs:

- immutable baseline documents;
- immutable proposed documents;
- application/version context;
- validation phase (`local_equivalent`, `staged`, or `postflight`).

Output:

- structured diagnostics only.

The validator must not write files, mutate manifests, start the application, access secrets not supplied as redacted references, or change the proposal.

### 6.2 Migrator

Inputs:

- source document and schema version;
- target schema version;
- migration context.

Output:

- migrated document;
- structured change list;
- warnings and required approvals.

Migrations are explicit setup operations. Opening an old document may preview a migration, but must not silently persist it.

### 6.3 Postflight

Postflight verifies the installed state after commit. It may read committed documents and controlled metadata, but should not repair them. Repair is a separate recovery or maintenance operation.

### 6.4 Reload adapter

A reload adapter, if supplied, must declare safe invocation conditions and a timeout. Failure to reload does not roll back a correctly committed configuration unless the application contract explicitly makes activation part of transactional success. The receipt must distinguish **committed** from **active**.

## 7. Governed transaction contract

### 7.1 Pre-commit gates

All must pass:

1. authenticated project, descriptor, and schemas;
2. compatible contract version;
3. active session and valid scoped lock;
4. actor authorization and required approval;
5. unchanged baseline digests;
6. path containment and target-policy checks;
7. document schema validation;
8. application validation;
9. staged architecture and manifest validation;
10. backup/journal destination health.

Governance preview runs with automatic remediation disabled.

### 7.2 Commit record

The journal records, without secrets:

- transaction and session IDs;
- application/project identity;
- actor authority and approval reference;
- target paths represented relative to project root;
- expected before and after digests;
- backup and temporary-file identities;
- ordered commit steps and durable completion markers;
- recovery status.

### 7.3 Commit behavior

- Acquire an exclusive target/project lock.
- Write durable backups before altering targets.
- Write and flush temporary siblings with controlled permissions.
- Update configuration and governed integrity metadata according to the journal plan.
- Persist progress markers after each completed operation.
- Run strict postflight.
- Restore read-only attributes/ACL policy.
- Mark complete only after the receipt is durable.

The implementation must include startup recovery for an interrupted transaction. It may choose roll-forward or rollback only when the journal and digest state prove that choice safe.

### 7.4 Audit receipt

Minimum fields:

- receipt and transaction IDs;
- timestamp in UTC;
- application/project identity and versions;
- contract and descriptor digest;
- actor/approval classification;
- result (`applied`, `recovered`, `rejected`, or `failed_recovery`);
- redacted changed pointers;
- before/after document and manifest digests;
- validation profile and summarized gate results;
- activation result (`active`, `restart_required`, `reload_failed`, or `not_applicable`).

Receipts should be integrity-protected. The signing or chained-hash method is a `pyprojectmgr` governance decision.

## 8. BFT reference contribution requirements

BFT should be the first contract implementation and must preserve these rules:

- `ConfigManager.save()` remains prohibited.
- `bundle_config.json` is `governed_delivery` and written only by `pyprojectmgr`.
- `UserStateStore` remains the authority for remembered open/save folders and window state.
- Legacy `global_settings.last_source_dir`, `global_settings.last_bundle_save_dir`, and `session` keys are hidden/deprecated and removed only through a versioned migration.
- Safety settings are elevated-impact and require explicit review/approval.
- "My Preferences" should offer safe user-state operations, such as reset remembered folders, without presenting legacy governed keys as active preferences.
- The Settings command launches/focuses a BFT-scoped ConfigEditor session; it never instructs the user to edit the governed JSON manually.

## 9. Versioning and compatibility

- Contract versions use semantic versioning.
- A major-version mismatch blocks editing.
- A newer compatible minor version may be accepted only when unknown fields are preserved.
- Descriptors declare minimum/maximum supported orchestrator capability where needed.
- Application schema version and contribution contract version are independent.
- Every committed receipt identifies both.

## 10. Contract acceptance tests

At minimum, the shared suite must prove:

- deterministic application and section ordering;
- duplicate/forged registration rejection;
- path traversal, symlink, and reparse-point escape rejection;
- schema and cross-field diagnostic mapping;
- type preservation and unknown-field preservation;
- read-only/derived field patch rejection;
- secret redaction in snapshots, logs, backups metadata, diffs, and receipts;
- stale-baseline rejection with two concurrent sessions;
- no writes during preview or failed validation;
- crash recovery at every journal step;
- config/manifest digest synchronization;
- postflight failure recovery;
- BFT runtime inability to write governed configuration;
- user-state changes not changing governed digests;
- unavailable/unhealthy `pyprojectmgr` yielding read-only behavior;
- real Tk and web UI tests for nested tabs, focus, overflow, and active scrolling.

## 11. Ratification questions

The team must settle these points before freezing `1.0`:

1. Is `.pyprojectmgr/setup_contribution.json` the canonical descriptor location, or is the manifest itself the descriptor container?
2. What is the authoritative suite registry and who may register/unregister applications?
3. Which identity/approval mechanism applies to safety- or deployment-impacting changes?
4. Which audit integrity mechanism is required?
5. Are user preferences displayed in ConfigEditor at launch, or behind a distinct mode to avoid confusing them with governed policy?
6. Does ThermX own a suite profile, or do its consumer applications own all persisted ThermX style settings?
7. Which SplashX profile installations are governed versus ordinary user profiles?

Until these questions are ratified, prototypes must remain read-only or use disposable test fixtures only.
