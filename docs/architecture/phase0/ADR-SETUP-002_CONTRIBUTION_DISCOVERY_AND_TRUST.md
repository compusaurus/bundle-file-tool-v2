# ADR-SETUP-002: Application Contribution Discovery and Trust

**Status:** Proposed  
**Date:** 2026-08-26  
**Decision owner:** George, Lead Architect  
**Implementation owner:** Paul, Lead Developer / Lead Analyst  
**Product acceptance:** Ringo  
**Consulted:** John, Lead Developer  
**Depends on:** ADR-SETUP-001

## Context

ConfigEditor must build top-level application tabs and section sub-tabs without hard-coding Bundle File Tool, ThermX, SplashX, or future applications. Dynamic discovery introduces a trust boundary: finding a directory or JSON file does not prove that it is an approved application, that its paths are contained, that its schema is authentic, or that its integration hooks are safe.

BFT's current manifest has no ratified setup-contribution pointer or stable suite project UID. The proposed contract therefore requires a discovery and identity decision before registration can be implemented.

## Decision

Use **governed registry discovery with manifest-bound contributions**.

1. `pyprojectmgr` owns the canonical suite application registry.
2. Every registered application has a stable, non-label identity assigned through the governed registration process.
3. A registry record resolves an approved project root and expected manifest identity.
4. The project manifest references a versioned setup contribution descriptor and its digest, either directly or through a ratified governance extension.
5. Recommended descriptor location is `<project-root>/.pyprojectmgr/setup_contribution.json`; the manifest pointer, not the filename convention alone, establishes authority.
6. The descriptor references application configuration schemas and allowlisted integration hooks. Schema and descriptor digests are authenticated before use.
7. ConfigEditor receives only contributions that `pyprojectmgr` has authenticated and classified as compatible.
8. Filesystem scanning may produce diagnostics or registration candidates, but cannot create a trusted application or writable target.

## Identity rules

- `application_id`, `project_uid`, and document/section/field IDs are stable machine identities.
- Product names and tab labels are mutable presentation metadata.
- Duplicate project UIDs or application IDs block the conflicting registrations.
- A moved project root is an explicit registry maintenance event, not automatic retargeting.
- Registry paths are stored and displayed in normalized form; case and link/reparse-point behavior are handled according to the host filesystem.
- A target document must resolve within the authenticated project root unless its governance class uses an approved provider, such as BFT `UserStateStore`.

## Registration lifecycle

### Register

1. An authorized operator selects or supplies a project candidate.
2. `pyprojectmgr` resolves the real project root and manifest.
3. It validates the manifest under the declared external-project profile.
4. It verifies project identity, descriptor pointer/digest, descriptor metaschema, schemas, and hook allowlist.
5. It records the stable project/application identity and approved root in the governed registry.
6. It emits a registration receipt.

### Upgrade

An application upgrade that changes the descriptor, schema, hook package, or contract major version places that contribution in `upgrade_pending` until the governed registry is revalidated. Existing incompatible settings remain visible read-only with diagnostics.

### Move

A move requires explicit registry maintenance and reauthentication. The old root is retained in audit evidence but not used as a fallback.

### Unregister

Unregistration removes the application from active setup discovery but does not delete application configuration or evidence. Deletion is a separate authorized operation.

## Failure behavior

| Condition | Required behavior |
|---|---|
| Missing project root | Diagnostic registration state; no writable tab |
| Invalid/corrupt manifest | Fail closed; show administrator diagnostic |
| Descriptor digest mismatch | Fail closed; do not load descriptor or hooks |
| Unsupported contract major version | Read-only diagnostic state |
| Missing schema | Read-only diagnostic state |
| Duplicate application/project identity | Block both conflicting writable registrations pending resolution |
| Path containment failure | Reject contribution/target as a security defect |
| Higher descriptor minor version | Accept only under declared compatibility and unknown-field preservation rules |

## Alternatives considered

### Scan known parent folders for applications

Rejected as authority. It is convenient but cannot establish identity, authorization, or authenticity and is vulnerable to stale copies and backups—especially relevant in a workspace containing multiple BFT/pyprojectmgr variants.

### Hard-code the initial application list

Rejected. It violates the modularity objective and makes every new application a ConfigEditor release.

### Let each application self-register at runtime

Rejected as the default. An application process should not grant itself suite setup authority. Installers may request registration, but `pyprojectmgr` must authenticate and authorize the record.

### Trust the descriptor path supplied by ConfigEditor

Rejected. UI input cannot define a governed trust root.

## Consequences

### Positive

- Deterministic tab population and ordering.
- Clear diagnostics for missing, incompatible, duplicated, or tampered applications.
- Project copies, backups, and abandoned builds cannot silently become live setup targets.
- Contract versions and schemas can evolve under explicit compatibility rules.

### Costs and constraints

- A governed registry schema and lifecycle service must be designed.
- Each application needs a stable project/application identity.
- Installers/upgraders must participate in registration maintenance.
- Windows link/reparse-point containment requires dedicated tests.

## Required follow-up decisions

1. Ratify the registry's canonical path/storage and integrity mechanism.
2. Ratify how project UIDs are assigned and represented in external manifests.
3. Ratify the manifest key that binds the descriptor and digest.
4. Ratify administrator visibility for unhealthy contributions.
5. Ratify whether portable installations use a portable registry or an explicitly selected, session-scoped registry.

## Compliance evidence required

- Forged, duplicate, missing, moved, and tampered project fixtures are rejected.
- Directory enumeration alone cannot produce a writable application tab.
- All document and schema paths pass root-containment and link/reparse-point checks.
- Registry upgrade and unregistration preserve audit evidence.
- Deterministic ordering uses stable metadata, not filesystem order.

## Approval record

- [ ] Approved as written
- [ ] Approved with conditions recorded below
- [ ] Returned for revision
- [ ] Rejected

**Conditions / rationale:**

> 

**George:** ____________________  **Date:** __________  
**Ringo acceptance:** ____________________  **Date:** __________
