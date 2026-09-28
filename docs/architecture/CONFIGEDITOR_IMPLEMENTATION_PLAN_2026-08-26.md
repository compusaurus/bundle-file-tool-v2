# ConfigEditor Central Setup Implementation Plan

**Date:** 2026-08-26  
**Status:** Proposed gated delivery plan  
**Working leadership:** George — architecture authority; Paul — implementation lead; John — lead developer reviewer as availability permits; Ringo — product/governance acceptance

## 1. Delivery decision

Proceed with architecture and contract ratification immediately. Do **not** connect ConfigEditor to governed production writes until the `pyprojectmgr` transaction service, recovery behavior, and BFT manifest reconciliation gates have passed.

The recommended reference sequence is:

```text
Ratify -> Reconcile baselines -> Extract read-only editor engine
        -> Build pyprojectmgr registry/session/transaction services
        -> Integrate BFT -> Integrate ThermX/SplashX
        -> Harden, recover, package, and release
```

BFT should be the first end-to-end application. Its existing separation between read-only governed configuration and `UserStateStore` provides a strong test of the architecture.

## 2. Operating rules

- Work is contract-first. Any implementation difference requires an architecture decision record before it becomes de facto behavior.
- Each phase has an entry gate, deliverables, acceptance tests, and exit gate.
- UI development may run against fixtures before the transaction service is ready, but Apply remains disabled outside disposable test projects.
- No phase weakens BFT's `ConfigManager.save()` prohibition.
- Preview and staged validation use non-mutating governance checks.
- All adjacent-project changes occur in their owning repositories with their own tests and review; this plan does not authorize cross-repository edits from BFT.
- A successful unit test suite is necessary but not sufficient; real UI, concurrency, permission, failure-injection, and recovery tests are required.

## 3. Workstream ownership

| Workstream | Accountable | Responsible | Consulted | Acceptance |
|---|---|---|---|---|
| Architecture and exceptions | George | Paul | John, application owners | George |
| Contract/metaschema | George | Paul / `pyprojectmgr` owner | John, application owners | George + Ringo |
| ConfigEditor core and UI | Paul | ConfigEditor developers | John, accessibility reviewer | Paul + Ringo |
| `pyprojectmgr` registry and transactions | George | Paul / `pyprojectmgr` developers | John, security/governance reviewer | George |
| BFT contribution | Paul | BFT developers | John | Paul + Ringo |
| ThermX contribution | ThermX owner | ThermX developers | George, Paul | George |
| SplashX contribution | SplashX owner | SplashX developers | George, Paul | George |
| Release/evidence | Paul | project owners | John | Ringo |

Role assignments are working assumptions from the current team discussion and should be corrected during Phase 0 if responsibilities differ.

## 4. Phase 0 — Ratify and reconcile

### Entry gate

George's directive is accepted as a candidate architecture.

### Tasks

1. Ratify the ownership boundary: ConfigEditor stages; `pyprojectmgr` governs and writes; applications define semantics.
2. Decide the product/package naming relationship between **ConfigEditor** and the existing **ConfigEdit** project.
3. Ratify descriptor location, suite registry authority, contract versioning, approval classes, and audit integrity method.
4. Create architecture decision records for:
   - ADR-SETUP-001: component ownership;
   - ADR-SETUP-002: application contribution discovery and trust;
   - ADR-SETUP-003: transaction/recovery model;
   - ADR-SETUP-004: governed configuration versus user state;
   - ADR-SETUP-005: hook isolation and trust.
5. Reconcile BFT's `.pyprojectmgr/project_spec.json` and `.pyprojectmgr/project_manifest.json`:
   - entry points;
   - infrastructure paths;
   - governed configuration paths;
   - manifest/config digest relationship.
6. Reconcile ConfigEdit core/Tk version and lifecycle metadata and identify its canonical manifest.
7. Decide persisted configuration ownership for ThermX and governed/profile classification for SplashX.

### Deliverables

- ratified ADR set;
- setup contract `1.0-rc1` and JSON metaschema;
- reconciled project governance baselines;
- signed-off ownership/RACI;
- initial threat model and data-classification table.

### Exit gate

- No unresolved blocker in the ownership, trust, or transaction model.
- BFT manifest and project specification validate as one consistent baseline.
- George approves contract `1.0-rc1` for prototype implementation.

## 5. Phase 1 — ConfigEditor read-only engine

### Entry gate

Contract `1.0-rc1` and representative fixture contributions exist.

### Tasks

1. Extract reusable ConfigEdit model/control code from manifest-specific behavior.
2. Replace flat `LayoutDefinition.tabs` with:
   - application collection;
   - application view model;
   - section collection;
   - typed field view models;
   - document/source classification.
3. Introduce an immutable baseline plus mutable working-copy session.
4. Use RFC 6901 pointers and typed patch generation.
5. Add dirty-state tracking and redacted path-level diff.
6. Add local JSON Schema validation and structured diagnostics.
7. Remove direct governed-save calls from controllers and views. Preserve any single-file save primitive only behind a non-governed/test adapter.
8. Add locked, derived, secret-reference, effective-source, and restart badges.
9. Build top-level application tabs and section sub-tabs in Tk and the web view from fixture descriptors.
10. Implement active scrolling, keyboard focus, overflow behavior, and accessible labels in real widgets.

### Tests

- descriptor-to-navigation determinism;
- type and unknown-field preservation;
- dirty tracking and patch generation;
- redaction;
- invalid/unsupported contribution read-only diagnostics;
- real Tk nested-tab and scrollbar integration tests;
- equivalent web navigation tests;
- no filesystem mutation in read-only/editor tests.

### Exit gate

ConfigEditor can open, edit, validate locally, and review fixture proposals for three applications without possessing a production governed write path.

## 6. Phase 2 — pyprojectmgr setup registry and session service

### Entry gate

ConfigEditor consumes the `1.0-rc1` fixture contract without application-specific code.

### Tasks

1. Publish the contribution metaschema and contract compatibility resolver.
2. Implement an authenticated suite application registry.
3. Verify project UID, manifest pointer/digest, descriptor, schemas, and allowed hook package.
4. Enforce project-root path containment, including symlink/reparse-point escape checks.
5. Implement read-only discovery and health diagnostics.
6. Add scoped session identities, expiry, actor context, locks, and baseline SHA-256 digests.
7. Expose an in-process service interface first; keep semantics transport-independent.
8. Return classified document snapshots, navigation, validation policy, and effective-source metadata.
9. Define read-only behavior for unavailable, incompatible, or unhealthy projects.

### Tests

- forged, duplicate, and mismatched identity rejection;
- descriptor/schema digest mismatch rejection;
- unsupported contract major version;
- deterministic ordering;
- target path and reparse-point escape attempts;
- session expiry and lock release;
- unavailable project and corrupt document diagnostics;
- absence of writes during discovery/open.

### Exit gate

ConfigEditor opens real authenticated application sessions through `pyprojectmgr`; governed fields remain read-only pending Phase 3.

## 7. Phase 3 — pyprojectmgr validation and transaction service

### Entry gate

Registry/session service passes security and containment tests.

### Tasks

1. Implement bounded patch submission and patch-policy validation.
2. Resolve allowlisted application validators/migrators without arbitrary code or command execution.
3. Build an isolated staging mirror.
4. Execute schema, application, architecture, and manifest validation on the staged result.
5. Ensure governance preview uses `auto_heal=False` and produces no source mutation.
6. Implement authorization and approval policy, including elevated safety changes.
7. Implement compare-and-swap baseline checking immediately before commit.
8. Design and implement a durable multi-file journal:
   - transaction plan;
   - durable backups;
   - temporary siblings;
   - ordered commit markers;
   - digest verification;
   - startup recovery.
9. Synchronize governed configuration and manifest integrity metadata within the recovery plan.
10. Run strict postflight and restore write protections.
11. Produce redacted integrity-protected audit receipts.

### Failure-injection matrix

Inject termination or failure:

- before journal durability;
- after backup creation;
- after each temporary file is flushed;
- after config replacement but before manifest replacement;
- after manifest replacement but before postflight;
- during postflight;
- during rollback/recovery;
- before receipt completion.

Each case must end in a provably valid baseline or a fail-closed `failed_recovery` state that prevents further editing until maintenance resolves it.

### Exit gate

The service demonstrates stale-write prevention, zero writes on failed validation, verified recovery at every journal step, synchronized digests, strict postflight, and complete redacted receipts.

## 8. Phase 4 — BFT reference integration

### Entry gate

Phases 0-3 pass and BFT governance metadata is consistent.

### Tasks

1. Create a BFT JSON Schema matching the ratified `ConfigManager` validation rules and actual file shape.
2. Publish BFT's setup contribution descriptor.
3. Define final section IDs and labels. Candidate grouping:
   - General;
   - Bundle Defaults;
   - Extraction;
   - Safety;
   - Interface;
   - Progress;
   - My Preferences.
4. Classify every BFT field:
   - governed delivery;
   - user preference;
   - read-only/derived;
   - deprecated;
   - elevated safety.
5. Deprecate legacy governed convenience keys through an explicit migration. Do not create a second active state source.
6. Implement the BFT application validator and postflight adapter as pure validation/verification hooks.
7. Add a safe BFT-scoped launch/focus route from the Settings command to ConfigEditor through `pyprojectmgr`.
8. Replace the current instruction to edit `bundle_config.json` manually.
9. Add user-preference actions, especially reset remembered open/save folders, through `UserStateStore` rather than the governed transaction.
10. Define and display activation semantics for each governed setting.

### Regression guarantees

- BFT `ConfigManager.save()` still raises `ReadOnlyConfigError`.
- Existing remembered-folder, suggested-name, and window-state behavior remains under `UserStateStore`.
- A user-preference change does not alter the governed config digest.
- Safety changes require elevated review.
- Manual or stale external changes are detected, not overwritten.
- Existing BFT functional and UI regression suites remain green.

### Exit gate

A BFT setting can be staged, reviewed, authorized, committed, digest-synchronized, postflight-verified, and audited end-to-end. Per-user preferences remain independent and functional.

## 9. Phase 5 — ThermX and SplashX contributions

### ThermX tasks

1. Decide whether persisted ThermX settings belong to a suite profile or each consuming application.
2. If a suite profile is approved, define its schema from the existing style/config vocabulary and sanitizers.
3. Preserve consumer explicit values; no suite setting may unexpectedly override constructor arguments.
4. Define sections such as Appearance, Layout, Progress Semantics, Cancel Control, and Performance.
5. Test all construction-time validation, consumer override, and reload limitations.

### SplashX tasks

1. Publish a schema and contribution for the governed/approved `splash_profile.json` layer.
2. Define sections such as Profile, Media, Window & Geometry, Mask, Playback, and Logging.
3. Preserve and display resolution precedence: explicit argument, environment variable, profile, failsafe.
4. Show when a configured profile value is masked by a higher-precedence source.
5. Validate media paths, geometry, logging paths, and platform-specific constraints without launching untrusted media during preview.

### Exit gate

Both applications appear through their own descriptors with no hard-coded ConfigEditor application logic, and their documented precedence/ownership rules are preserved.

## 10. Phase 6 — Hardening and release

### Tasks

1. Complete accessibility, localization readiness, keyboard, focus, scaling, and overflow review.
2. Run permission tests as ordinary user, administrator, portable install, and read-only install.
3. Test concurrent ConfigEditor processes and application-running scenarios.
4. Complete secret/redaction and backup-retention review.
5. Test corrupt registry, manifest, descriptor, schema, config, journal, and receipt cases.
6. Package ConfigEditor, `pyprojectmgr` service components, schemas, descriptors, and registry initialization.
7. Add install/upgrade/uninstall/recovery runbooks.
8. Produce traceability from George's brief through ADRs, contracts, tests, and release evidence.
9. Run a controlled pilot with BFT before enabling ThermX/SplashX writes.

### Release gate

- Architecture authority approves all governance evidence.
- Product acceptance confirms navigation and terminology.
- No open blocker/critical defects.
- Recovery drill succeeds from documented operational instructions.
- Audit receipts and diagnostic exports are supportable without exposing secrets.
- Rollback to the previous suite release is documented and rehearsed.

## 11. Proposed implementation increments

| Increment | Demonstrable outcome | Production write enabled? |
|---|---|---|
| I0 | Ratified contracts and reconciled BFT governance baseline | No |
| I1 | Nested ConfigEditor UI using fixtures, with local validation/diff | No |
| I2 | Authenticated real-project discovery and read-only sessions | No |
| I3 | Disposable-project journaled transaction and crash recovery | Test projects only |
| I4 | BFT governed end-to-end pilot plus independent user preferences | Controlled pilot |
| I5 | ThermX/SplashX contributions | After individual gates |
| I6 | Hardened suite release | Yes |

## 12. Definition of done

The project is complete only when:

1. Installed authenticated applications contribute their own application tab and sub-tabs through the ratified contract.
2. ConfigEditor contains no BFT/ThermX/SplashX-specific write logic.
3. `pyprojectmgr` enforces manifest/schema/application validation and is the sole governed writer.
4. Transactions resist stale sessions and recover from interruption without leaving config and integrity metadata divergent.
5. Users can understand source, classification, impact, validation, and activation of every displayed setting.
6. BFT's governed/user-state separation and remembered-folder behavior remain correct.
7. ThermX and SplashX precedence/ownership rules remain correct.
8. Evidence traces every governing requirement to tests and release artifacts.

## 13. Immediate next actions

1. George reviews the architecture decisions and seven ratification questions in the contracts document.
2. Paul prepares the Phase 0 ADR skeletons and BFT governance reconciliation proposal.
3. The `pyprojectmgr` owner identifies the canonical registry, manifest schema extension point, and approval mechanism.
4. The ConfigEditor owner freezes direct governed-save expansion and prepares a read-only nested-layout spike.
5. ThermX and SplashX owners answer the persisted ownership questions before UI fields are designed.

This sequencing permits useful UI and contract progress immediately while preventing an attractive prototype from creating an unsafe production write path.
