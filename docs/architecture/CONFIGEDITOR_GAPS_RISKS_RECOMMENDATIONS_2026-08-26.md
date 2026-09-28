# ConfigEditor Setup Governance — Gaps, Risks, and Recommendations

**Date:** 2026-08-26  
**Assessment status:** Current-code review and forward risk analysis  
**Decision headline:** Proceed with contract and foundation work; block governed production editing until the critical gaps below are closed.

## 1. Overall assessment

George's central ConfigEditor/`pyprojectmgr` model aligns well with the suite's need for predictable setup and architectural oversight. The existing projects contain useful pieces, but no current component supplies the complete governed workflow:

- ConfigEdit has a useful generated editor concept but is single-document, flat-tab, and directly writes its target.
- `pyprojectmgr` has external-project manifest validation and governance preflight but no setup registry, editing session, transaction, recovery, approval, or audit service.
- BFT has the strongest configuration ownership boundary—governed runtime config is read-only and per-user convenience state is separate—but lacks a setup descriptor/schema and contains governance metadata inconsistencies.
- ThermX and SplashX have settings/profile vocabularies, but their persisted ownership and governance classifications are not yet consistent enough for automatic registration.

This is not a reason to reject the initiative. It establishes the correct dependency order: contracts and governance first, presentation integration second, production Apply last.

## 2. Severity model

| Severity | Meaning |
|---|---|
| Blocker | Governed production editing must not be enabled until resolved |
| Critical | High probability or impact to integrity, security, or recoverability |
| Major | Material correctness, maintainability, usability, or rollout risk |
| Moderate | Important quality/operational concern that can follow the core gate |

## 3. Cross-suite gaps and risks

| ID | Severity | Gap or risk | Consequence | Required disposition |
|---|---|---|---|---|
| SETUP-G01 | Blocker | Mutation authority is not implemented | Direct ConfigEditor writes would bypass architecture and manifest governance | Implement `pyprojectmgr` as the sole governed transaction authority |
| SETUP-G02 | Blocker | No recoverable multi-file transaction | Config and manifest digest can diverge after interruption | Durable journal, backup, ordered commit, startup recovery, strict postflight |
| SETUP-G03 | Blocker | No ratified application contribution contract | UI becomes hard-coded and application semantics drift | Ratify descriptor/metaschema, version negotiation, and ownership rules |
| SETUP-G04 | Blocker | No authenticated application registry | Forged or accidental directories could become trusted setup targets | Governed registry plus manifest-bound descriptor/schema digests |
| SETUP-G05 | Critical | No stale-baseline protection | Two editors or external maintenance can silently overwrite changes | Scoped lock plus digest compare-and-swap immediately before commit |
| SETUP-G06 | Critical | Existing preflight can auto-heal | Preview could mutate the source project without explicit approval | Force non-mutating validation for preview/staging; separate authorized maintenance |
| SETUP-G07 | Critical | Hook trust/isolation is undefined | A descriptor could introduce arbitrary code execution | Allowlisted governed import references; no commands; define process/isolation policy |
| SETUP-G08 | Critical | Authorization and approval classes are undefined | Safety/deployment changes may be made by an ordinary user | Ratify actor identity, elevated approvals, timeout, evidence, and denial behavior |
| SETUP-G09 | Critical | Secret handling contract is absent | Secrets may leak through UI snapshots, diffs, backups, logs, or receipts | Use secret references/providers and mandatory redaction tests |
| SETUP-G10 | Major | "Central hub" could become a monolithic config store | Coupling, migration collisions, unclear ownership, suite-wide blast radius | Centralize orchestration/UI, not application data ownership |
| SETUP-G11 | Major | Contract/version compatibility is undefined | Tool upgrades may misrender or corrupt newer schemas | Independent semantic versions for contribution contract and document schema |
| SETUP-G12 | Major | No effective-value/source model | Users may edit a value masked by env/CLI and believe it is active | Display configured value, effective value, source, and activation requirement |
| SETUP-G13 | Major | Write protection/installer behavior is undefined | Development succeeds but installed builds cannot write safely or restore protection | Test ordinary-user, admin, portable, read-only, upgrade, and uninstall cases |
| SETUP-G14 | Major | Audit evidence has no integrity standard | Receipts cannot reliably support governance or incident review | Ratify signing or chained-hash approach, retention, export, and redaction |
| SETUP-G15 | Major | UI accessibility/overflow is not a contract gate | Generated forms can repeat inactive scrolling and focus defects | Real Tk/web tests for nested tabs, overflow, keyboard, scaling, and scrollbars |
| SETUP-G16 | Moderate | Naming differs between ConfigEdit and ConfigEditor | Packaging, process, documentation, and support ambiguity | Ratify capability name and implementation package/rename strategy |

## 4. ConfigEdit-specific findings

### CE-G01 — Flat navigation model (Major)

The current layout exposes one `tabs` list for the keys of one target document. George's hierarchy requires application tabs containing application section tabs. Simply wrapping the existing notebook in another notebook would create a visual hierarchy without establishing document classification, application identity, or governed sessions.

**Recommendation:** replace the layout contract with explicit application, section, field, and document-source models. Keep labels separate from stable IDs.

### CE-G02 — Direct save bypass (Blocker)

`ConfigModel.save()` validates and directly replaces its target file. Single-file temporary replacement is a useful low-level operation, but it cannot update governed configuration and manifest integrity metadata as one recoverable action. It also conflicts directly with BFT's read-only configuration contract.

**Recommendation:** remove direct save from the governed controller flow. ConfigEditor should generate a bounded proposal for the `pyprojectmgr` transaction service.

### CE-G03 — Single-document/CWD coupling (Major)

The editor is initialized from relative settings/target paths and one JSON file. A suite hub needs authenticated project identities, multiple classified documents, non-project user-state locations, and deterministic source information.

**Recommendation:** accept only session snapshots created by `pyprojectmgr`; do not let the UI choose arbitrary governed paths.

### CE-G04 — Hard-coded manifest validation (Major)

The existing validation policy looks for selected manifest roots rather than validating arbitrary application settings through a document schema and application rules.

**Recommendation:** implement generic schema diagnostics plus allowlisted application validation hooks. Keep `pyprojectmgr` manifest validation as a separate authoritative gate.

### CE-G05 — Type/edit fidelity (Critical)

Generic generated forms risk converting booleans, numbers, nulls, arrays, and objects through strings. Unknown properties may also be lost if the working model is rebuilt only from displayed fields.

**Recommendation:** preserve the complete original document, use typed field adapters, express edits as pointers/patches, and test round trips including unknown fields.

### CE-G06 — Test realism (Major)

Current GUI tests rely heavily on mocked Tk behavior. That cannot prove real nested notebooks, focus traversal, scrolling, resizing, event binding, or platform-specific widget behavior.

**Recommendation:** retain fast unit tests and add real Tk integration tests plus web browser tests for the rendered interaction contract.

### CE-G07 — Version/lifecycle inconsistency (Moderate)

Core and Tk headers report different versions/lifecycle states, and the current manifest appears oriented to an older `pyprojectmgr` governance console use case.

**Recommendation:** identify one canonical release identity and manifest before extracting reusable components.

## 5. pyprojectmgr-specific findings

### PPM-G01 — Validation is present; orchestration is incomplete (Blocker)

`GovernancePreflight.validate_manifest(project_root=...)` and `run_sequence(...)` provide a useful external-project validation base. They do not provide authenticated discovery, setup locks, proposal validation, authorization, a journaled commit, rollback, or an audit receipt.

**Recommendation:** build a dedicated setup domain service instead of expanding UI routes into ad hoc file operations.

### PPM-G02 — Auto-heal side effects (Critical)

`run_sequence` defaults `auto_heal=True` and may invoke manifest remediation. That behavior is reasonable for an explicitly authorized maintenance workflow but unsafe for preview, opening a setup screen, or validating a staged change.

**Recommendation:** expose a guaranteed read-only validation operation and make setup preview call it explicitly. Do not depend solely on a caller remembering a default.

### PPM-G03 — Registry authority unclear (Blocker)

There is no identified canonical suite registry tying an installed application/project UID to its manifest and setup descriptor.

**Recommendation:** choose a governed registry with controlled registration/unregistration, duplicate detection, install/upgrade semantics, and diagnostics for missing projects.

### PPM-G04 — Transaction boundary unclear (Blocker)

The precise set of files changed with application configuration—including manifest digests and evidence—is not declared as a transaction plan.

**Recommendation:** make the plan explicit before validation; journal every target and expected digest; recover on service startup before accepting new sessions.

### PPM-G05 — Transport and privilege boundary (Major)

It is undecided whether ConfigEditor calls an in-process library, local service, CLI, or web endpoint and where elevated privilege occurs.

**Recommendation:** ratify transport-independent service semantics first. Start in-process for testability if suitable, but keep authorization and mutation out of UI classes and define a future privilege boundary.

## 6. BFT-specific findings

### BFT-G01 — Settings command contradicts governance (Major)

The current Settings action is a placeholder that tells users to edit `bundle_config.json` directly. This instruction conflicts with BFT's enforced read-only runtime configuration.

**Recommendation:** as an immediate low-risk correction, replace the manual-edit advice with a governed-setup-unavailable message. After the service exists, launch/focus ConfigEditor through `pyprojectmgr`, scoped to BFT.

### BFT-G02 — Manifest/spec divergence (Blocker for onboarding)

The project specification declares entry points that the project manifest omits, infrastructure lists differ, and `configuration_paths` is empty even though the manifest carries a governed configuration digest.

**Recommendation:** reconcile through the canonical `pyprojectmgr` governance process and verify the resulting digest before publishing a BFT contribution.

### BFT-G03 — No machine-readable setup schema (Blocker for onboarding)

BFT validation is implemented in Python, but ConfigEditor needs a schema to build correct controls and give immediate feedback. A schema alone will not cover every domain rule.

**Recommendation:** publish a JSON Schema generated/reviewed against `ConfigManager.validate()` and add a pure application validator for cross-field/domain constraints. Add conformance tests so code and schema cannot drift.

### BFT-G04 — Legacy convenience fields remain governed (Major)

`bundle_config.json` still contains remembered-directory/session-shaped fields while the application correctly uses `UserStateStore` for mutable convenience state.

**Recommendation:** mark legacy fields deprecated and non-presentational; remove them only through a versioned migration. Never bind them to the Setup UI as active preferences.

### BFT-G05 — Preference versus policy confusion (Major)

Putting "My Preferences" next to safety policy can imply equal governance and activation behavior.

**Recommendation:** use explicit classification badges and explanatory grouping. Preference operations should use `UserStateStore`; governed Apply should exclude them or clearly show a separate commit path.

### BFT-G06 — Safety settings are high impact (Critical)

Changing allow/deny patterns or size protections can alter what BFT includes, excludes, or processes.

**Recommendation:** require elevated review, preview impact where feasible, validate patterns with the exact runtime matcher, and retain an audit receipt.

## 7. ThermX-specific findings

### THERM-G01 — Persisted owner is undecided (Blocker for onboarding)

ThermX exposes a rich Python style and pump-setting vocabulary, but a shared library may not be the correct owner of one global mutable profile. Consumer applications may need to own their ThermX presentation settings.

**Recommendation:** George and the ThermX owner must choose one of:

1. application-owned ThermX sections contributed by each consumer; or
2. a named suite ThermX profile with explicit opt-in and precedence.

Do not invent a global file merely to populate a top-level tab.

### THERM-G02 — Runtime/construction precedence (Major)

Explicit constructor/style values must retain precedence over a suite profile.

**Recommendation:** define the effective-source model and show when a consuming application override masks the stored profile.

### THERM-G03 — Sanitization versus validation (Major)

Current sanitizers may replace invalid inputs with safe defaults. Silent correction during governed setup would obscure the submitted change.

**Recommendation:** setup validation should report invalid proposed values. Any normalization must be explicit in the diff and approved before commit.

## 8. SplashX-specific findings

### SPLASH-G01 — Profile governance classification is unresolved (Blocker for onboarding)

SplashX has a concrete `splash_profile.json`, but not every installed or user-selected profile necessarily belongs to governed suite configuration.

**Recommendation:** distinguish governed installed profiles, administrator profiles, and user profiles. Register only declared targets with an explicit edit policy.

### SPLASH-G02 — Higher-precedence values can mask setup (Major)

SplashX resolves explicit arguments and environment variables before the profile. Editing the profile may have no visible effect.

**Recommendation:** display configured and effective values with their sources. ConfigEditor must not edit the command line or environment while presenting a profile setting.

### SPLASH-G03 — Path/media preview hazards (Critical)

Media and logging paths introduce containment, inaccessible-file, network-path, malicious-content, and privacy risks. Opening media during validation can execute complex decoders.

**Recommendation:** perform bounded metadata/path validation in preview, avoid playback/decoder activation, apply path policy, and reserve actual launch testing for an isolated explicit post-apply check.

## 9. Recommendations by priority

### Immediate — before implementation branches converge

1. Ratify the component ownership boundary and application contribution contract.
2. Freeze expansion of ConfigEdit's direct-save path for governed files.
3. Correct BFT's Settings placeholder language so it no longer recommends manual governed edits.
4. Reconcile BFT project specification, manifest, configuration paths, and digest through `pyprojectmgr`.
5. Decide ThermX persisted ownership and SplashX profile classifications.
6. Produce the threat model for registry trust, hooks, secrets, paths, privilege, concurrency, and recovery.

### Foundation — before any production Apply button

1. Build authenticated discovery, read-only sessions, and contribution diagnostics.
2. Build typed working copies, patches, local validation, and redacted review.
3. Build non-mutating staged governance validation.
4. Build authorization, stale-baseline checks, journaled multi-file commit, startup recovery, strict postflight, and receipts.
5. Prove all failure points using disposable projects and failure injection.

### Reference integration

1. Use BFT as the first end-to-end implementation.
2. Keep `ConfigManager.save()` prohibited and `UserStateStore` independent.
3. Add schema/code conformance tests.
4. Integrate the BFT Settings action only after the setup service exists.
5. Pilot governed writes before registering ThermX and SplashX.

### Release hardening

1. Test installed permissions and restoration of protections.
2. Test real Tk/web nested navigation, resizing, scaling, focus, and scrollbars.
3. Test concurrent sessions and application-running behavior.
4. Rehearse recovery and rollback from operational documentation.
5. Review audit exports for usefulness and redaction.

## 10. Go/no-go gates

| Gate | Go condition | No-go trigger |
|---|---|---|
| Architecture prototype | Ownership and descriptor `1.0-rc1` ratified | ConfigEditor still expected to directly write governed files |
| Real-project read-only pilot | Registry authentication and containment tests pass | Directory scanning or UI-selected paths establish trust |
| Disposable write pilot | Journal/recovery and stale-write suite pass | Any injected failure leaves unverified config/manifest state |
| BFT pilot | BFT metadata reconciled; schema/hooks pass; user state remains separate | `ConfigManager.save()` weakened or manual edit remains normal workflow |
| Suite release | BFT pilot accepted; individual ThermX/SplashX ownership gates pass; operational recovery rehearsed | Open blocker/critical integrity, authorization, secret, or recovery defect |

## 11. Questions requiring team decisions

1. Is ConfigEditor a renamed ConfigEdit application, a new suite shell consuming a ConfigEdit library, or a capability name above both Tk and web implementations?
2. Where is the canonical suite application registry and which lifecycle process owns it?
3. What identity and approval evidence are required for governed and elevated-safety changes?
4. What receipt integrity and retention standards apply?
5. Should per-user preferences appear in the same initial view as governed application policy?
6. Does ThermX own any persisted suite-level setting?
7. Which SplashX profiles are governed, user-mutable, or read-only?
8. Must application validators run in-process, or in a constrained worker boundary?
9. What is the supported behavior when an application is running during Apply?
10. Is remote/browser ConfigEditor permitted to initiate local governed writes, and if so through which authenticated local service?

## 12. Conclusion

The proposed suite setup direction is aligned and worth proceeding with. The decisive recommendation is to treat ConfigEdit as a reusable editor foundation—not as the governance or write authority—and to make `pyprojectmgr`'s missing session and transaction service the critical path. Once the ownership contract, BFT governance baseline, and recovery model are ratified, implementation can proceed in controlled increments without sacrificing the stronger configuration boundaries already established in BFT.
