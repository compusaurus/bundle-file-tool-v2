# ConfigEditor Central Setup Architecture

**Date:** 2026-08-26  
**Status:** Architecture candidate for George's ratification  
**Prepared by:** Paul, implementation lead / lead analyst  
**Directive source:** George's Architecture and Setup Governance brief, relayed by Ringo

## 1. Executive disposition

George's direction is accepted as the correct suite-level architecture, subject to the ownership and transaction boundaries in this document.

ConfigEditor should become the common setup **presentation and editing surface**. It should not become an unrestricted writer or a monolithic store for every application's configuration. Each application continues to own its settings semantics and files. `pyprojectmgr` becomes the central **orchestrator and governance authority** that discovers those application contributions, verifies them, stages and validates changes, performs governed writes, synchronizes integrity metadata, and emits an audit result.

The existing ConfigEdit project is a useful basis for controls, generated forms, and Tk/web presentation. It is not safe to adopt unchanged. Its current model presents a flat list of tabs for one JSON document and its `ConfigModel.save()` writes directly to the target file. That conflicts with BFT's ratified runtime contract, under which governed `bundle_config.json` is read-only and `ConfigManager.save()` always raises `ReadOnlyConfigError`.

**Readiness conclusion:** the suite is architecture-ready but not yet implementation-ready for governed editing. Contract ratification and the Phase 0 reconciliation gates in the implementation plan must occur first.

## 2. Objective

Provide one clean, predictable, modular setup experience in which:

- top-level tabs represent registered applications, not hard-coded application names;
- sub-tabs represent application-owned configuration sections;
- applications supply versioned schemas, navigation metadata, validation, migration, and apply semantics;
- ConfigEditor supplies a consistent, accessible editor and change-review experience;
- `pyprojectmgr` controls discovery, authorization, validation, mutation, recovery, manifest compliance, and audit;
- governed settings, user preferences, runtime overrides, and secrets remain visibly and technically distinct.

## 3. Architectural principles

### 3.1 One hub, distributed ownership

"Central configuration hub" means a common user experience and a common governance workflow. It does **not** mean one central JSON file, one giant schema, or ConfigEditor owning every application's rules.

Each application remains the authority for:

- setting identifiers and meanings;
- default values and permitted ranges;
- cross-field validation;
- migration between schema versions;
- restart/reload requirements;
- which values are governed, user-local, secret, derived, or read-only.

### 3.2 Stable IDs, presentation labels

Application, document, section, and field IDs are durable contract identifiers. Labels such as "Bundle File Tool" are presentation text and may change without changing identity. Navigation order must come from contribution metadata, never from filesystem enumeration or labels.

### 3.3 Staged editing, governed commit

ConfigEditor edits an in-memory working copy. It may perform fast local validation and render a diff, but it may not directly save a governed document. `pyprojectmgr` is the sole governed mutation authority.

### 3.4 Fail closed

If the application contribution is invalid, the baseline is stale, the manifest is unhealthy, an authorization check fails, or `pyprojectmgr` is unavailable, ConfigEditor remains read-only for governed values. No partial or best-effort governed write is permitted.

### 3.5 Separate policy from convenience

Governed delivery configuration and mutable per-user state have different lifecycles. They must use separate documents, labels, validation policies, write authorities, and audit rules.

For BFT, `bundle_config.json` remains governed and read-only at runtime. Remembered folders and window state remain in `UserStateStore`. Legacy convenience keys still present in `bundle_config.json` should be deprecated and hidden from normal setup rather than becoming a second mutable source.

## 4. Logical component model

| Component | Primary responsibility | Explicit non-responsibility |
|---|---|---|
| Application project | Own settings semantics, schema, defaults, validation/migration hooks, and setup contribution descriptor | Does not build a separate suite settings UI or bypass orchestration |
| ConfigEditor core | Create setup sessions, build nested navigation, preserve typed working values, track dirty state, validate locally, and produce reviewable diffs | Does not write governed files, update manifests, or invent application semantics |
| ConfigEditor Tk/web shells | Render application tabs, section sub-tabs, fields, diagnostics, review, approval prompts, and results | Do not contain application-specific hard-coded tabs or mutation logic |
| `pyprojectmgr` setup registry | Discover registered projects and authenticate compatible setup contributions | Does not infer a writable settings surface from arbitrary JSON |
| `pyprojectmgr` transaction service | Lock, baseline, validate, authorize, journal, commit, recover, synchronize digests, postflight, and audit | Does not delegate governed writes to ConfigEditor |
| Installer/release process | Install initial governed payloads, descriptors, schemas, permissions, and registry entries | Does not leave production policy writable by ordinary runtime code |
| Application runtime | Consume verified governed settings and independent user state | Does not mutate governed delivery configuration |

## 5. Navigation hierarchy

The target UI contains two contract-driven levels:

1. **Application tabs** — one top-level tab for each installed, authenticated, compatible application contribution.
2. **Section sub-tabs** — application-owned groupings within the selected application.

Recommended initial shape:

| Application | Candidate sub-tabs | Notes |
|---|---|---|
| Bundle File Tool | General, Bundle Defaults, Extraction, Safety, Interface, Progress, My Preferences | `My Preferences` is a visibly separate user-state class; safety changes require stronger approval |
| ThermX | Appearance, Layout, Progress Semantics, Cancel Control, Performance | ThermX presently exposes a Python style/config vocabulary; it needs a project-owned persisted profile and schema before registration |
| SplashX | Profile, Media, Window & Geometry, Mask, Playback, Logging | Edit the profile document only; retain runtime precedence of explicit arguments, environment variables, profile, then failsafe defaults |

These names are candidate labels, not ratified IDs. Applications must publish the final IDs and labels through their descriptors.

The UI must also provide:

- classification badges such as **Governed**, **User preference**, **Read-only**, and **Restart required**;
- per-field help, source, effective value, and validation feedback;
- dirty-state indication at application and section level;
- a review screen showing path-level before/after changes;
- clear distinction between staged, validated, applied, recovered, and rejected states;
- keyboard navigation, active scrollbars where content can overflow, and usable focus order.

## 6. End-to-end orchestration

### 6.1 Open session

1. ConfigEditor asks `pyprojectmgr` for the authenticated application registry.
2. `pyprojectmgr` resolves each project root from the governed registry and verifies manifest, descriptor, schema, supported contract version, and path containment.
3. `pyprojectmgr` acquires a scoped setup-session lock and loads each permitted document.
4. It records baseline SHA-256 digests and returns a read-only session snapshot plus presentation metadata.
5. ConfigEditor constructs top-level and sub-tab navigation from that snapshot.

### 6.2 Edit and review

1. ConfigEditor updates only its working copy.
2. Typed controls preserve JSON/TOML types; no silent stringification or coercion is allowed.
3. Local schema checks provide immediate feedback.
4. The application validator checks cross-field and domain rules.
5. ConfigEditor displays a redacted path-level diff, impact level, approval requirement, and reload/restart behavior.

### 6.3 Validate and apply

1. ConfigEditor submits the session ID, baseline digests, proposed patch, and approval evidence to `pyprojectmgr`.
2. `pyprojectmgr` verifies the lock, authorization, descriptor version, baseline digests, and target paths.
3. It applies the proposal to an isolated staging mirror.
4. It validates document schemas, application rules, architectural rules, and manifest compliance against the staged result.
5. Preview/staging governance runs with automatic remediation disabled. Validation must not silently change the proposal.
6. If all gates pass, `pyprojectmgr` creates a recovery journal and durable backups, writes temporary siblings, commits the affected configuration and integrity metadata, and performs strict postflight validation.
7. It restores required write protections and emits an audit receipt with redacted change metadata and before/after digests.
8. If any commit or postflight step fails, it executes deterministic recovery and reports whether baseline restoration was verified.

### 6.4 Reload or restart

Application metadata declares whether a change is:

- immediately reloadable;
- reloadable only at an application-defined safe point;
- effective on next launch;
- installation/redeployment scoped.

ConfigEditor must never imply that a committed value is active when the application has not reloaded it.

## 7. Governance boundary

### 7.1 Required invariants

- No governed document is written through `ConfigModel.save()` or application runtime code.
- `pyprojectmgr` is the only component that updates governed configuration and the corresponding manifest digest.
- Every target path is declared, normalized, contained inside its authenticated project root, and checked against link/reparse-point escape.
- Every apply request includes baseline digests; stale baselines fail rather than overwrite another editor's work.
- All affected files participate in one recoverable transaction journal.
- Preview and validation never invoke `auto_heal` or otherwise mutate the source project.
- Hook implementations are resolved from allowlisted, governed application packages; descriptors may not contain arbitrary shell commands.
- Secrets are referenced through a secret provider or credential handle and are redacted from snapshots, diffs, logs, backups, and receipts.
- Locked and derived fields are visible when useful but cannot be submitted as writable patches.
- Unknown fields are preserved unless the application migration contract explicitly removes them.
- A failed postflight is a failed transaction, not a warning-only success.

### 7.2 Transaction reality

Replacing one temporary file atomically does not make a multi-file update atomic. A governed change may affect the application config, manifest digest, registry metadata, or generated evidence. The service therefore needs a journaled transaction with recovery markers and verified rollback. This is a core requirement, not an implementation enhancement.

## 8. Current-code assessment

### 8.1 ConfigEdit

Reusable foundation:

- data-driven form generation;
- Tk notebook and scrollable field concepts;
- controller/model separation;
- validation-policy abstraction;
- atomic replacement for a single file as a low-level primitive.

Required redesign:

- flat `LayoutDefinition.tabs` becomes an application-and-section hierarchy;
- one-target `ConfigModel` becomes a session with multiple classified documents;
- direct `save()` is removed from the governed path and replaced by proposal submission;
- manifest-specific hard-coded validation becomes descriptor/schema/application validation;
- CWD-relative settings and target discovery become registry-derived absolute identities;
- shallow mocked GUI tests are supplemented by real widget/integration tests;
- core/Tk release and lifecycle metadata are reconciled.

### 8.2 pyprojectmgr

Existing useful capability:

- external-project manifest validation through `project_root`;
- strict governance preflight and schema synchronization checks;
- a natural position as the suite's architecture authority.

Missing capability:

- authenticated setup contribution registry;
- contract-version negotiation;
- setup-session and lock service;
- patch/diff validation API;
- staged no-mutation preflight;
- multi-file journaled transaction and recovery service;
- authorization/approval policy;
- audit receipt and redaction contract.

Existing auto-heal behavior must be disabled during preview and staging. Remediation belongs to an explicit, separately authorized maintenance action.

### 8.3 Bundle File Tool

Aligned foundation:

- governed `bundle_config.json` is verified and read-only at runtime;
- mutable convenience data already has a separate `UserStateStore`;
- the application therefore demonstrates the intended policy/user-state split.

Blocking gaps:

- the Settings command is still a placeholder and tells the user to edit `bundle_config.json` directly;
- no machine-readable settings schema or setup contribution descriptor exists;
- legacy convenience keys remain in the governed file;
- `.pyprojectmgr/project_spec.json` and `.pyprojectmgr/project_manifest.json` disagree on entry points and infrastructure;
- the manifest has an empty `configuration_paths` list despite carrying a governed configuration digest.

The Settings command should eventually launch or focus ConfigEditor through `pyprojectmgr`, scoped to BFT. It must not embed a second independent editor.

### 8.4 ThermX and SplashX

ThermX currently has a well-defined Python presentation/settings vocabulary and sanitizers but no clearly established project-owned persisted setup document discovered in this review. Its owner must decide whether setup edits a suite profile, consumer application profile, or library defaults. A shared library should not silently acquire global mutable settings.

SplashX has a profile key registry and an explicit resolution order: explicit argument, environment variable, `splash_profile.json`, then internal failsafe. Its contribution should edit only the declared profile layer and explain when a higher-precedence runtime value masks the configured value.

## 9. Architecture decisions requiring ratification

| Decision | Recommended disposition |
|---|---|
| Product/package name | Use **ConfigEditor** for the suite capability; decide whether the existing `ConfigEdit` package is renamed or retained as an implementation package |
| Governed mutation authority | `pyprojectmgr` only |
| Application discovery | Governed registry plus manifest pointer to a versioned contribution descriptor; no directory scanning as authority |
| Descriptor location | `.pyprojectmgr/setup_contribution.json` with a manifest-governed pointer/digest |
| Schema format | JSON Schema for JSON documents plus application validator for domain rules |
| User preferences | Separate documents and write policy; never merged into governed delivery configuration |
| Preview behavior | Strict and non-mutating; `auto_heal=False` |
| Concurrency | Scoped lock plus digest-based compare-and-swap |
| Failure recovery | Durable journal, backups, postflight, and verified rollback |
| Initial applications | BFT first as the reference integration; ThermX and SplashX after their persisted ownership contracts are settled |

## 10. Acceptance criteria for this architecture

The architecture is ratified when George and the team explicitly agree that:

1. ConfigEditor is the shared UI/session layer, not the governed writer.
2. `pyprojectmgr` is the sole governed orchestrator and mutation authority.
3. Applications publish versioned contributions rather than application-specific editor code.
4. Governed settings and per-user state remain separate.
5. No implementation begins on a write path until transaction, recovery, authorization, and audit contracts are approved.
6. BFT manifest/spec/configuration-path inconsistencies are corrected before BFT onboarding is declared compliant.

## 11. Conclusion

George's proposed hierarchy and central orchestration model should proceed. The safest delivery path is to reuse ConfigEdit's presentation ideas, establish a strict application contribution contract, and build the governed setup session and transaction capabilities in `pyprojectmgr` before connecting any Apply button. BFT should be the first reference application because its read-only governed configuration and separate user-state design make the ownership boundary explicit and testable.
