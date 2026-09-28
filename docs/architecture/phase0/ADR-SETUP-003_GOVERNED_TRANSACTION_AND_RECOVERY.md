# ADR-SETUP-003: Governed Setup Transaction and Recovery

**Status:** Proposed  
**Date:** 2026-08-26  
**Decision owner:** George, Lead Architect  
**Implementation owner:** Paul, Lead Developer / Lead Analyst  
**Product acceptance:** Ringo  
**Consulted:** John, Lead Developer  
**Depends on:** ADR-SETUP-001, ADR-SETUP-002

## Context

A governed configuration change can affect more than one file. BFT currently verifies `bundle_config.json` against `governance.governed_config_sha256` in `.pyprojectmgr/project_manifest.json`. Updating the configuration without synchronizing the manifest makes the application fail its integrity boundary. Replacing a single temporary file atomically does not make the configuration-plus-manifest update atomic.

The setup workflow must also prevent stale editors from overwriting newer changes, guarantee that preview is non-mutating, recover after process or machine interruption, restore file protection, and produce trustworthy evidence.

## Decision

`pyprojectmgr` will implement a **session-scoped, compare-and-swap, journaled governed transaction**.

### Session and baseline

1. `pyprojectmgr` opens an opaque setup session under an authenticated actor context.
2. It acquires a scoped project/application setup lock.
3. It reads all declared documents and records SHA-256 baseline digests, descriptor/schema versions, and relevant manifest state.
4. ConfigEditor receives immutable snapshots and edits only a working copy.

### Proposal and validation

1. ConfigEditor submits bounded patch operations, baseline digests, descriptor identity, justification, and approval evidence when required.
2. `pyprojectmgr` validates patch targets and classifications.
3. It applies the proposal to an isolated staging mirror.
4. It runs document schema, application, architecture, and manifest validation against the proposed state.
5. Preview/staged validation is guaranteed non-mutating. Automatic remediation is disabled.
6. Any error/blocker rejects the proposal without changing source files.

### Commit

Immediately before commit, `pyprojectmgr` recomputes baselines. Any mismatch rejects the session as stale.

If unchanged and authorized, it:

1. constructs an explicit transaction plan listing every target and expected before/after digest;
2. writes a durable recovery journal;
3. creates durable backups with controlled permissions;
4. writes and flushes temporary sibling files;
5. replaces targets in the journaled order, recording durable completion markers;
6. runs strict postflight validation;
7. restores the approved read-only/ACL policy;
8. writes an integrity-protected, redacted audit receipt;
9. marks the journal complete and releases the lock.

### Recovery

On startup and before new sessions, `pyprojectmgr` finds incomplete journals. It selects rollback or roll-forward only when recorded and observed digests prove the action safe. An unprovable state becomes `failed_recovery`, blocks further setup mutation for that project, and requires authorized maintenance.

## Transaction states

```text
OPEN -> DIRTY -> VALIDATING -> VALIDATED -> COMMITTING -> APPLIED -> CLOSED
  |        |           |            |             |
  +--------+-----------+------------+-------------+-> REJECTED
                                                 +-> RECOVERING
                                                       |-> RECOVERED
                                                       +-> FAILED_RECOVERY
```

A changed proposal invalidates a prior `VALIDATED` state. Only `VALIDATED` may enter `COMMITTING`.

## Non-negotiable controls

- No writes during open, preview, local validation, or failed authoritative validation.
- `auto_heal=False` or a dedicated read-only validation API for setup validation.
- One exclusive mutation lock per governed project scope.
- Digest compare-and-swap at commit time, not only session-open time.
- Path containment and target allowlist verification before staging and commit.
- Journal durability before target mutation.
- Recovery testing after every journal step.
- Secret redaction from diffs, logs, journal metadata, backups metadata, and receipts.
- Postflight failure is transaction failure, not warning-only success.
- Receipt distinguishes `committed` from `active`; restart/reload may be separate.

## BFT reference transaction

For a BFT governed setting change, the minimum transaction set is:

1. `bundle_config.json` proposed content;
2. `.pyprojectmgr/project_manifest.json` with the new `governed_config_sha256` and approved metadata changes;
3. generated governance artifacts that are normatively bound to the manifest, if the ratified pyprojectmgr export process requires them;
4. transaction journal, backups, and receipt.

The exact generated-artifact set must be produced by the canonical pyprojectmgr plan. ConfigEditor must not infer it.

## Alternatives considered

### Atomic replace of `bundle_config.json`, then update the manifest

Rejected. Interruption between the two replacements leaves an invalid integrity chain.

### Update the manifest first, then the configuration

Rejected for the same reason, with the divergence reversed.

### Write first and roll back only when postflight fails

Rejected without a durable pre-write journal and backups. A process or power failure may prevent the code that intended to roll back from running.

### Rely only on a file lock

Rejected. Locks do not detect external maintenance, stale network/portable state, or a process that ignored the lock. Digest compare-and-swap is also required.

### Let validation auto-heal drift

Rejected for normal setup. It silently broadens the approved proposal. Remediation is a distinct maintenance transaction with its own diff and approval.

## Consequences

### Positive

- Configuration and integrity metadata remain coherent across failures.
- Concurrent editors cannot silently overwrite one another.
- Every successful mutation has traceable validation and approval evidence.
- Recovery is deterministic and testable.

### Costs and constraints

- The transaction service is the critical-path implementation item.
- Cross-platform durability and file-protection semantics require explicit engineering.
- Multi-file rollback may be slower and requires retention policy.
- Application activation must be represented separately from commit success.

## Acceptance and failure-injection evidence

Required termination/failure points include:

- before journal durability;
- after each backup;
- after each temporary file flush;
- after each target replacement;
- during manifest update;
- during strict postflight;
- during protection restoration;
- during receipt creation;
- during rollback and roll-forward recovery.

For every point, evidence must prove either the exact approved after-state or the exact verified baseline. Otherwise the project remains blocked in `failed_recovery`.

## Approval record

- [ ] Approved as written
- [ ] Approved with conditions recorded below
- [ ] Returned for revision
- [ ] Rejected

**Conditions / rationale:**

> 

**George:** ____________________  **Date:** __________  
**Ringo acceptance:** ____________________  **Date:** __________
