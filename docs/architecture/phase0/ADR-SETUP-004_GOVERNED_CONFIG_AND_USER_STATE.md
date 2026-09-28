# ADR-SETUP-004: Governed Configuration and User-State Separation

**Status:** Proposed  
**Date:** 2026-08-26  
**Decision owner:** George, Lead Architect  
**Implementation owner:** Paul, Lead Developer / Lead Analyst  
**Product acceptance:** Ringo  
**Consulted:** John, Lead Developer  
**Depends on:** ADR-SETUP-001

## Context

BFT previously used `bundle_config.json` for both shipped policy/defaults and mutable convenience values. The ratified R-BFT-01 design separated those roles:

- `bundle_config.json` is a hash-verified delivery payload and read-only at runtime;
- `UserStateStore` owns per-user remembered folders and window state.

The current shipped JSON still contains legacy convenience-shaped keys under `global_settings` and `session`, while the running application uses `UserStateStore`. A central setup UI could accidentally reactivate those legacy keys, create two sources of truth, or present per-user behavior as governed suite policy.

## Decision

Maintain a strict classification boundary between governed delivery configuration and mutable user state.

### Governed delivery configuration

Includes settings whose change affects application policy, safety, shipped defaults, or controlled behavior. It is:

- stored in an application-owned governed document;
- verified by manifest-bound integrity metadata;
- editable only through a `pyprojectmgr` governed transaction;
- subject to authorization, postflight, audit, and restart/reload semantics;
- read-only to the application runtime.

For BFT, `bundle_config.json` remains in this class.

### User state

Includes remembered dialog folders, window geometry, panel state, and similar current-user convenience. It is:

- stored outside the governed delivery document through `UserStateStore`;
- writable under the current user without changing governed config or manifest digests;
- resettable independently;
- not promoted into suite policy by ConfigEditor.

### Runtime overrides and effective values

Command-line arguments, environment variables, and operation-specific selections are neither governed defaults nor user-state writes unless an application contract explicitly says so. ConfigEditor may display their source/effective value but cannot persist them through the wrong layer.

## BFT field disposition

| Current area/key | Class | Phase 0 disposition |
|---|---|---|
| `version`, `schema_version` | governed/derived release metadata | Visible read-only; changed only by release/migration process |
| `global_settings.input_dir` | governed default, subject to product confirmation | Do not confuse with last-open directory |
| `global_settings.output_dir` | governed default, subject to product confirmation | Do not confuse with last-save directory |
| `global_settings.log_dir` | governed delivery setting | Orchestrated change; path policy applies |
| `global_settings.relative_base_path` | governed operational default | Orchestrated change; validate containment/semantics |
| `global_settings.last_source_dir` | legacy user-state seed | Hidden/deprecated; no active binding in Setup |
| `global_settings.last_bundle_save_dir` | legacy user-state seed | Hidden/deprecated; no active binding in Setup |
| `session.first_launch` | legacy user-state seed | Hidden/deprecated |
| `session.window_geometry` | legacy user-state seed | Hidden/deprecated; active value belongs to `UserStateStore` |
| `app_defaults.*` | governed defaults | Editable through orchestrated transaction |
| `safety.*` | elevated governed policy | Explicit impact review and elevated approval |
| `ui.layout`, `ui.bundle_mode`, panel defaults | governed application defaults unless reclassified | Show as defaults; do not overwrite current-user state silently |
| `ui.progress.*` | governed presentation/operation defaults | Orchestrated; activation semantics declared |
| `UserStateStore.last_source_dir` | user preference | User-state service only |
| `UserStateStore.last_bundle_save_dir` | user preference | User-state service only |
| `UserStateStore.window_geometry` | user preference | User-state service only |

Final classification of input/output defaults and UI defaults requires product confirmation, but no unresolved field may be writable through both layers.

## Migration rule for legacy keys

1. Do not remove legacy keys as part of manifest reconciliation.
2. Mark them deprecated and omit them from the ordinary governed editing surface.
3. Continue one-time seeding only as currently ratified and tested.
4. Define a later versioned BFT config migration that removes the keys after every supported runtime no longer depends on them for seeding.
5. The migration must preserve existing `UserStateStore` values, display its diff, and be applied through `pyprojectmgr`.

## ConfigEditor presentation

- Governed policy and user preferences use distinct headings, badges, explanations, and Apply/reset actions.
- A governed diff never includes user-state changes.
- A user-state reset never changes `bundle_config.json` or its digest.
- "My Preferences" should initially provide safe operations such as resetting remembered folders or window state; it should not expose the legacy governed keys.
- The UI shows whether a value is a shipped default, current user preference, operation override, or effective value.

## Alternatives considered

### Put all settings back in `bundle_config.json`

Rejected. It reintroduces runtime mutation of a governed payload, machine-specific drift, installer conflicts, and integrity failures.

### Move all UI/default settings to user state

Rejected. Some defaults are deliberately governed and must be consistent across installations or controlled environments.

### Mirror every user preference into both documents

Rejected. Mirroring creates two sources of truth and ambiguous conflict resolution.

### Hide the distinction in one seamless Apply operation

Rejected. The user must understand that policy and preference changes have different authority, scope, audit, and activation behavior. A shared review screen may summarize both only if it preserves separate commit paths and results.

## Consequences

### Positive

- Remembered folders and suggested bundle naming remain responsive and user-specific.
- Governed delivery integrity remains stable during ordinary use.
- Setup accurately communicates scope and authority.
- Portable and multi-user installations avoid machine-specific policy drift.

### Costs and constraints

- Every field requires classification and source/effective-value handling.
- Legacy keys require a managed deprecation period.
- UI defaults may need a product decision on whether they are organizational defaults or personal preferences.
- Testing must cover both layers and prove they do not cross-write.

## Compliance evidence required

- `ConfigManager.save()` continues to raise `ReadOnlyConfigError`.
- Remembered open and bundle-save folders persist through `UserStateStore`.
- Suggested bundle names remain computed/provided independently of governed writes.
- Resetting user preferences leaves the `bundle_config.json` SHA-256 unchanged.
- Editing governed defaults leaves existing user preferences unchanged.
- Legacy keys are not bound to active preference controls.

## Approval record

- [ ] Approved as written
- [ ] Approved with conditions recorded below
- [ ] Returned for revision
- [ ] Rejected

**Product classification conditions:**

> 

**George:** ____________________  **Date:** __________  
**Ringo acceptance:** ____________________  **Date:** __________
