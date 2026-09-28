# Team Communication: Ratification Review of SPEC-VCS-001 v0.2.1

**From:** Paul, Lead Analyst / Collaborative Developer  
**To:** Ringo, Product Owner; George, Lead Architect; John, Lead Developer  
**Date:** 2026-08-31  
**Subject:** Contract-freeze assessment of the repository support specification  
**Document reviewed:** `SPEC-VCS-001_v0.2.1_Repository_Support_Specification.md`  
**Source SHA-256:** `0741cfb526328bdf9d3e6d2ff9ed0ca30422d5da228741d1a7168309675afea3`  
**Disposition:** **ARCHITECTURE DIRECTION APPROVED; PHASE 0 FREEZE NOT ACCEPTED. RETURN AS A v0.2.2 FREEZE CANDIDATE.**

## Purpose and review boundary

Ringo asked for an independent review of George's v0.2.1 revision and a team recommendation. I treated the attached specification as a design artifact to analyze, not as instructions to execute. This review assesses alignment, accuracy, completeness, gaps, foreseeable implementation risk, and readiness to declare the v1 contract frozen. It does not implement or authorize the tool.

The review compares v0.2.1 with the previous v0.2.0 findings and the verified product context for Bundle File Tool (BFT), `pyprojectmgrV2`, the inspected ThermX workspaces, and the EDSS/EDSM/EDV privacy boundary. I also checked the reviewed workspace for the five named schema artifacts and conformance files claimed by the roadmap.

## Executive conclusion

George's revision is materially better and preserves the right architecture. It now locks one package identity (`src/vcs_tool`, `vcs-tool`, and `python -m vcs_tool`), models index and worktree file state separately, introduces per-rule policy dispositions, defines strict JSON stream purity, bounds Git subprocess execution, separates privacy projections, and correctly defers serialized BFT provenance to a future BFT transport RFC.

Those changes close important design risks. Of the original fourteen findings, **seven are resolved and seven are partially resolved**. Of the five v0.2.0 ratification blockers, **two are resolved and three are only partially resolved**.

The document nevertheless labels itself “RATIFIED” and Phase 0 “COMPLETE” before the contract is internally consistent or supported by freeze evidence. In the reviewed workspace, no matching `vcs_status_v1.json`, `vcs_files_v1.json`, `vcs_validate_v1.json`, `vcs_diff_summary_v1.json`, or `vcs_error_v1.json` artifact exists under `docs`, `src`, or `tests`. The specification contains Markdown-escaped schema examples, but those are not directly distributable or validator-tested schema files. Several examples, schemas, and test cases also contradict one another.

My recommendation is to preserve the architecture, change the status back to **Freeze Candidate**, and issue a focused v0.2.2 contract repair. John may run a non-binding provider spike to retire command and platform risk, but the team should not merge an implementation against a supposedly frozen v1 surface until the five blocker groups below are closed.

## What v0.2.1 gets right

- **One package surface:** Section 2.1 removes the earlier `tools.vcs_tool` versus `vcs_tool` ambiguity and standardizes `src/vcs_tool`, the console script, and module invocation.
- **BFT-usable inventory model:** `list-files` now separates `index_status`, `worktree_status`, `conflict_status`, and `original_path`, preserving BFT's own selection and safety authority.
- **Coherent policy direction:** Rules now carry `allow`, `warn`, or `fail` dispositions, and repository-dependent rules become not applicable when repository presence is allowed.
- **Honest BFT transport boundary:** Section 7.2 limits VCS metadata to the in-memory manifest and defers bundle serialization rather than claiming unsupported artifact provenance.
- **Stronger machine interface:** JSON mode requires exactly one schema-compliant document on the designated stream and forbids tracebacks and diagnostic prose.
- **Useful hardening baseline:** `shell=False`, prompt suppression, a path separator, a constrained environment, a ten-second timeout, and a ten-megabyte output ceiling are all appropriate starting controls.
- **Correct governance placement:** Repository policy remains QTC/governance evidence and does not become a sixth `pyprojectmgr` Pentagon pillar.
- **Cross-project privacy intent:** Local, portable, and machine-log projections are distinguished, and callers must supply an allowlisted root.

## Prior-finding resolution ledger

| Prior finding | v0.2.1 status | Assessment |
|---|---|---|
| F-01 Repository absence versus exit 10 | **Resolved** | Non-repository `inspect` remains a successful typed result. |
| F-02 Missing BFT file-list capability | **Resolved** | `list-files` is a first-class API/CLI operation with JSON and NUL output. |
| F-03 Package, entry point, and ownership | **Partial** | The package ambiguity is resolved; release ownership, version source, schema-data packaging, license, and offline delivery remain unspecified. |
| F-04 Canonical domain/API/JSON boundary | **Partial** | A standard envelope and closed schemas are introduced, but the five schemas do not consistently implement that envelope and are not published as machine-readable artifacts. |
| F-05 Repository-state semantics | **Partial** | Common states are covered; SHA object format, clean-state details, conflicts, submodules, worktrees, and upstream freshness remain incomplete. |
| F-06 BFT tracked-file safety claim | **Resolved** | BFT stays authoritative and filesystem mode remains the default. |
| F-07 BFT provenance/header mismatch | **Resolved by deferral** | The document now says metadata is in memory only and requires a later BFT transport RFC for serialization. |
| F-08 Diff report versus applicable delta | **Resolved** | `diff-summary` remains observational; patch transport is outside scope. |
| F-09 Snapshot ownership and reproducibility | **Resolved** | Snapshot/archive ownership remains with BFT. |
| F-10 Security controls | **Partial** | Important process bounds are present, but exact command, ref, Git-config, cancellation, decoding, and bounded-capture rules are not frozen. |
| F-11 Failure and stream contracts | **Partial** | Stream purity is resolved; cancellation is absent and output-limit failure is incorrectly mapped to the internal-error exit class. |
| F-12 Proposed sixth repository pillar | **Resolved** | The five-pillar integrity model is explicitly invariant. |
| F-13 Cross-project onboarding/privacy | **Partial** | Projection profiles and root allowlisting are present, but they are not schema-bound and path-name rejection is not a sufficient privacy boundary. |
| F-14 Acceptance/conformance evidence | **Partial** | The twenty-case matrix is useful, but it contains contract mismatches and omits high-risk state, security, schema, and integration cases. |

## Previous-blocker closure ledger

| v0.2.0 blocker | v0.2.1 status | Result |
|---|---|---|
| B01 Normative schema contracts | **Partial** | Inline schemas were added, but files, fixtures, envelope consistency, and validator evidence are missing. |
| B02 Packaging ambiguity | **Resolved** | One source/import/CLI layout is now selected. |
| B03 Validation contradiction | **Partial** | Rule dispositions and aggregation are improved; `NOT_APPLICABLE` is not representable in the result schema and policy details remain unspecified. |
| B04 BFT provenance transport | **Resolved** | Serialization is explicitly deferred to a BFT-owned RFC. |
| B05 Privacy/output conflict | **Partial** | Profiles are defined in prose but not as interoperable schemas; path, remote, and timestamp rules still conflict with deterministic portable output. |

## Ratification blockers

### VCS-021-B01 — Ratification and schema freeze are asserted without freeze artifacts

**Severity: Blocker**

The roadmap declares all five schemas frozen under `specs.equitable.dev/schemas/vcs/` and Phase 0 complete. The package tree also names five schema files. No matching artifact is present in the reviewed workspace under `docs`, `src`, or `tests`; no positive or negative schema fixtures are present; and no approval record or conformance evidence accompanies the “RATIFIED” label.

The embedded blocks are Markdown-escaped representations, not directly consumable JSON files. A filename and an inline example do not establish a frozen interface. This is also a release risk: Section 2.2 does not say how schema resources enter the wheel, how callers locate them offline, or which source is authoritative if local and hosted copies differ.

**Required correction:**

1. Change the document status to `FREEZE CANDIDATE` until team approval is recorded.
2. Commit the five valid Draft 2020-12 schema files under `src/vcs_tool/schemas/` and package them as distribution data.
3. Add `$id` resolution tests, positive examples, one negative fixture per constraint family, and a checksum or release-manifest rule for any hosted mirror.
4. Add a short approval record naming Ringo, George, John, and Paul dispositions and the exact schema commit/checksums.

**Exit evidence:** all schema files parse offline, all cross-references resolve offline and from their canonical IDs, fixtures produce the expected accept/reject results, packaged-wheel access is tested, and the approval record identifies the frozen artifact set.

### VCS-021-B02 — The “standard envelope,” validation result, and conformance cases disagree

**Severity: Blocker**

Section 3 says all JSON responses share the standard envelope, including `provider_version`, `capabilities`, and `warnings`. The `inspect` schema requires those fields, but `list-files`, `validate`, and `diff-summary` omit `provider_version` and `capabilities`; the error schema omits operation, provider, capabilities, and warnings. Every `schema_id` property is merely a string rather than a constant equal to the schema `$id`, so an instance can claim the wrong schema and still validate.

The validation contract has two direct inconsistencies:

- TC-16 expects `violations=[...]`, while the schema permits only `findings`.
- TC-17 expects a machine-readable `NOT_APPLICABLE` finding, while a finding contains only `severity`, `passed`, `message`, and `details`. A boolean cannot distinguish pass from not applicable.

**Required correction:** define one reusable versioned envelope (or explicitly document operation-specific envelope variants), make `schema_id` a `const`, and add a finding outcome such as `PASS`, `FAIL`, `WARN`, or `NOT_APPLICABLE`. Use one canonical term—`findings`—through schemas, models, examples, and tests. Define count invariants so `violation_count` and `warning_count` must agree with findings.

**Exit evidence:** the five schemas share a tested envelope rule, examples validate against the correct schema and fail against the wrong one, and TC-16/TC-17 use the exact model and serialized field names.

### VCS-021-B03 — `diff-summary` cannot accurately represent its promised inputs and outputs

**Severity: Blocker**

The operation promises revision-to-revision and HEAD-to-working-tree comparisons, yet both `base_ref` and `target_ref` are required strings and no working-tree sentinel or target kind is defined. It is unclear whether a working-tree comparison includes staged changes, unstaged changes, untracked files, or all three.

The schema also requires non-negative integer insertions and deletions for every file. Git's numeric diff representation uses a non-numeric marker for binary files; coercing that state to zero falsely means “known zero line changes.” Renamed and copied entries lack `original_path`, and no rule defines rename detection thresholds or deterministic ordering.

Unlike `list-files`, the section has no Python API signature or CLI invocation. Ref-versus-path disambiguation and unsafe-ref behavior therefore remain unstated.

**Required correction:** add explicit base and target kinds (`ref`, `index`, `worktree`), nullable line counts for binary files with defined total aggregation, `original_path` for rename/copy, exact API/CLI signatures, deterministic ordering, and staged/unstaged/untracked semantics. Define ref validation and the exact Git argument shapes used to separate revisions from paths.

**Exit evidence:** schema-valid tests cover ref-to-ref, HEAD-to-index, HEAD-to-worktree, binary, rename, copy, type change, hostile ref, missing ref, and repeated deterministic output.

### VCS-021-B04 — Subprocess security and resource-failure behavior are not yet a frozen contract

**Severity: Blocker for the hardened provider claim**

The hardening baseline is useful, but `--` before path arguments does not solve unsafe revision arguments. Exact command templates are absent. The environment allowlist retains `HOME` and `USERPROFILE`, while only system Git configuration is disabled; global and local configuration can still affect behavior through settings such as external diff or filesystem monitors. The specification does not state which configuration layers are trusted, suppressed, or selectively overridden.

`VcsOutputLimitError` is mapped to exit 50, which the exit table reserves for an unhandled internal exception. A controlled safety limit is not an internal bug. Cancellation, bounded streaming capture, encoding/locale behavior, executable resolution, and helper-variable suppression are also missing.

**Required correction:** publish an operation-by-operation Git command matrix, ref grammar, config-layer policy, executable-resolution rule, decoding/locale rule, bounded streaming strategy, and cancellation contract. Give output-limit and cancellation stable non-internal exit/error classes. Explicitly neutralize or reject external diff, pager, askpass/SSH askpass, fsmonitor, and other helpers relevant to the selected commands.

**Exit evidence:** adversarial tests cover leading-dash refs, path/ref ambiguity, hostile global and local Git configuration, helper execution attempts, timeout, cancellation, output overflow, non-UTF filenames/output, and proof that no network or prompt path is invoked.

### VCS-021-B05 — Privacy projections are prose-only and portable output is not reproducibly defined

**Severity: Blocker for Phase 2 and matrimonial-system use**

The local `inspect` schema always requires `root_dir` and may expose `remote_url`, while `PORTABLE_PROVENANCE` is only a prose field list. There is no separate schema showing how a host obtains a payload that excludes those local fields. Adding `timestamp` to portable provenance also defeats byte reproducibility unless its source and canonicalization are defined.

The `MACHINE_LOG` example calls `github.com/org/repo` a redacted hostname, but it includes organization and repository path information. That can itself identify a private project. The vault pattern examples (`/vault/`, `*.case`, `*.edsm`) are sensitive to separators, case, symlinks, junctions, and naming variation; they can be defense in depth, but not the security boundary.

**Required correction:** publish a distinct `portable_provenance_v1` schema and a machine-log projection policy. Exclude remotes from portable and machine-log output by default. Either omit the timestamp from canonical provenance or define a caller-supplied, normalized reproducible timestamp separate from repository inspection. Make canonical resolved-root allowlisting and explicit deny roots the primary isolation rule, including symlink/junction containment.

**Exit evidence:** schema and tests prove that portable output contains no absolute path, username, remote URL, organization/repository path, or uncontrolled clock value; privacy-root tests cover Windows and POSIX separators, case variation, symlink/junction escape, and nested repository boundaries.

## High-priority accuracy and completeness gaps

### VCS-021-H01 — File-state enums are still incomplete

The two-dimensional design is correct, but the conflict enum omits Git's both-added and both-deleted unmerged states. Index/worktree enums do not represent type changes even though the diff schema does. Submodule state is not represented. Define all supported porcelain-v2 mappings, an explicit unsupported-state behavior, deterministic sort order, default inclusion behavior when no CLI flags are supplied, path normalization, and ignored-directory expansion.

### VCS-021-H02 — Repository-state derivation needs a complete decision table

`commit_sha` is fixed to forty hexadecimal characters without an object-format policy. Either explicitly support only SHA-1 repositories and return a typed unsupported-state error, or add `object_format` and lengths appropriate to supported Git repositories. Also freeze the meaning of clean state for untracked files, conflicts, submodules, intent-to-add, and file-mode changes; define bare and linked-worktree behavior; and state that ahead/behind reflects local tracking refs that may be stale because the tool never fetches.

### VCS-021-H03 — The host policy itself lacks a normative schema

The result schema is not the policy-input schema. `VcsPolicy` is shown as Python and `pyprojectmgr` as YAML, but branch wildcard grammar, case sensitivity, invalid rule combinations, defaults, and versioning are not machine-defined. Add `vcs_policy_v1.json` or an equivalent canonical host binding before Phase 2, then bind it into the `pyprojectmgr` governance schema instead of relying on permissive additional properties.

### VCS-021-H04 — The twenty-case matrix is a smoke suite, not a freeze suite

Add cases for every unmerged status, ignored files, staged-plus-unstaged state on one path, rename/copy source paths, type and mode changes, binary counts, missing/stale upstream, ahead/behind combinations, bare/worktree/submodule states, output limit, cancellation, hostile refs/configuration, negative schema fixtures, deterministic ordering, no-network proof, packaged schema access, and end-to-end `pyprojectmgr`, BFT, and EDSS/EDSM/EDV boundaries.

TC-20 should promise byte identity only between the canonical serializer and JSON CLI output. A typed Python object is not itself byte-identical, and NUL/text modes intentionally have different representations.

### VCS-021-H05 — Delivery ownership remains incomplete

Before release, name the version source, release owner, package license, wheel/sdist data rules for schemas, supported-platform policy, Git discovery rule, and offline installation path. These do not require reopening the architecture, but they do require evidence before distribution.

## Project-alignment conclusions

### `pyprojectmgrV2`

The specification correctly leaves the Pentagon at five pillars and treats repository state as governance/QTC evidence. Phase 2 still needs a versioned repository-policy schema, exact wildcard semantics, policy migration/default behavior, and a separate portable-provenance schema. The example `require_repository: allow` plus a failing clean-worktree rule is coherent only if the not-applicable outcome is machine-representable and tested.

### Bundle File Tool

The three selection modes now align with BFT's responsibility boundary: filesystem remains default, tracked mode intersects the BFT plan with repository inventory, and repository-aware mode annotates rather than replaces BFT selection. Hard-deny rules and final plan-to-artifact reconciliation must remain authoritative.

The provenance correction is acceptable: metadata is runtime-only until a BFT-owned transport RFC defines serialization, round-trip compatibility, validation, and any authenticity claim. No bundle should be described as carrying provenance before that RFC is implemented.

### PyThermX and NodeThermX

Successful non-repository inspection continues to fit the inspected active roots. Each host should adopt an explicit policy profile rather than silently inheriting repository-required defaults. Repository adoption should not become a prerequisite for unrelated work.

### EDSS / EDSM / EDV

The privacy direction is improved, but matrimonial-system use remains blocked until projection schemas and canonical root containment are tested. Source repositories, client vaults, and case evidence must remain separate authorities even when directory names or repository ancestry overlap.

## Recommended phase gate

| Activity | Recommendation | Constraint |
|---|---|---|
| Declare Phase 0 complete | **No** | Five blocker groups and freeze artifacts remain. |
| John runs a provider risk spike | **Yes, draft-only** | No stable API/schema commitment and no host integration. |
| Merge/release `vcs_tool` v1 | **No** | Requires v0.2.2 approval and executable conformance evidence. |
| Start `pyprojectmgr` Phase 2 integration | **No** | Requires policy and portable-provenance schemas. |
| Start BFT Phase 3 selection integration | **No** | Requires stable file-state semantics and Phase 1 evidence. |
| Serialize provenance into bundles | **No** | Requires a separate BFT transport RFC. |

## Recommended assignments

| Owner | Immediate assignment | Exit evidence |
|---|---|---|
| **George** | Issue v0.2.2 as `FREEZE CANDIDATE`; extract and reconcile schemas; add the command, privacy, and state decision tables. | Specification, schema files, traceability matrix, and approval-ready change log. |
| **John** | Build a disposable Git CLI spike and adversarial fixture repositories; validate command shapes across Windows and supported Python/Git versions. | Test evidence for refs, paths, binary/rename/conflict states, helpers, timeouts, output limits, and cancellation. |
| **Paul** | Review schema invariants, policy dependency rules, BFT selection reconciliation, and portable/privacy projections. | Independent schema and cross-product sign-off report. |
| **Ringo** | Decide the portable timestamp rule, machine-log remote policy, platform scope, and formal ratification authority. | Product decision record and final Phase 0 approval. |

## v0.2.2 acceptance checklist

1. The status is `FREEZE CANDIDATE` until approval; ratification identifies people, commit, schema checksums, and evidence.
2. Five valid, packaged, offline-resolvable schemas exist with positive and negative fixtures.
3. Every response implements the declared envelope or a documented versioned variant; `schema_id` is constrained to its schema.
4. Validation findings represent `PASS`, `FAIL`, `WARN`, and `NOT_APPLICABLE`, with consistent counts and names.
5. Diff inputs, binary counts, rename/copy source paths, working-tree semantics, API, CLI, and ref safety are complete.
6. File-state and repository-state decision tables cover supported Git states and define typed unsupported results.
7. The process contract covers exact commands, Git config/helpers, timeout, cancellation, bounded output, decoding, and executable resolution.
8. Portable and machine-log projections are schema-bound, deterministic, and free of local/privacy identifiers.
9. Policy input is versioned and bound into `pyprojectmgr`; BFT provenance remains runtime-only.
10. The expanded conformance suite passes from source and built wheel on the supported platform/runtime matrix.

## Final recommendation

Record **approval of the v0.2.1 architecture direction**, but reject its self-declared ratification and Phase 0 completion. The revision has solved the earlier scope and ownership problems and is close to a usable contract. The remaining issues are concentrated in artifact truth, schema consistency, diff accuracy, subprocess isolation, and privacy projection—not in the overall architecture.

George should issue v0.2.2 as a freeze candidate, John should use the interval for a non-binding adversarial provider spike, and the team should ratify only the exact committed schemas and evidence set. That course preserves momentum without turning unresolved examples into a permanent v1 compatibility obligation.

**Paul**  
Lead Analyst / Collaborative Developer

