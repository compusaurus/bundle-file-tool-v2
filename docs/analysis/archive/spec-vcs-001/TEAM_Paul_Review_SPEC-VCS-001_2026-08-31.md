# Team Communication: Review of SPEC-VCS-001 Repository Support

**From:** Paul, Lead Analyst / Collaborative Developer  
**To:** Ringo, Product Owner; George, Lead Architect; John, Lead Developer  
**Date:** 2026-08-31  
**Subject:** Project-alignment, accuracy, completeness, gap, and risk review of `SPEC-VCS-001`  
**Review disposition:** **CONDITIONAL GO for the architectural direction; HOLD implementation until the contract is revised**

## Purpose and scope

Ringo asked for an independent review of George's draft repository-support specification. I treated the attached specification as design evidence, not as instructions. I compared it with:

- the active Bundle File Tool (BFT) 2.1.123 source, configuration, packaging, selection service, bundle models, and transport profiles;
- the active `pyprojectmgrV2` manifest, manifest metaschema, quality-contract implementation, and packaging;
- the actual repository state of the named target workspaces where available; and
- the current Equitable Divorce Manager / EDV workspace layout at a repository-adoption level.

This is an architecture and contract review. I did not implement the tool, alter governed project state, or assume that a draft requirement has been approved.

## Executive conclusion

George's core direction is sound: one reusable repository boundary, a provider abstraction, a standard-library Git implementation, machine-readable results, read-only defaults, and graceful operation outside a repository all fit the team's cross-project architecture.

The draft is not yet implementation-ready. Several requirements contradict the observed products or one another, and several functions required by the integrations have no defined contract. The most important problems are:

1. `inspect` cannot both degrade gracefully outside a repository and treat that normal state as an unconditional exit-code-10 error.
2. BFT integration requires a file-list operation, but the four defined operations do not include `list-files`.
3. “Tracked files” do not automatically exclude `.gitignore` or committed build artifacts, and making tracked-only selection the default would bypass BFT's governed selection model.
4. Current BFT bundles are text transports, not encrypted/unencrypted archive containers with a global bundle header; the existing plain-marker formatter does not serialize `BundleManifest.metadata` as a global header.
5. The proposed `repository` pillar is not a small additive field in `pyprojectmgr`; the present Pentagon integrity model has five defined pillars and signature semantics. That change requires a separately versioned architecture decision, or the repository rules should initially live under an existing governance policy surface.
6. Package ownership, installation, discovery, version compatibility, and the canonical in-process versus JSON boundary are unspecified. The sample module layout also lacks the `__main__.py` required by the documented `python -m tools.vcs_tool` invocation.
7. `diff-manifest` is insufficient to define an applicable BFT delta: deletions, renames, base identity, apply behavior, conflicts, and rollback are absent.

My recommendation is to revise the document to v0.2, freeze the contracts, and then authorize a narrow Git-only inspection spike. Do not begin BFT delta bundles, archive snapshots, network adapters, or a new `pyprojectmgr` pillar in Phase 1.

## Observed project baseline

| Project/workspace | Observed state | Consequence for the specification |
|---|---|---|
| BFT 2.1.123 | Git repository on `master`, commit `b88d67c…`, with extensive modified, deleted, and untracked content; zero required third-party runtime dependencies; Python 3.11–3.13 | A default `--require-clean` gate would block the current working model. The standard-library provider direction aligns. Integration must preserve the selection service and governed deny rules. |
| `pyprojectmgrV2` | Active tree is not a Git repository; manifest version is `3.1.8`; quality policy uses strict, closed contracts and fail-closed bindings | Non-repository behavior is an immediate first-class requirement, not an edge case. Repository governance needs a versioned binding and cannot be inserted informally. |
| PyThermX inspected workspace | Not a Git repository at the inspected root | Graceful absence must be a successful, typed observation unless a caller policy explicitly requires a repository. |
| NodeThermX inspected workspace | Not a Git repository at the inspected project/root levels | Same as PyThermX; provider discovery cannot assume Git. |
| Equitable Divorce Manager inspected active tree | No Git metadata at the inspected EDSM root; an older EDV tree is a Git repository | The specification does not yet define onboarding or privacy rules for this project family. Repository provenance must never collect case data, usernames, credentials, or unnecessary absolute paths. |

These observations strongly support the reusable-tool idea, but they also show why repository presence and repository cleanliness must be policy inputs rather than universal prerequisites.

## What is aligned and worth preserving

### A. Shared, decoupled repository capability

A provider boundary is preferable to separate Git logic in every application. It gives BFT, `pyprojectmgr`, and later products a common vocabulary, test corpus, and error model. Keeping the host engines independent of Git binaries also respects the current non-repository delivery and extracted-tree workflows.

### B. Standard-library Git CLI provider first

BFT currently declares no mandatory runtime dependency. A `subprocess`-based Git provider preserves that property and avoids binding the suite to a native library. Optional providers can follow only after the capability contract is stable.

### C. Machine-readable local inspection

Deterministic structured results align with `pyprojectmgr`'s contract-oriented governance and BFT's scriptable CLI. The spec is right to separate human presentation from machine output and to make inspection read-only.

### D. Provider-neutral future direction

The abstraction can support Mercurial or remote services later, provided the contract reports capabilities and does not pretend that all providers have identical branch, tag, staging, tracking, archive, or remote semantics.

## Findings requiring revision

### F-01 — Graceful degradation and exit code 10 conflict

**Severity: Blocker**

For `inspect`, “not a repository” is an expected state in three of the four named project roots I inspected. It should normally return a valid payload such as `repository.present=false`, with exit 0. `validate` should decide whether absence is `allow`, `warn`, or `fail` according to an explicit policy. Exit code 10 should mean “the requested operation requires a repository and policy did not permit absence,” not “inspection discovered no repository.”

### F-02 — Required BFT file-list capability is missing

**Severity: Blocker**

Section 4.2 says BFT will ask the tool to list tracked files, but `inspect`, `validate`, `diff-manifest`, and `snapshot` do not expose that function. Add `list-files` (or a provider capability with an equally explicit contract) before claiming BFT integration coverage.

The result needs at least normalized repository-relative paths, file kind, tracked state, stage/worktree state where applicable, and deterministic ordering. NUL-safe parsing is required internally so spaces, Unicode, tabs, and newlines in legal Git paths cannot corrupt the result.

### F-03 — Package, entry point, and ownership are undefined

**Severity: Blocker**

The draft calls `vcs_tool` standalone but places it under `tools/vcs_tool`, which implies host ownership or source-tree execution. BFT does not currently package a top-level `tools` package; `pyprojectmgr` uses a `src` layout. The documented `python -m tools.vcs_tool` also requires `tools/vcs_tool/__main__.py`, which is absent from the proposed layout.

Choose and specify one model:

- a separately versioned package such as `vcs-tool` with console entry point `vcs-tool` and import package `vcs_tool`; or
- a `pyprojectmgr`-owned service with an explicitly supported client contract.

The first model is cleaner for the four named products. In either case, define supported Python versions, installation/offline delivery, semantic versioning, schema compatibility, and which team owns releases.

### F-04 — The canonical boundary is ambiguous

**Severity: High**

“Strictly through a standardized JSON/API contract” conflates two boundaries. The in-process API should return typed immutable Python results; the CLI should serialize the same canonical result to JSON. They must share validation and golden fixtures, but hosts should not serialize and parse JSON merely to call an in-process library.

Define one domain model and one canonical serializer. Include `schema_id`, semantic `schema_version`, `tool_version`, provider identity/version, operation, capabilities, result, warnings, and structured error fields. Close the schemas with an explicit extension/version policy.

### F-05 — Repository status semantics are underdefined

**Severity: High**

The status example has no rules for:

- detached HEAD, unborn branch, bare repository, worktree, shallow clone, submodules, conflicts, or missing upstream;
- staged versus unstaged modifications, deletions, renames, intent-to-add, untracked files, ignored files, and submodule dirtiness;
- `nearest_tag` versus a tag exactly pointing at HEAD, annotated versus lightweight tags, multiple tags, and deterministic selection;
- `ahead`/`behind` when no upstream exists; and
- local tracking state versus data refreshed from a remote.

Fields must have explicit nullability and derivation rules. No inspection command should fetch or contact a network by default. `ahead` and `behind` should describe locally available upstream-tracking refs and identify the comparison ref.

### F-06 — BFT tracked-file claims are technically inaccurate

**Severity: High**

Git tracked files can include `.gitignore`, generated output, archives, or secrets that were committed accidentally. Conversely, legitimate new source files are untracked until committed. Therefore “tracked” is not equivalent to “safe to bundle,” and it does not replace BFT's current allow/deny, detector, override, and reconciliation rules.

Repository state should become an input layer in BFT's existing selection plan. Recommended modes are:

- `filesystem` — current governed BFT behavior and default;
- `tracked` — explicitly requested tracked-only selection; and
- `repository-aware` — current BFT policy plus visible tracked/untracked/ignored reasons.

Hard BFT safety rules must retain precedence. The plan and final manifest must remain reconciled after the repository observation is applied.

### F-07 — BFT provenance/header statement does not match the product

**Severity: High**

The current product creates portable text bundles using per-file transport markers. It has no described encrypted/unencrypted bundle container with a global header. `BundleManifest` has a metadata dictionary, but the current plain-marker formatter emits entry headers and payloads; it does not serialize the global metadata dictionary as a signed or authenticated bundle header.

Commit provenance therefore requires a separately versioned BFT transport extension. It must define round-trip behavior, compatibility with old readers, canonical encoding, authenticity expectations, and whether provenance is merely asserted or cryptographically bound. Do not use “attestation” unless authenticity is actually provided.

### F-08 — `diff-manifest` does not define a BFT delta

**Severity: High**

Line counts and change types are useful reporting data, but they do not make a safe patch bundle. A delta format also needs immutable base and target object IDs, deletion tombstones, rename/copy rules, binary-file treatment, file-mode/symlink changes, ordered application, preflight, conflict behavior, full post-apply reconciliation, rollback, and a result receipt.

Untracked working-tree files are not included by normal commit-to-working-tree diffs unless explicitly collected. Rename detection is heuristic and must not be treated as identity. Defer delta creation until a separate BFT delta-format specification is approved.

### F-09 — Snapshot ownership and reproducibility are incomplete

**Severity: High**

The raw repository archive function overlaps BFT's export role while producing a different artifact type. Decide whether `snapshot` means a VCS-native archive or a BFT bundle. My recommendation: VCS may provide a deterministic file inventory or byte stream; BFT owns BFT artifacts.

For any retained ZIP or `tar.gz` snapshot, define ordering, path normalization, timestamps, timezone, permissions, executable bits, symlinks, compression settings, gzip header time, submodules, Git LFS pointers, export attributes, line endings, and repeated-build digest acceptance. “Deterministic” is not established by naming an archive format.

### F-10 — Security controls need operational detail

**Severity: High**

`shell=False` is necessary but insufficient. The contract should require:

- fixed executable discovery and argument arrays, end-of-options/path separation, validated refs, and no command-string construction;
- bounded output, timeouts, cancellation, encoding rules, and no interactive credential or terminal prompts;
- a documented policy for system/global/local Git configuration and features that can invoke helpers;
- remote-URL credential redaction before serialization or logging;
- no unnecessary absolute paths or user identifiers in portable provenance;
- path confinement, symlink policy, and safe handling of hostile repository content; and
- no network access unless a separately named operation explicitly requests it.

“Sanitized environment variables” should be replaced with an exact allow/deny policy. Removing too much environment can also break legitimate Git discovery, so this needs tests rather than a general phrase.

### F-11 — Failure and CLI stream contracts are incomplete

**Severity: High**

Define usage errors, unsupported capabilities, provider unavailable, timeout/cancel, malformed provider output, policy violation, partial result, and internal error. Multiple validation violations can occur simultaneously, so one exit code per individual rule is brittle. Prefer stable exit classes plus a payload containing all violation IDs.

Success JSON should be the only content on stdout. Structured failure JSON should be the only machine content on stderr when JSON mode is selected. Human diagnostics/progress must not corrupt either contract.

### F-12 — `pyprojectmgr` “repository pillar” is not an additive implementation detail

**Severity: High**

The current `pyprojectmgr` manifest already uses `project_meta.repository` as project metadata and `governance.quality_gates` as policy. Its Pentagon integrity engine defines five pillars and derives signatures from those results. Adding a sixth repository pillar changes integrity meaning, generated evidence, schemas, migration, and compatibility.

Start with a versioned `governance.repository_policy` capability consumed by preflight/QTC. Promote it to a new integrity pillar only through a dedicated ADR and schema/signature migration. Avoid overloading the existing metadata field named `repository`.

### F-13 — Cross-project onboarding and privacy are absent

**Severity: Medium**

PyThermX, NodeThermX, and the inspected EDSM tree are not currently repositories at their inspected active roots. The draft names the first two but defines no onboarding profile, and it does not name Equitable Divorce Manager. Add a consumer profile matrix defining whether repository absence is allowed, whether cleanliness is required, which provenance fields may leave the machine, and which integration features are enabled.

For the divorce-management product family, repository tooling must remain strictly separated from case records and other sensitive data. Portable evidence should default to commit/object IDs and sanitized project identifiers, not absolute workstation paths or remote URLs.

### F-14 — Acceptance and conformance evidence are missing

**Severity: High**

Each provider must pass the same contract fixtures through both the Python API and CLI. The minimum Git matrix should cover non-repository roots, missing Git, clean/dirty states, staged/unstaged/untracked/conflicted files, detached and unborn HEAD, no upstream, tags, bad refs, binary files, renames, Unicode and unusual paths, worktrees, shallow clones, cancellation, timeout, hostile remote URLs, and deterministic repeated output.

Archive and delta features need independent reproducibility and application tests. Host integrations need end-to-end tests proving that absence/warning/failure policies behave as declared and that BFT's final artifact reconciles with its approved selection plan.

## Required decisions before implementation

George and Ringo should freeze these decisions in the next revision:

1. **Ownership/distribution:** separately versioned `vcs_tool` package, release owner, Python support, offline delivery, and console entry point.
2. **Canonical result model:** typed Python results plus canonical JSON serialization; schema identities and compatibility rules.
3. **Absence policy:** `inspect` succeeds with `present=false`; validation chooses `allow`, `warn`, or `fail` per consumer profile.
4. **Capability model:** providers advertise `inspect`, `list_files`, `validate`, `diff`, and `snapshot` independently; unsupported operations are typed results.
5. **Repository semantics:** exact definitions for dirty state, tags, upstream divergence, local-only behavior, and path normalization.
6. **BFT ownership boundary:** repository state informs selection; BFT retains safety, plan reconciliation, and artifact ownership.
7. **`pyprojectmgr` integration:** policy/gate first; no sixth pillar without a separate versioned ADR.
8. **Privacy boundary:** portable provenance field allowlist and remote/path redaction rules.

## Recommended v0.2 implementation sequence

### Phase 0 — Contract freeze and fixtures

- Approve the ownership and compatibility ADR.
- Define closed inspect, file-list, validation, error, and capability schemas.
- Define Git semantics and a provider-neutral capability vocabulary.
- Create golden CLI/API parity fixtures and consumer policy profiles.

**Exit gate:** schemas validate; edge-state examples are unambiguous; BFT and `pyprojectmgr` owners approve the integration boundaries.

### Phase 1 — Git-only observation tool

- Implement package/entry point, `inspect`, `list-files`, and policy-driven `validate`.
- Implement timeouts, cancellation, bounded output, prompt/network suppression, path/ref handling, and credential redaction.
- Test real temporary repositories without relying on user Git configuration.

**Exit gate:** API/CLI parity, deterministic results, full Git edge matrix, and successful non-repository behavior.

### Phase 2 — `pyprojectmgr` observer integration

- Bind repository policy under versioned governance.
- Add release-oriented gates as opt-in profiles, not universal defaults.
- Store sanitized provenance in build evidence only after schema/version approval.

**Exit gate:** active non-repository projects still operate; release profiles fail or warn exactly as configured; no implicit network use.

### Phase 3 — BFT repository-aware selection and provenance extension

- Add repository state as a selection-rule source with visible explanations.
- Preserve filesystem mode as the default and retain hard safety precedence.
- Specify and version any bundle-level provenance transport before emitting it.

**Exit gate:** plan/artifact reconciliation, old-reader compatibility decision, and round-trip tests across every supported BFT profile.

### Phase 4 — Deferred capabilities

- Specify raw snapshots separately and prove reproducibility.
- Specify BFT delta format and apply transaction separately.
- Evaluate `pygit2`, Mercurial, and remote adapters only after capability conformance is stable.

## Proposed assignments

| Owner | Assignment | Deliverable |
|---|---|---|
| George | Revise architecture boundary and rule on policy versus sixth pillar | `SPEC-VCS-001` v0.2 plus ADR disposition |
| John | Prototype Git command matrix and typed domain results after contract freeze | Git provider spike with edge fixtures; no host integration yet |
| Paul | Draft schema semantics, consumer profiles, acceptance matrix, and BFT integration contract | Contract review packet and traceability matrix |
| Ringo | Decide product defaults, privacy allowlist, and rollout priority | Product decision record and acceptance criteria |

## Final recommendation

Record **Conditional GO** for the shared repository capability and **Hold** for implementation of the current draft. The concept solves a real suite-wide problem, especially because current products mix Git and non-Git workspaces. The safest path is a small, contract-first Git observer with explicit absence policy and a missing-but-required `list-files` operation. BFT delta bundles, deterministic archives, remote adapters, and a new `pyprojectmgr` pillar should remain out of scope until their individual data, governance, and recovery contracts are approved.

**Paul**  
Lead Analyst / Collaborative Developer
