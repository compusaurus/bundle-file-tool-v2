# Team Communication: Review of SPEC-VCS-001 v0.2.0

**From:** Paul, Lead Analyst / Collaborative Developer  
**To:** Ringo, Product Owner; George, Lead Architect; John, Lead Developer  
**Date:** 2026-08-31  
**Subject:** Ratification-readiness review of the revised repository support specification  
**Document reviewed:** `SPEC-VCS-001_v0.2.0_Repository_Support_Specification.md`  
**Source SHA-256:** `d2104a4d1abf5e6444e8b09668c747420c73bbe1a745de9e95754238a0b1bda6`  
**Disposition:** **CONDITIONAL APPROVAL OF DIRECTION; RETURN FOR v0.2.1 CONTRACT REPAIR BEFORE FREEZE OR PHASE 1**

## Purpose and scope

Ringo asked for an updated independent review after George incorporated the first analysis into v0.2.0. I treated the attached document as a design artifact, not as instructions. I compared it with the earlier fourteen findings and with the same verified product baselines: BFT 2.1.123, the active `pyprojectmgrV2` governance model, the inspected ThermX workspaces, and the EDSS/EDSM/EDV repository-adoption and privacy context.

This communication evaluates project alignment, technical accuracy, completeness, gaps, foreseeable implementation risks, and ratification readiness. It does not authorize or implement the tool.

## Executive conclusion

The revision is a substantial and constructive response. It makes the right scope decisions:

- repository absence is now a successful `inspect` result;
- `list-files` is now a first-class operation;
- archives and delta application are explicitly deferred to BFT;
- the Pentagon remains a five-pillar model;
- BFT retains its selection and safety authority;
- network operations are excluded; and
- EDSS/EDSM/EDV privacy is recognized.

Of the fourteen earlier findings, **six are resolved, seven are partially resolved, and one remains unresolved**. The architecture is now coherent enough to complete Phase 0, but the document is not yet a valid contract freeze. Its JSON blocks are examples rather than complete normative schemas; `diff-summary` has no result schema or Python API contract; packaging still offers contradictory layouts and module names; validation policy semantics conflict internally; and BFT provenance is still assigned to metadata that its current transport formats do not serialize.

I recommend a focused v0.2.1 repair. Once the five ratification blockers below are closed with normative artifacts and tests, I would support ratification and a Git-only Phase 1 spike.

## Prior-finding resolution ledger

| Prior finding | v0.2.0 status | Assessment |
|---|---|---|
| F-01 Repository absence versus exit 10 | **Resolved** | `inspect` now returns `is_repository=false` and exit 0; exit 10 is limited to operations/policies requiring a repository. |
| F-02 Missing BFT file-list capability | **Resolved** | `list-files` is now in scope with JSON, text, and NUL surfaces. Its data model still needs repair, addressed below. |
| F-03 Package, entry point, and ownership | **Partial** | A standalone `vcs_tool` package and `__main__.py` are named, but two package layouts and two different module paths remain “supported”; release ownership and offline distribution remain unspecified. |
| F-04 Canonical domain/API/JSON boundary | **Partial** | Immutable models and canonical serializers are now named. Examples still lack a common envelope, schema IDs, operation identity, provider version/capabilities, and closed-schema rules. |
| F-05 Repository-state semantics | **Partial** | Detached/unborn HEAD, exact/nearest tags, worktree counts, and local upstream divergence are added. Important derivation and nullability rules remain undefined. |
| F-06 BFT tracked-file safety claim | **Resolved** | The three requested BFT modes are present, filesystem remains default, and BFT safety precedence is preserved. |
| F-07 BFT provenance/header mismatch | **Open** | `x_vcs_provenance` is assigned to `BundleManifest.metadata`, but current BFT formatters do not serialize that global metadata into the bundle artifact. |
| F-08 Diff report versus applicable delta | **Resolved** | The operation is narrowed to observational `diff-summary`; patch creation/application is deferred. |
| F-09 Snapshot ownership and reproducibility | **Resolved** | Snapshot/archive generation is removed from `vcs_tool` and assigned to BFT. |
| F-10 Security controls | **Partial** | Prompt suppression, credential redaction, an environment allowlist, and no-network scope are added. Exact per-command, configuration, timeout, output-bound, cancellation, and path policies remain incomplete. |
| F-11 Failure and stream contracts | **Partial** | Stable exit classes and JSON stream separation are introduced. Several error classes and JSON-purity rules remain ambiguous. |
| F-12 Proposed sixth repository pillar | **Resolved** | The five-pillar model is explicitly invariant; repository rules move to governance policy. |
| F-13 Cross-project onboarding/privacy | **Partial** | EDSS/EDSM/EDV is now in scope with privacy language. The isolation boundary is not yet expressed as enforceable roots, fields, and tests. |
| F-14 Acceptance/conformance evidence | **Partial** | A useful initial matrix is present, but it is not yet the comprehensive provider/API/CLI contract suite required for freeze. |

## Ratification blockers

### VCS-020-B01 — The schemas to be “frozen” are not present as normative contracts

**Severity: Blocker**

The specification names JSON schema files but supplies illustrative JSON objects, not complete schemas. A contract freeze requires, at minimum:

- stable `$id`/`schema_id` and semantic schema version;
- required and optional fields;
- types, enums, numeric bounds, formats, and nullability;
- `additionalProperties` policy and an extension/version strategy;
- canonical field ordering/serialization rules if byte determinism is claimed;
- structured warning and error objects rather than free-form warning strings; and
- positive and negative validation fixtures.

`diff-summary` is in the in-scope operation list but has neither a named schema in the package tree nor a result example or Python API signature. Either add `vcs_diff_summary_v1.json` and complete the contract or defer the operation from v0.2.x.

The output examples also omit fields recommended by the agreed architecture: operation identity, provider version, advertised capabilities, and a stable schema identifier. Phase 0 cannot close by freezing filenames alone.

### VCS-020-B02 — Packaging remains internally ambiguous

**Severity: Blocker**

Section 2.1 declares a standalone package named `vcs_tool`, then permits both `tools/vcs_tool/` and `src/vcs_tool/`, and claims both `python -m tools.vcs_tool` and `python -m vcs_tool`. Those are different installed package identities unless a compatibility package is deliberately shipped.

Select one canonical layout and invocation. I recommend:

- source layout: `src/vcs_tool/`;
- import: `from vcs_tool import ...`;
- module invocation: `python -m vcs_tool`;
- console entry point: `vcs-tool`; and
- no `tools.vcs_tool` compatibility surface in v1.

Add the package's `pyproject.toml`, single version source, license/ownership, supported Git version policy, offline wheel/delivery rule, and release owner. The specification version and eventual executable version should not be assumed to be the same lifecycle merely because both currently say `0.2.0`.

### VCS-020-B03 — Validation policy is contradictory and under-specified

**Severity: Blocker**

The scope promises caller-defined `allow`, `warn`, and `fail`, but `VcsPolicy` exposes booleans without a per-rule severity. The command is described as “fail-fast,” yet the specified payload aggregates multiple violations. These are incompatible models.

There are further semantic conflicts:

- `require_repository=false` combined with `require_clean=true`, as shown in the `pyprojectmgr` example, leaves cleanliness undefined when no repository exists;
- `require_synced` cannot establish remote synchronization because the tool never fetches and upstream refs can be stale;
- `require_tag` does not say whether an exact HEAD tag is required or a nearest tag is sufficient;
- `require_clean` does not define whether untracked files, conflicts, or dirty submodules count; and
- branch wildcard matching, case sensitivity, and detached-HEAD behavior are unspecified.

Replace the booleans with explicitly validated rules or profiles whose disposition is `allow`, `warn`, or `fail`. Rename `require_synced` to something truthful such as `require_tracking_ref_equal` and state that it uses locally cached tracking refs only. Aggregate all evaluated findings unless a separately named short-circuit option is requested.

Also resolve exit-code overlap: a failed `validate` repository rule should normally be exit 1 with a `VCS_GATE_REPOSITORY_REQUIRED` violation; exit 10 should be reserved for an operational command such as `list-files` or `diff-summary` that cannot run outside a repository.

### VCS-020-B04 — BFT provenance still has no artifact transport

**Severity: Blocker for BFT Phase 3; not a blocker for an isolated Phase 1 tool**

The revision correctly removes archive creation from `vcs_tool`, but Section 6.2 still labels `BundleManifest.metadata["x_vcs_provenance"]` as “Bundle Header Provenance.” In the reviewed BFT 2.1.123 code, `BundleManifest.metadata` exists in memory, while the plain-marker and Markdown-fence formatters emit per-entry headers and payloads; they do not serialize arbitrary global manifest metadata. Parsing reconstructs formatter metadata rather than round-tripping caller-supplied `x_vcs_provenance`.

Consequently, adding the dictionary key alone will not put provenance in the saved bundle, and claiming that it does would produce false assurance. Choose one of these dispositions:

1. remove portable BFT provenance from SPEC-VCS-001 and defer it to a versioned BFT transport proposal; or
2. make the requirement explicitly runtime-only and state that it is not preserved in the artifact.

Do not use “header” or “attestation” until the BFT transport specification defines serialization, compatibility, validation, and—if intended—authentication.

### VCS-020-B05 — Privacy and output fields contradict one another

**Severity: Blocker**

The privacy section prohibits absolute workstation paths in portable metadata and logs, yet both `inspect` examples emit an absolute `root_dir`. The acceptance matrix tests remote credential redaction, but the inspect schema contains no remote URL field. The contract therefore cannot establish which data is local-only, portable, loggable, or absent.

Define explicit projection profiles:

- **local diagnostic result:** may contain an absolute resolved root only when requested;
- **portable provenance:** allowlisted fields such as provider, full commit ID, exact tag, branch when attached, and clean-state claim; no root path, username, user directory, or remote URL; and
- **logs/evidence:** state exactly which projection is permitted.

For EDSS/EDSM/EDV, isolation must be enforceable. `list-files` can disclose sensitive filenames even when it never opens a file. Bind calls to an explicitly configured source-code repository root; reject roots under case-data/client-vault locations; never infer upward across a privacy boundary; and test those rejections.

## High-priority accuracy and completeness gaps

### VCS-020-H01 — `list-files` cannot represent real Git states accurately

A single `status` plus `is_tracked` and `is_staged` cannot represent Git's two-dimensional index/worktree state. One path can be staged and unstaged at the same time; conflicts have multiple stage records; rename/copy results need old and new paths; deletion and type changes need distinct states; ignored and untracked are different categories.

Use separate fields such as `index_status`, `worktree_status`, `conflict_status`, `original_path`, `is_tracked`, `is_untracked`, and `is_ignored`, with closed enums and null rules. Define:

- default CLI behavior when no inclusion flags are supplied;
- behavior on a non-repository path;
- deterministic ordering;
- duplicate/path-transition handling;
- case and Unicode normalization policy; and
- whether ignored directories are represented as directories or expanded to every ignored file.

NUL mode should define exactly what information it preserves. A path-only stream is safe for piping but cannot carry the status model exposed by JSON.

### VCS-020-H02 — Repository-state derivation remains incomplete

The new fields are useful, but the specification still needs rules for bare repositories, linked worktrees, shallow repositories, submodule dirtiness, multiple exact tags, nearest-tag selection/tie-breaking, missing upstream, stale tracking refs, intent-to-add, file-mode changes, and the length/derivation of `short_sha`. `exact_tag` may need to be a deterministic list because multiple tags can point at HEAD.

Define whether `is_clean` includes untracked files and conflicts. Ignored files should normally not make a worktree dirty, but this must be contractual rather than assumed.

### VCS-020-H03 — Security hardening needs executable command templates

The additions are directionally correct, but a generic promise to add `--` to file paths or refs is not sufficient; Git places revision and path separators differently by command, and some revision-parsing commands need validation rather than a generic terminator.

Before freeze, specify or test exact command families, executable resolution, timeout, cancellation, maximum output, decoding, pager suppression, locale behavior, and behavior under hostile Git configuration. The proposed environment allowlist still inherits `HOME`/`USERPROFILE`, which can re-enable global Git configuration; `GIT_EXEC_PATH` can redirect helpers; `SSH_AUTH_SOCK` is unnecessary for a local-only tool. Define whether system/global/local Git configuration is honored, suppressed, or selectively overridden. Clear or override askpass, external-diff, pager, and relevant helper variables rather than relying only on `GIT_TERMINAL_PROMPT=0`.

The current test matrix has a timeout case but no stated default timeout, cancellation contract, output cap, or cancellation exit/error class.

### VCS-020-H04 — JSON stream purity has an escape hatch

Section 4.2 allows “critical runtime traces” on stderr in JSON mode. That can corrupt the single structured error document a parent process expects. In JSON mode, stderr should contain exactly one schema-compliant error/violation document and no traceback or prose. Tracebacks belong in an explicitly requested debug log or human format.

Usage errors should also be structured when JSON output was successfully selected. Add typed failures for permission/I/O errors, unsupported provider capability, cancellation, output limit, malformed provider response, unsafe path/ref, and unsupported repository state.

### VCS-020-H05 — Provider capability negotiation is still absent

The architecture retains a provider registry, but results expose only a provider name. Add provider version and advertised capabilities. Future Git, Mercurial, native, and remote providers will not implement identical staging, ignored-file, upstream, tag, or diff behavior. Hosts must be able to distinguish “unsupported” from “empty” or “not applicable.”

### VCS-020-H06 — BFT “secret scanners” are not part of the reviewed baseline

Section 6.2 says BFT secret scanners take precedence. The reviewed BFT tree has governed path rules and metadata/content detectors, but I did not find a credential/secret-content scanning feature. Tests using filenames such as `secret/**` demonstrate rule matching, not secret detection.

Remove the claim or bind it to a separately specified and tested BFT capability. The VCS integration must not rely on a protection that does not currently exist.

### VCS-020-H07 — The acceptance matrix remains too narrow for freeze

Add conformance cases for:

- API/CLI byte/semantic parity and schema rejection fixtures;
- no upstream, stale upstream, ahead/behind combinations, and no-fetch proof;
- exact/nearest/multiple tags;
- conflicts, ignored paths, staged-plus-unstaged paths, deletion, rename, binary and mode changes;
- bad/hostile refs and unusual filenames;
- bare, linked-worktree, shallow, and submodule cases or explicit unsupported results;
- deterministic repeated output and ordering;
- permission errors, cancellation, output limits, malformed provider results, and hostile environment/configuration;
- JSON stdout/stderr purity; and
- end-to-end `pyprojectmgr`, BFT selection reconciliation, and EDSS/EDSM/EDV privacy-root enforcement.

“100% test pass” is not an acceptance definition unless the required test inventory and its expected evidence are frozen.

## Project-alignment conclusions

### `pyprojectmgr`

The move to `governance.repository_policy` and the explicit five-pillar invariance are correct. The current metaschema permits additional governance properties in the relevant profiles, so merely adding the key may be accepted without meaningfully validating it. Phase 2 must add a versioned repository-policy schema/binding, migration behavior, canonical defaults, and QTC evidence rules rather than rely on permissive acceptance.

The example policy must also be corrected: `require_repository=false` with `require_clean=true` needs an explicit not-applicable/warning rule or should be rejected as incoherent.

### Bundle File Tool

The three selection modes and safety precedence are well aligned. `filesystem` should remain the default, `tracked` should be an explicit opt-in intersection with BFT safety, and `repository-aware` should annotate the canonical BFT plan without replacing it. Final artifact reconciliation remains mandatory.

Portable provenance is not aligned until BFT defines a versioned transport for it. Also remove the unsupported secret-scanner claim.

### PyThermX and NodeThermX

Non-repository `inspect` behavior now aligns with their inspected active roots. Each consumer still needs an explicit profile defining whether absence, cleanliness, branch, and provenance are applicable. A default `validate` policy that requires a repository should not be silently applied to these products.

### EDSS / EDSM / EDV

The privacy intent is correct but needs enforceable project-root allowlisting and portable-field projection. The tool must never traverse or list case/vault trees simply because they are located under or near a repository root. Source provenance and client data must remain separate authorities and storage domains.

## Required v0.2.1 changes before ratification

1. Publish the five named normative schemas plus a complete `diff-summary` schema, or defer `diff-summary`.
2. Choose only `src/vcs_tool`, `python -m vcs_tool`, and `vcs-tool`; add packaging, ownership, Git-version, and offline-delivery rules.
3. Replace contradictory boolean validation semantics with explicit rule dispositions and dependency validation.
4. Replace the `list-files` single-status model with separate index/worktree/conflict fields and deterministic path rules.
5. Define remaining repository states, provider capabilities, nullability, tag/upstream semantics, and no-fetch claims.
6. Make JSON mode emit exactly one structured document on its designated stream for every outcome.
7. Specify exact process security, configuration, timeout, cancellation, output-bound, path, and ref behavior.
8. Remove or defer BFT bundle provenance until a BFT transport version serializes it; remove the unsupported secret-scanner claim.
9. Reconcile `root_dir`, remote URL, logs, portable provenance, and EDSS/EDSM/EDV privacy projections.
10. Expand the conformance matrix and freeze expected evidence, not merely a pass percentage.

## Recommended team disposition and assignments

| Owner | Immediate assignment | Exit evidence |
|---|---|---|
| George | Issue v0.2.1 resolving the five blockers and normative ownership boundaries | Revised specification with no “or” layouts or semantic contradictions |
| Paul | Draft schema field/nullability tables, policy dependency rules, and the cross-project privacy projection | Traceability matrix from all findings to clauses and tests |
| John | Do not start the provider implementation yet; prepare executable command/test prototypes only after schemas stabilize | Reviewed command matrix and contract fixtures, with no host integration |
| Ringo | Confirm portable provenance fields, consumer defaults, and whether `diff-summary` remains Phase 1 scope | Product decision record |

## Final recommendation

Record **Conditional Approval of v0.2.0's architecture** and **Return for Contract Repair**. The revision has removed the original scope hazards and has responded substantively to the prior review. It is now close to a freeze candidate, but freezing examples as if they were schemas would transfer ambiguity directly into code and host integrations.

Approve Phase 1 only after v0.2.1 supplies normative schemas, one package identity, coherent validation and file-state semantics, pure machine streams, enforceable security/privacy rules, and a complete conformance inventory. BFT provenance should remain disabled until BFT itself has a versioned transport capable of preserving it.

**Paul**  
Lead Analyst / Collaborative Developer
