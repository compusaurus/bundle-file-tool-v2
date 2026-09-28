# SPEC-VCS-001: Pluggable VCS and Repository Support Tool

**Document reference:** `SPEC-VCS-001` — Version 0.2.2 Draft  
**Prepared for:** Ringo — Product Owner; George — Lead Architect; John — Lead Developer; Paul — Lead Analyst / Collaborative Developer  
**Date:** August 31, 2026  
**Status:** **Freeze Candidate — Phase 0 Contract Work; Not Ratified for Implementation or Release**  
**Supersession:** Replaces v0.2.1 only after the approval record in the gate register reaches `CONTRACT_FROZEN`  
**Normative terms:** `MUST`, `MUST NOT`, `SHOULD`, and `MAY` express proposed requirements pending ratification

**Companion drafts:**

- `DRAFT_SPEC-VCS-001_v0.2.2_Data_and_Policy_Contracts.md`
- `DRAFT_SPEC-VCS-001_v0.2.2_Git_Provider_Security_and_Privacy_Profile.md`
- `DRAFT_SPEC-VCS-001_v0.2.2_Conformance_Gate_and_Evidence_Register.md`

---

## 1. Executive decision

Version 0.2.2 adopts the following architecture:

1. `vcs_tool` is a standalone, standard-library-first Python package with one import, module, and console surface.
2. Phase 1 supports local, read-only Git inspection through a hardened CLI provider; it performs no clone, fetch, pull, push, checkout, reset, commit, tag, merge, rebase, or credential operation.
3. Repository absence is a successful `inspect` result. Operations that intrinsically require a repository return a typed repository error.
4. Public operations are `inspect`, `list-files`, `validate`, and `diff-summary`.
5. Domain models are immutable typed values. JSON, text, and NUL are serializers over those values, not independent implementations.
6. Machine contracts are versioned separately from the document and executable. Schema artifacts, examples, fixtures, hashes, and named approval—not prose—close Phase 0.
7. Validation evaluates all enabled rules and returns deterministic findings with explicit `PASS`, `FAIL`, `WARN`, `NOT_APPLICABLE`, or `SKIPPED` outcomes.
8. BFT remains the authority for bundle selection, exclusions, safety rules, and artifact reconciliation. Repository state may filter or annotate a BFT plan but never bypass BFT safety.
9. Repository governance remains QTC evidence in `pyprojectmgr`; it does not become a sixth Pentagon integrity pillar.
10. Portable provenance is a separate privacy projection. It excludes local paths, users, remotes, and uncontrolled timestamps.
11. Source-code repository roots and matrimonial/client-data roots are separate security authorities. Canonical root containment is the primary isolation control.
12. A document author cannot self-declare `CONTRACT_FROZEN`, `IMPLEMENTED`, or `EVIDENCE_ACCEPTED`.

This draft authorizes contract review and a disposable provider risk spike. It does not authorize a stable v1 release or Phase 2/3 host integration.

---

## 2. Scope and non-scope

### 2.1 Phase 1 scope

- identify whether an explicitly bounded directory belongs to a supported local Git repository;
- inspect repository identity, HEAD, branch, tag, worktree, and locally cached upstream state;
- enumerate tracked, changed, untracked, ignored, renamed, conflicted, type-changed, and supported submodule states;
- evaluate caller-supplied repository policy without modifying the repository;
- summarize file and line changes between supported endpoint pairs;
- expose Python, console, JSON, text, and NUL interfaces as defined by operation;
- produce local diagnostic and portable provenance projections;
- suppress interactive prompts, helpers, pagers, external diff/text conversion, and network behavior;
- enforce bounded time, bounded output, cancellation, path containment, and typed failures; and
- supply deterministic fixtures and conformance evidence.

### 2.2 Explicitly outside Phase 1

- repository creation or initialization;
- network discovery or synchronization;
- clone, fetch, pull, push, credential, SSH-agent, or remote API behavior;
- checkout, switch, reset, restore, clean, commit, amend, merge, rebase, cherry-pick, tag creation, stash, worktree creation, or submodule update;
- patch creation or application;
- archive, snapshot, bundle, or delta artifact generation;
- artifact signing, attestation, or provenance authentication;
- serialized BFT bundle provenance before a BFT-owned transport RFC is ratified;
- Mercurial, Subversion, hosted-provider APIs, or native Git libraries in Phase 1;
- recursive repository discovery outside the caller-approved root boundary; and
- traversal of client case, vault, evidence, or matrimonial data roots.

### 2.3 Honest capability claims

The tool reports only local state visible to the installed Git binary and filesystem. Ahead/behind means comparison with locally cached tracking refs. It does not mean the repository is synchronized with a remote service. A clean worktree does not prove a trusted build, complete provenance, or an authentic release.

---

## 3. Package, ownership, and delivery boundary

### 3.1 Canonical package layout

```text
src/vcs_tool/
  __init__.py
  __main__.py
  api.py
  cli.py
  models.py
  serializers.py
  policy.py
  errors.py
  security.py
  providers/
    __init__.py
    base.py
    git_cli.py
    mock_provider.py
  schemas/
    vcs_common_v1.json
    vcs_status_v1.json
    vcs_files_v1.json
    vcs_validate_v1.json
    vcs_diff_summary_v1.json
    vcs_error_v1.json
    vcs_policy_v1.json
    vcs_portable_provenance_v1.json
```

There is no `tools.vcs_tool` compatibility package in v1.

### 3.2 Public identity

| Concern | Contract |
|---|---|
| Distribution name | `vcs-tool` |
| Import package | `vcs_tool` |
| Console script | `vcs-tool = vcs_tool.cli:main` |
| Module invocation | `python -m vcs_tool` |
| Python support | 3.11, 3.12, and 3.13 |
| Git baseline | Git 2.25 or later; capabilities may further restrict repository formats/features |
| Required runtime dependencies | Python standard library only |
| Version source | `vcs_tool.__version__`, populated from package metadata by one build-time source |
| Schema access | Package resources; no network required |

The implementation repository MUST define the license, wheel and sdist inclusion rules, supported platform profiles, and offline installation procedure before release.

### 3.3 Accountable roles

| Authority | Accountable role |
|---|---|
| Product scope and cross-product policy | Ringo |
| Architecture and schema boundary | George |
| Reference implementation and provider evidence | John |
| Contract, traceability, privacy, and integration review | Paul |

Role assignments do not substitute for the named approvals in the evidence register.

---

## 4. Architecture and provider model

### 4.1 Public façade

```python
tool = VcsTool(
    root=project_root,
    provider="git_cli",
    allowed_roots=(project_root,),
    denied_roots=(),
    timeout_seconds=10.0,
    max_output_bytes=10_485_760,
)
```

`root` is the requested project directory. It MUST exist and resolve to a directory before provider execution. API hosts MUST provide explicit `allowed_roots`. The CLI treats the resolved `--path` value as its default allowed boundary.

The provider MAY discover a repository root above `root` only when that root remains within an explicitly supplied allowed boundary. It MUST NOT cross a denied root or infer upward beyond that boundary.

### 4.2 Provider interface

```python
class IVcsProvider(Protocol):
    provider_id: str
    provider_version: str | None

    def capabilities(self) -> VcsCapabilities: ...
    def inspect(self) -> VcsStatusResult: ...
    def list_files(self, options: VcsFileListOptions) -> VcsFileListResult: ...
    def diff_summary(self, request: VcsDiffRequest) -> VcsDiffSummaryResult: ...
```

Policy validation is provider-independent and evaluates typed inspection/file results. Providers MUST NOT define different policy meanings.

### 4.3 Phase 1 providers

| Provider | Purpose | Status |
|---|---|---|
| `git_cli` | Hardened local Git provider | Phase 1 reference implementation |
| `mock` | Deterministic models, failures, and contract fixtures | Required for conformance |
| `pygit2`, `hg_cli`, remote providers | Future capability profiles | Deferred |

### 4.4 Capability model

Every result and error carries a capability object. Required v1 capability keys are:

```text
inspect
list_files
validate
diff_summary
ignored_detection
rename_detection
submodule_status
sha256_object_format
local_tracking_diff
```

A capability value means the provider can execute the named behavior under its current platform and repository profile. `false` means unsupported, not empty and not applicable. Calling an unsupported operation returns `VCS_CAPABILITY_UNSUPPORTED`.

Unknown future capability keys MAY appear only through the common schema's versioned extension rule. Hosts MUST ignore unknown extension capabilities and MUST NOT infer support from provider identity.

---

## 5. Public operations

The logical data contracts, field invariants, policy model, and canonical examples are defined in `DRAFT_SPEC-VCS-001_v0.2.2_Data_and_Policy_Contracts.md`.

### 5.1 `inspect`

#### Python API

```python
status = tool.inspect()
portable = tool.project_portable_provenance(status)
```

#### CLI

```text
vcs-tool inspect [--path DIR] [--projection local|portable] [--format json|text]
```

#### Semantics

- Missing or invalid paths are usage failures.
- A valid non-repository directory returns exit 0 with `is_repository=false`.
- Local projection may include resolved local paths and a sanitized remote URL.
- Portable projection uses `vcs_portable_provenance_v1.json` and excludes local paths, usernames, remote data, and timestamps.
- Detached and unborn HEAD are represented explicitly.
- Multiple exact tags are returned as a sorted array.
- Upstream counts use local tracking refs only and include an explicit freshness value of `not_checked`.
- Bare, linked-worktree, shallow, submodule, and object-format state are represented or rejected with a typed unsupported result.

### 5.2 `list-files`

#### Python API

```python
result = tool.list_files(
    VcsFileListOptions(
        include_tracked=True,
        include_untracked=False,
        include_ignored=False,
    )
)
```

#### CLI

```text
vcs-tool list-files [--path DIR] [--tracked] [--untracked] [--ignored] [--format json|nul|text]
```

#### Semantics

- The operation requires a supported non-bare repository.
- If no inclusion flag is supplied, `--tracked` is the default.
- JSON represents index, worktree, conflict, rename, type-change, and submodule state independently. Copy identity is a diff inference, not an index state.
- Every path is repository-relative, uses `/`, contains no `.` or `..` segment, and is returned once.
- Output order is the unsigned UTF-8 byte ordering of the normalized current path, then original path.
- Ignored directories are expanded to files; an aggregate directory placeholder is not a file result.
- NUL mode is a deterministic path-only projection. It emits each selected path followed by one NUL byte and emits zero bytes for an empty result.
- NUL mode does not claim status-model parity with JSON.

### 5.3 `validate`

#### Python API

```python
result = tool.validate(policy)
```

#### CLI

```text
vcs-tool validate [--path DIR] --policy FILE [--format json|text]
```

#### Semantics

- The policy file MUST validate against `vcs_policy_v1.json` before repository evaluation.
- All enabled rules are evaluated in the frozen rule order.
- A rule whose repository prerequisite is absent returns `NOT_APPLICABLE`; it does not create a false violation.
- A disabled rule returns `SKIPPED`.
- A violated rule with disposition `allow`, `warn`, or `fail` returns `PASS`, `WARN`, or `FAIL`, respectively, with a stable reason ID and observed-state details.
- Overall `passed` is true if and only if no finding has outcome `FAIL`.
- Exit 1 means a completed validation with one or more policy failures; it is not a process error.

### 5.4 `diff-summary`

#### Python API

```python
result = tool.diff_summary(
    VcsDiffRequest(
        base=VcsDiffEndpoint.ref("HEAD"),
        target=VcsDiffEndpoint.worktree(),
    )
)
```

#### CLI

```text
vcs-tool diff-summary [--path DIR] (--base REF | --base-index) (--target REF | --target-index | --target-worktree) [--format json|text]
```

#### Supported endpoint pairs

| Base | Target | Meaning |
|---|---|---|
| Ref | Ref | Committed tree to committed tree |
| Ref | Index | Committed tree to index/staging area |
| Ref | Worktree | Committed tree to index plus tracked worktree changes |
| Index | Worktree | Unstaged tracked worktree changes |

Untracked files are excluded from v1 diff summaries. They remain visible through `list-files`. User refs are resolved to full object IDs before diff execution and are never passed to a diff command as unresolved option-like values.

Binary file insertion/deletion counts are `null`. Aggregate line totals sum text-file counts only and report `binary_files_changed` separately. Rename/copy records require `original_path`.

---

## 6. Repository and policy semantics

### 6.1 Clean worktree

`is_clean=true` means all of the following are zero or false:

- staged changes;
- unstaged tracked changes;
- untracked files;
- conflicts; and
- dirty supported submodules.

Ignored files do not make the worktree dirty. Unsupported or unreadable submodule state produces `is_clean=null` and a structured warning. For `VCS_RULE_CLEAN_WORKTREE`, unknown clean state is a violated condition whose `allow`, `warn`, or `fail` disposition determines the finding outcome.

### 6.2 Tag semantics

- `exact_tags` contains every tag whose peeled target is HEAD, sorted by unsigned UTF-8 bytes.
- `nearest_tag` follows the frozen Git provider command profile and is observational.
- `distance` is the commit distance reported for the selected nearest tag.
- Exact-tag policy requires at least one entry in `exact_tags`; a nearest tag does not satisfy it.

### 6.3 Upstream semantics

- `tracking_ref` is the configured local tracking ref for the current attached branch.
- `ahead_count` and `behind_count` compare HEAD with that local ref.
- No command contacts a remote.
- `freshness=not_checked` is mandatory in Phase 1.
- Missing upstream is distinct from equal counts.

### 6.4 Branch pattern semantics

Allowed-branch patterns are case-sensitive and use Python `fnmatch.fnmatchcase` semantics over the complete short branch name. `*` may match `/`; `?` and bracket expressions are supported; brace expansion and extended globs are not. Invalid bracket syntax is rejected during policy validation.

### 6.5 Object identifiers

Results identify `object_format` as `sha1` or `sha256`. Full object IDs are lowercase hexadecimal and must have the length associated with the declared format. Short IDs are display-only, never used as identity, cache, signature, or policy keys.

---

## 7. Output, determinism, and failure contract

### 7.1 Machine output

- JSON is UTF-8 without BOM and contains exactly one document followed by one LF.
- Canonical JSON uses sorted object keys, compact separators, lowercase booleans/null, and no insignificant whitespace.
- Arrays with set semantics are sorted by their stated rule.
- Dynamic execution time, process IDs, hostnames, usernames, and absolute paths are excluded from portable output.
- Python/API parity means the canonical serializer applied to the typed API result produces the exact JSON bytes written by the CLI. The typed Python object is not itself a byte sequence.

### 7.2 Stream purity

In JSON mode:

- exit 0 writes exactly one success or validation-result document to `stdout` and zero bytes to `stderr`;
- exit 1 writes exactly one validation-result document to `stderr` and zero bytes to `stdout`;
- other non-zero exits write exactly one `vcs_error_v1` document to `stderr` and zero bytes to `stdout`; and
- tracebacks, log lines, progress messages, Git diagnostics, and prompts never appear on either machine stream.

Human diagnostics MAY be emitted only in text mode or to an explicitly configured separate log sink.

### 7.3 Exit codes

| Exit | Constant | Meaning |
|---:|---|---|
| 0 | `VCS_SUCCESS` | Operation completed successfully |
| 1 | `VCS_POLICY_VIOLATION` | Validation completed with one or more `FAIL` findings |
| 2 | `VCS_USAGE_ERROR` | Invalid syntax, path, option, or policy input |
| 10 | `VCS_NOT_A_REPOSITORY` | Operation requires a repository and none is available |
| 11 | `VCS_BINARY_MISSING` | Configured Git executable is unavailable |
| 12 | `VCS_BINARY_UNSUPPORTED` | Git version or executable identity does not meet the accepted profile |
| 20 | `VCS_IO_ERROR` | Permission, decoding, or local filesystem/provider I/O failure |
| 21 | `VCS_PRIVACY_BOUNDARY` | Requested or discovered path violates an allow/deny boundary |
| 30 | `VCS_REF_NOT_FOUND` | A requested ref does not resolve to an allowed object |
| 31 | `VCS_CAPABILITY_UNSUPPORTED` | Provider, repository, object format, or state is unsupported |
| 40 | `VCS_TIMEOUT` | Time bound exceeded |
| 41 | `VCS_OUTPUT_LIMIT` | Bounded output ceiling exceeded |
| 42 | `VCS_CANCELLED` | Caller or console cancellation completed safely |
| 50 | `VCS_INTERNAL_ERROR` | Unhandled implementation defect |

The error schema and provider profile define stable error codes, classes, details, and redaction.

---

## 8. Security, isolation, and privacy boundary

`DRAFT_SPEC-VCS-001_v0.2.2_Git_Provider_Security_and_Privacy_Profile.md` is normative for:

- executable resolution;
- environment construction;
- Git configuration and helper suppression;
- exact command families;
- ref resolution and path separation;
- time, output, cancellation, and child-process cleanup;
- decoding and unsupported path behavior;
- remote sanitization;
- allowed and denied root enforcement; and
- local, portable, and machine-log projections.

No provider may claim conformance by satisfying this document while violating that profile.

---

## 9. Host integration profiles

### 9.1 `pyprojectmgrV2`

- Repository policy is stored under `governance.repository_policy` and validates against `vcs_policy_v1.json` or a schema-bound equivalent.
- Repository results are QTC/preflight evidence and do not change the five-pillar Pentagon integrity digest.
- A non-repository project can pass when repository presence is allowed; dependent findings are `NOT_APPLICABLE`.
- Portable provenance is inserted only through the portable schema, never by copying the local diagnostic object.
- Any build time belongs to the build manifest, not repository identity.

### 9.2 Bundle File Tool

| Mode | Contract |
|---|---|
| `filesystem` | Existing BFT selection; VCS ignored; default |
| `tracked` | Intersect BFT's safe candidate plan with selected tracked repository paths |
| `repository-aware` | Preserve filesystem traversal and annotate candidates with repository state |

BFT hard-deny/exclusion rules, path safety, plan review, and plan-to-artifact reconciliation always take precedence. Tracking does not authorize inclusion. Ignored or untracked status does not authorize exclusion when the selected mode requires filesystem behavior.

VCS metadata remains in memory until a separate BFT transport RFC defines versioned serialization. This specification makes no claim that current bundle artifacts preserve provenance.

### 9.3 PyThermX and NodeThermX

Hosts without repositories use an explicit policy profile with `require_repository.disposition=allow`. Repository adoption is not implied by tool availability. Host onboarding records whether repository evidence is required, optional, warning-only, or not applicable.

### 9.4 EDSS / EDSM / EDV

- Source-code roots are explicitly allowlisted.
- Client case, vault, evidence, exports, and working-data roots are explicitly denied.
- The canonical discovered repository root must remain inside an allowed root and outside every denied root.
- Portable provenance contains no local/client path or remote identifier.
- `list-files` is treated as sensitive metadata access because filenames can disclose client information.

Name-pattern checks MAY supplement these controls but MUST NOT be the primary isolation boundary.

---

## 10. Staged implementation

### Gate 0 — Current: contract and evidence preparation

Required outputs:

- approved four-document draft set;
- eight machine-readable schemas and offline resolution rules;
- positive and negative fixtures;
- command/security matrix;
- repository-state and policy decision tables;
- expanded test inventory;
- package/release ownership rules; and
- named approval with document and artifact hashes.

### Phase 1A — Disposable Git provider spike

John MAY prototype exact Git command behavior, parsers, cancellation, and fixture repositories. Spike code is not a stable package and does not authorize host integration.

### Phase 1B — Reference implementation

After `CONTRACT_FROZEN`, implement `src/vcs_tool`, package schemas, and pass the source/wheel conformance suite on each claimed platform/runtime profile.

### Phase 2 — `pyprojectmgr` integration

Bind the policy schema into governance/QTC, add portable provenance to build manifests, and prove that the Pentagon remains unchanged.

### Phase 3 — BFT integration

Implement tracked and repository-aware selection, preserve BFT safety precedence, and prove plan-to-artifact reconciliation. Serialized provenance remains a separate BFT RFC.

---

## 11. Gate and approval governance

`DRAFT_SPEC-VCS-001_v0.2.2_Conformance_Gate_and_Evidence_Register.md` is the source of truth for status.

Allowed states are:

```text
PROPOSED
PARTIAL
CONTRACT_FROZEN
IMPLEMENTED
EVIDENCE_ACCEPTED
DEFERRED
REJECTED
```

No author may self-mark a gate `CONTRACT_FROZEN` or `EVIDENCE_ACCEPTED`. Every transition records artifact paths, versions and hashes, implementation revision when applicable, test results, owner, reviewers, approval date, retest date, residual risk, and exceptions.

---

## 12. Ratification checklist

Version 0.2.2 becomes the Phase 0 baseline only when:

- Ringo approves product scope, host defaults, privacy projections, and implementation sequence;
- George approves package, provider, state, schema, and integration boundaries;
- John accepts implementability of command templates, models, packaging, and conformance fixtures;
- Paul accepts traceability, policy semantics, BFT alignment, privacy isolation, and residual risk;
- all companion drafts agree on identifiers, fields, operations, failures, and gates;
- all eight schemas exist as valid package artifacts with frozen hashes and offline references;
- positive and negative examples validate as expected;
- every Gate 0 item is `CONTRACT_FROZEN`; and
- the approval record names the exact document and artifact revisions.

Until then, this document remains a freeze candidate.

---

— **Version 0.2.2 Draft for Team Review**
