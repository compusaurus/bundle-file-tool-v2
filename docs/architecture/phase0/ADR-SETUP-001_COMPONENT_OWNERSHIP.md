# ADR-SETUP-001: Component Ownership for Central Setup

**Status:** Proposed  
**Date:** 2026-08-26  
**Decision owner:** George, Lead Architect  
**Implementation owner:** Paul, Lead Developer / Lead Analyst  
**Product acceptance:** Ringo  
**Consulted:** John, Lead Developer  
**Supersedes:** None

## Context

George has directed that ConfigEditor become the central modular configuration hub and that `pyprojectmgr` orchestrate setup and enforce architecture/manifest compliance. The existing ConfigEdit implementation currently combines presentation, validation, and direct target-file saving. BFT, however, has a ratified split in which governed `bundle_config.json` is read-only at runtime, while per-user convenience state is written by `UserStateStore`.

Without an explicit ownership decision, ConfigEditor could become a second configuration authority, application projects could duplicate setup UIs, and manifest integrity metadata could diverge from the files it governs.

## Decision

Adopt the following separation of responsibilities:

1. **Application projects own configuration meaning.** Each application owns stable setting IDs, schemas, defaults, validation, migration, classification, and activation semantics.
2. **ConfigEditor owns presentation and staged editing.** It renders application tabs and section sub-tabs, holds an in-memory working copy, performs local validation, and produces a redacted proposal/diff.
3. **`pyprojectmgr` owns governed orchestration and mutation.** It authenticates contributions, opens sessions, locks targets, validates proposals, authorizes changes, commits recoverably, synchronizes integrity metadata, runs postflight, and emits audit evidence.
4. **Application runtimes consume but do not mutate governed delivery configuration.** User-local preferences remain under an application-owned user-state service.
5. **Installers own initial placement and filesystem protection.** They install governed payloads and restore the approved permissions/attributes after authorized maintenance.

For a governed document, ConfigEditor has no direct filesystem save authority. The existing ConfigEdit `ConfigModel.save()` may be retained only for explicitly classified non-governed/test adapters and may not be reachable from the governed setup controller.

## Responsibility matrix

| Capability | Application | ConfigEditor | pyprojectmgr | Installer/runtime |
|---|---:|---:|---:|---:|
| Define setting semantics/schema | A/R | C | C | I |
| Define tabs/sections/labels | A/R | renders | validates contract | I |
| Hold working copy and diff | C | A/R | verifies | I |
| Authenticate project/contribution | I | consumes | A/R | C |
| Authorize governed change | C | presents | A/R | I |
| Write governed config | I | prohibited | A/R | installer only at install/upgrade |
| Update governed digest/manifest | I | prohibited | A/R | C |
| Write user preferences | defines service | may invoke service | I | application user-state service A/R |
| Recover interrupted governed write | C | reports | A/R | C |
| Produce audit receipt | C | displays | A/R | I |

## Invariants

- No application-specific writer is added to ConfigEditor.
- No governed target path originates from free-form UI input.
- No governed Apply operation succeeds without `pyprojectmgr` validation and authorization.
- No application runtime regains a save path for governed delivery configuration.
- ConfigEditor remains read-only for governed values when `pyprojectmgr` is unavailable or unhealthy.
- Application labels are presentation; stable IDs are contract identity.

## Alternatives considered

### ConfigEditor owns all configuration files

Rejected. It centralizes write power without application semantics or governance transactions, creates a monolithic failure boundary, and conflicts with BFT's read-only contract.

### Each application owns a complete settings UI and writer

Rejected. It duplicates interaction patterns and governance logic, creates inconsistent approvals, and prevents suite-level oversight.

### pyprojectmgr owns the UI as well as governance

Rejected as the primary architecture. It would couple governance internals to toolkit-specific presentation and reduce ConfigEditor's value as a reusable setup shell. `pyprojectmgr` may host service endpoints and administration diagnostics, but application editing presentation belongs to ConfigEditor.

### Permit ConfigEditor to write, then ask pyprojectmgr to verify

Rejected. Post-write verification cannot prevent partial writes, stale overwrites, or an interval in which configuration and integrity metadata disagree.

## Consequences

### Positive

- One predictable setup surface without centralizing application data ownership.
- BFT's governed/user-state split remains intact.
- Manifest compliance is enforced before and after mutation.
- Tk and web presentations can share the same session contract.
- Application contributions can evolve independently under versioned contracts.

### Costs and constraints

- `pyprojectmgr` must gain a setup registry, session service, and transaction service before production Apply can be enabled.
- ConfigEdit's current direct-save flow requires refactoring.
- Application teams must publish schemas and contribution descriptors.
- Local validation and authoritative validation must share diagnostic identities to avoid contradictory feedback.

## Compliance evidence required

1. A code search proves no governed ConfigEditor controller calls a direct file-save method.
2. BFT tests continue to prove `ConfigManager.save()` raises `ReadOnlyConfigError`.
3. User-state changes do not change the governed config digest.
4. An unavailable `pyprojectmgr` produces read-only UI behavior.
5. End-to-end evidence shows `pyprojectmgr` performed the governed commit and digest synchronization.

## Approval record

George should select one disposition:

- [ ] Approved as written
- [ ] Approved with conditions recorded below
- [ ] Returned for revision
- [ ] Rejected

**Conditions / rationale:**

> 

**George:** ____________________  **Date:** __________  
**Ringo acceptance:** ____________________  **Date:** __________
