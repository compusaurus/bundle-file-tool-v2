# SPEC-VCS-001 v0.2.2 Data and Policy Contracts

**Document reference:** `SPEC-VCS-001-DATA` — Version 0.2.2 Draft  
**Architecture:** `DRAFT_SPEC-VCS-001_v0.2.2_Repository_Support_Specification.md`  
**Date:** August 31, 2026  
**Status:** **Candidate Contract — Machine Schemas and Fixtures Not Yet Frozen**  
**Normative terms:** `MUST`, `MUST NOT`, `SHOULD`, and `MAY` express proposed requirements pending ratification

---

## 1. Purpose and authority

This document defines the logical data, policy, nullability, ordering, and serialization contracts for `vcs_tool` v1. It exists to keep operation semantics out of ad hoc dataclasses and CLI code.

The tables and examples below are the design source for the machine-readable Draft 2020-12 JSON Schema artifacts. The `.json` files become normative only when they are committed, packaged, validated, hashed, and recorded as `CONTRACT_FROZEN` in `DRAFT_SPEC-VCS-001_v0.2.2_Conformance_Gate_and_Evidence_Register.md`.

No Markdown code block, hosted URL, or generated documentation page by itself constitutes a frozen schema.

---

## 2. Schema registry and versioning

### 2.1 Required v1 schema artifacts

| Schema | Canonical `$id` | Purpose |
|---|---|---|
| `vcs_common_v1.json` | `https://specs.equitable.dev/schemas/vcs/vcs_common_v1.json` | Common envelope, capabilities, warnings, paths, object IDs, extensions |
| `vcs_status_v1.json` | `https://specs.equitable.dev/schemas/vcs/vcs_status_v1.json` | Local diagnostic `inspect` result |
| `vcs_files_v1.json` | `https://specs.equitable.dev/schemas/vcs/vcs_files_v1.json` | JSON `list-files` result |
| `vcs_validate_v1.json` | `https://specs.equitable.dev/schemas/vcs/vcs_validate_v1.json` | Validation result and findings |
| `vcs_diff_summary_v1.json` | `https://specs.equitable.dev/schemas/vcs/vcs_diff_summary_v1.json` | Diff request/result representation |
| `vcs_error_v1.json` | `https://specs.equitable.dev/schemas/vcs/vcs_error_v1.json` | Structured non-policy failures |
| `vcs_policy_v1.json` | `https://specs.equitable.dev/schemas/vcs/vcs_policy_v1.json` | Caller policy input |
| `vcs_portable_provenance_v1.json` | `https://specs.equitable.dev/schemas/vcs/vcs_portable_provenance_v1.json` | Portable repository provenance projection |

### 2.2 Version rules

- Schema `$id` filenames are stable within major version 1.
- Every instance `schema_id` MUST be a `const` equal to the applicable `$id`.
- `schema_version` MUST be exactly `1.0.0` for the initial v1 schemas.
- Additive compatible behavior uses the explicit `extensions` object or a minor schema version only when older validators remain safe.
- A new required field, changed meaning, removed enum member, or narrowed accepted value requires a new schema major version.
- Executable and specification versions do not determine schema compatibility by equality.

### 2.3 Closure strategy

All top-level objects and governed nested objects MUST reject unknown properties. Draft 2020-12 schemas using shared `$defs` SHOULD use `unevaluatedProperties: false` after composition so common-envelope fields are not accidentally reopened.

Forward extensions appear only under:

```json
{
  "extensions": {
    "vendor-or-domain-key": {}
  }
}
```

Hosts MUST ignore unknown extension keys and MUST NOT treat them as evidence of a standard capability or policy result.

---

## 3. Canonical JSON and comparison rules

### 3.1 Encoding

- UTF-8, no BOM.
- Exactly one JSON document followed by exactly one LF byte.
- Compact separators: `,` and `:` without optional spaces.
- Object keys sorted by Unicode code-point order, equivalent to Python `json.dumps(..., sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)` for the permitted value domain.
- No floats, NaN, Infinity, duplicate keys, comments, or trailing commas.
- Control characters use JSON escaping. `/` is not escaped.

### 3.2 Deterministic arrays

| Array | Ordering rule |
|---|---|
| Capabilities represented as keys | Canonical object-key ordering |
| Warnings | Emission order by command stage, then warning code |
| Exact tags | Unsigned UTF-8 byte order |
| Files | Normalized current path, then normalized original path; unsigned UTF-8 bytes |
| Validation findings | Frozen rule order in Section 7.3 |
| Diff file summaries | Current path, original path, change type; unsigned UTF-8 bytes |

When an array is semantically ordered, the producer MUST construct the order before serialization. Serializer key sorting does not sort arrays.

### 3.3 Paths

Repository-relative path fields:

- use `/` separators on every platform;
- are relative to the canonical repository root;
- do not begin with `/`;
- do not contain an empty, `.`, or `..` segment;
- preserve filename case and Unicode code points as reported by the provider;
- are not Unicode-normalized by the tool; and
- MUST be valid UTF-8 for JSON/text output.

A provider encountering a path that cannot be represented as valid UTF-8 returns `VCS_PATH_ENCODING_UNSUPPORTED` rather than lossy replacement. NUL mode does not create a broader support claim than the Python path model.

### 3.4 Identity and display values

Full object IDs are identity values. Short object IDs are display values only. A cache key, signature input, policy comparison, or provenance identity MUST NOT use `short_sha`.

---

## 4. Standard result envelope

Every success, validation, portable-provenance, and error JSON result includes these fields. Operation schemas may add fields but may not redefine their meaning.

| Field | Type | Required | Rule |
|---|---|---:|---|
| `schema_id` | string/URI | Yes | `const` equal to the applicable schema `$id` |
| `schema_version` | string | Yes | Exact schema semantic version |
| `tool_version` | string | Yes | Installed distribution version; semantic-version pattern |
| `operation` | enum | Yes | `inspect`, `list_files`, `validate`, or `diff_summary`; errors identify attempted operation or `startup` |
| `provider_id` | string or null | Yes | `git_cli`, `mock`, future registered ID, or null before selection |
| `provider_version` | string or null | Yes | Sanitized provider version or null before discovery |
| `capabilities` | object | Yes | All required v1 capability keys, each boolean; empty only before provider selection |
| `warnings` | array | Yes | Structured warnings; empty array when none |
| `extensions` | object | Yes | Versioned extension container; empty object by default |

### 4.1 Capability object

The object is closed for the initial v1 schema and contains:

```text
inspect: boolean
list_files: boolean
validate: boolean
diff_summary: boolean
ignored_detection: boolean
rename_detection: boolean
submodule_status: boolean
sha256_object_format: boolean
local_tracking_diff: boolean
```

Future standard capabilities require a compatible schema update. Vendor experimentation belongs under `extensions.capabilities` and is never interpreted as a standard capability.

### 4.2 Warning object

| Field | Type | Required | Rule |
|---|---|---:|---|
| `code` | string | Yes | Stable `VCS_WARN_*` identifier |
| `message` | string | Yes | Sanitized human-readable summary |
| `details` | object | Yes | Closed or operation-defined detail object; no secrets/local paths in portable projection |

Warnings do not change the process exit code unless a policy rule translates observed state into a `FAIL` finding.

---

## 5. Local `inspect` result

### 5.1 Top-level fields

In addition to the standard envelope, `vcs_status_v1` contains:

| Field | Type | Required | Non-repository value |
|---|---|---:|---|
| `projection` | const `local_diagnostic` | Yes | `local_diagnostic` |
| `requested_dir` | absolute string | Yes | Resolved requested directory |
| `is_repository` | boolean | Yes | `false` |
| `root_dir` | absolute string or null | Yes | `null` |
| `repository_kind` | `worktree`, `bare`, or `none` | Yes | `none` |
| `object_format` | `sha1`, `sha256`, or null | Yes | `null` |
| `head` | object or null | Yes | `null` |
| `tags` | object or null | Yes | `null` |
| `worktree` | object or null | Yes | `null` |
| `upstream` | object or null | Yes | `null` |

The invariant is:

```text
is_repository == false
  <=> root_dir, object_format, head, tags, worktree, upstream are null
      and repository_kind == "none"
```

For a bare repository, `is_repository=true`, `repository_kind=bare`, and `worktree=null`.

### 5.2 HEAD object

| Field | Type | Rule |
|---|---|---|
| `commit_sha` | string or null | Null only for unborn HEAD; lowercase full object ID |
| `short_sha` | string or null | Null with `commit_sha`; 7–16 lowercase hex characters; display-only |
| `branch` | string or null | Short branch name; null when detached |
| `is_detached` | boolean | True only when HEAD is not attached to a branch and is not unborn |
| `is_unborn` | boolean | True when HEAD has no commit |
| `is_shallow` | boolean | Repository shallow state |
| `linked_worktree` | boolean | True when this is a linked worktree |

Conditional object-ID validation uses top-level `object_format`:

| Format | Full object ID |
|---|---|
| `sha1` | Exactly 40 lowercase hexadecimal characters |
| `sha256` | Exactly 64 lowercase hexadecimal characters |

### 5.3 Tags object

| Field | Type | Rule |
|---|---|---|
| `exact_tags` | array of strings | Every exact tag at HEAD, sorted; empty for no exact tag or unborn HEAD |
| `nearest_tag` | string or null | Provider-selected observational nearest tag |
| `distance` | non-negative integer or null | Null when no nearest tag or unborn HEAD |

If `nearest_tag` is null, `distance` MUST be null. Multiple exact tags do not require one to equal `nearest_tag`.

### 5.4 Worktree object

| Field | Type | Rule |
|---|---|---|
| `is_clean` | boolean or null | Derived by Section 6.1; null when a required dimension cannot be determined |
| `staged_count` | non-negative integer | Unique paths with index changes |
| `unstaged_count` | non-negative integer | Unique paths with tracked worktree changes |
| `untracked_count` | non-negative integer | Unique untracked file paths |
| `conflicted_count` | non-negative integer | Unique unmerged paths |
| `dirty_submodule_count` | non-negative integer | Supported dirty submodule paths |

One path may contribute to both staged and unstaged counts. Counts are not expected to sum to a unique total.

### 5.5 Upstream object

| Field | Type | Rule |
|---|---|---|
| `tracking_ref` | string | Full local tracking ref |
| `ahead_count` | non-negative integer | HEAD-only commits relative to local tracking ref |
| `behind_count` | non-negative integer | Tracking-ref-only commits relative to HEAD |
| `freshness` | const `not_checked` | Phase 1 never fetches |
| `remote_url` | sanitized string or null | Local diagnostic only; never contains credentials, query, or fragment |

`upstream=null` means no usable configured tracking ref. Equal zero counts are not equivalent to null.

---

## 6. Portable provenance result

Portable provenance uses its own schema and standard envelope. It is a projection, not a redaction performed by downstream hosts.

| Field | Type | Required | Rule |
|---|---|---:|---|
| `projection` | const `portable_provenance` | Yes | Projection identity |
| `is_repository` | boolean | Yes | Repository presence |
| `object_format` | enum or null | Yes | `sha1`, `sha256`, or null |
| `commit_sha` | string or null | Yes | Full ID only; null for non-repository/unborn |
| `branch` | string or null | Yes | Null when detached, unborn, or non-repository |
| `is_detached` | boolean or null | Yes | Null for non-repository |
| `is_unborn` | boolean or null | Yes | Null for non-repository |
| `exact_tags` | array | Yes | Sorted; empty when none/non-repository |
| `is_clean` | boolean or null | Yes | Null when no worktree/non-repository/unsupported determination |

The following fields are prohibited anywhere outside `extensions` and MUST also be rejected from standard extensions by policy:

```text
requested_dir
root_dir
username
hostname
remote_url
remote_host
organization
repository_path
timestamp
process_id
```

Portable repository identity has no timestamp. A build system MAY add a caller-controlled normalized build time in its own manifest layer. That time is not repository state and is excluded from any repository-identity digest.

The repository-identity digest, if a host needs one, is computed over the canonical JSON bytes of this allowlisted object only:

```text
is_repository
object_format
commit_sha
branch
is_detached
is_unborn
exact_tags
is_clean
```

Envelope/tool/provider metadata is evidence about production of the record but is excluded from that digest.

---

## 7. Policy input and validation result

### 7.1 Policy input

`vcs_policy_v1` is a closed object:

| Field | Type | Required | Rule |
|---|---|---:|---|
| `schema_id` | const URI | Yes | Policy schema `$id` |
| `schema_version` | const `1.0.0` | Yes | Policy schema version |
| `policy_id` | string | Yes | Stable host-controlled identifier, 1–128 characters |
| `rules` | object | Yes | Exactly the registered v1 rule keys |
| `extensions` | object | Yes | Empty by default |

Each rule contains:

| Field | Type | Required | Rule |
|---|---|---:|---|
| `enabled` | boolean | Yes | Disabled rules return `SKIPPED` |
| `disposition` | `allow`, `warn`, or `fail` | Yes | Effect when the rule condition is violated |
| `parameters` | object | Yes | Rule-specific, closed, empty when no parameters |

### 7.2 Registered rules

| Rule ID | Violation condition | Parameters |
|---|---|---|
| `VCS_RULE_REPOSITORY_REQUIRED` | Target is not a repository | None |
| `VCS_RULE_CLEAN_WORKTREE` | Worktree `is_clean` is false or null | None |
| `VCS_RULE_ALLOWED_BRANCH` | Attached branch matches none of the patterns | `patterns`: non-empty unique array |
| `VCS_RULE_NO_DETACHED_HEAD` | HEAD is detached | None |
| `VCS_RULE_EXACT_TAG_REQUIRED` | HEAD has no exact tag | None |
| `VCS_RULE_TRACKING_REF_EQUAL` | No upstream or local ahead/behind is nonzero | `missing_upstream_is_violation`: boolean |

An invalid pattern, unknown parameter, duplicate pattern, empty required pattern list, or unknown rule is a policy schema/usage error before repository evaluation.

### 7.3 Frozen evaluation order

```text
1. VCS_RULE_REPOSITORY_REQUIRED
2. VCS_RULE_CLEAN_WORKTREE
3. VCS_RULE_ALLOWED_BRANCH
4. VCS_RULE_NO_DETACHED_HEAD
5. VCS_RULE_EXACT_TAG_REQUIRED
6. VCS_RULE_TRACKING_REF_EQUAL
```

If repository state is absent and repository-required disposition permits execution, rules 2–6 return `NOT_APPLICABLE`. If repository-required itself is disabled, it returns `SKIPPED` and rules 2–6 still return `NOT_APPLICABLE`.

### 7.4 Finding outcome

| State | Outcome |
|---|---|
| Rule disabled | `SKIPPED` |
| Required prerequisite absent | `NOT_APPLICABLE` |
| Condition satisfied | `PASS` |
| Condition violated, disposition `allow` | `PASS` with reason `VCS_RULE_ALLOWED_BY_POLICY` |
| Condition violated, disposition `warn` | `WARN` |
| Condition violated, disposition `fail` | `FAIL` |

### 7.5 Validation result

In addition to the standard envelope:

| Field | Type | Required | Invariant |
|---|---|---:|---|
| `policy_id` | string | Yes | Echoes validated policy ID |
| `passed` | boolean | Yes | True iff no finding is `FAIL` |
| `violation_count` | non-negative integer | Yes | Count of `FAIL` |
| `warning_count` | non-negative integer | Yes | Count of `WARN` |
| `not_applicable_count` | non-negative integer | Yes | Count of `NOT_APPLICABLE` |
| `skipped_count` | non-negative integer | Yes | Count of `SKIPPED` |
| `findings` | array | Yes | One per registered rule, in frozen order |

Each finding contains:

```text
rule_id
disposition
outcome: PASS | FAIL | WARN | NOT_APPLICABLE | SKIPPED
reason_id
message
observed
```

`observed` is a closed rule-specific object. It MUST NOT contain an absolute path or remote identifier when serialized for portable evidence.

---

## 8. File-list result

### 8.1 Result fields

In addition to the standard envelope:

| Field | Type | Rule |
|---|---|---|
| `root_dir` | absolute string | Local JSON operation only |
| `include_tracked` | boolean | Effective selection option |
| `include_untracked` | boolean | Effective selection option |
| `include_ignored` | boolean | Effective selection option |
| `total_count` | non-negative integer | Equals `len(files)` |
| `files` | array | Unique normalized paths in canonical order |

### 8.2 File entry

| Field | Type | Rule |
|---|---|---|
| `path` | repository-relative string | Current path |
| `original_path` | string or null | Required non-null for rename; null otherwise |
| `index_status` | enum | Index dimension |
| `worktree_status` | enum | Worktree dimension |
| `conflict_status` | enum | Unmerged state or `none` |
| `is_tracked` | boolean | Tracked by index/history |
| `is_untracked` | boolean | Exactly one of untracked/ignored may be true |
| `is_ignored` | boolean | Ignored and untracked are distinct |
| `submodule` | object or null | Supported submodule status |

### 8.3 Status enums

`index_status`:

```text
none
unmodified
added
modified
deleted
renamed
type_changed
unmerged
```

`worktree_status`:

```text
none
unmodified
modified
deleted
type_changed
untracked
ignored
unmerged
```

`conflict_status` maps all Git unmerged XY states:

| Enum | Git code |
|---|---|
| `none` | Not unmerged |
| `both_deleted` | `DD` |
| `added_by_us` | `AU` |
| `deleted_by_them` | `UD` |
| `added_by_them` | `UA` |
| `deleted_by_us` | `DU` |
| `both_added` | `AA` |
| `both_modified` | `UU` |

### 8.4 Boolean invariants

```text
is_untracked => !is_tracked && !is_ignored && worktree_status == "untracked"
is_ignored   => !is_tracked && !is_untracked && worktree_status == "ignored"
conflict_status != "none" => index_status == "unmerged" && worktree_status == "unmerged"
index_status == "renamed" => original_path != null
index_status != "renamed" => original_path == null
```

### 8.5 Submodule object

| Field | Type | Rule |
|---|---|---|
| `head_changed` | boolean | Recorded gitlink differs from checked-out submodule HEAD |
| `modified_content` | boolean | Tracked content dirty inside submodule |
| `untracked_content` | boolean | Untracked content exists inside submodule |

If the provider cannot determine a requested submodule dimension, it MUST return a warning and MUST NOT assert a definitive clean state.

---

## 9. Diff request and result

### 9.1 Endpoint

| Field | Type | Rule |
|---|---|---|
| `kind` | `ref`, `index`, or `worktree` | Endpoint type |
| `ref` | string or null | Required for `ref`; null otherwise |
| `resolved_object_id` | string or null | Present in result for `ref`; never accepted from caller as authority |

Supported pairs are those listed in the architecture. Other pairs return usage error before provider execution.

### 9.2 Result fields

In addition to the standard envelope:

| Field | Type | Rule |
|---|---|---|
| `base` | endpoint object | Includes resolved object ID for refs |
| `target` | endpoint object | Includes resolved object ID for refs |
| `files_changed` | non-negative integer | Equals `len(file_summaries)` |
| `insertions` | non-negative integer | Sum of non-null text insertion counts |
| `deletions` | non-negative integer | Sum of non-null text deletion counts |
| `binary_files_changed` | non-negative integer | Count where `is_binary=true` |
| `untracked_files_included` | const false | Phase 1 invariant |
| `file_summaries` | array | Unique canonical order |

### 9.3 File summary

| Field | Type | Rule |
|---|---|---|
| `path` | repository-relative string | Current path |
| `original_path` | string or null | Non-null for rename/copy only |
| `change_type` | enum | `modified`, `added`, `deleted`, `renamed`, `copied`, `type_changed` |
| `insertions` | non-negative integer or null | Null iff binary |
| `deletions` | non-negative integer or null | Null iff binary |
| `is_binary` | boolean | Controls count nullability |

Required invariants:

```text
is_binary == true  => insertions == null && deletions == null
is_binary == false => insertions >= 0 && deletions >= 0
change_type in {"renamed", "copied"} => original_path != null
change_type not in {"renamed", "copied"} => original_path == null
```

Rename/copy detection uses the threshold frozen in the Git provider profile. Changes in that threshold are observable contract changes.

---

## 10. Error result

`vcs_error_v1` includes the standard envelope plus:

| Field | Type | Rule |
|---|---|---|
| `error_code` | string | Stable `VCS_*` identifier |
| `error_class` | enum | Category below |
| `message` | string | Sanitized; no raw Git command or secrets |
| `retryable` | boolean | Whether identical request may succeed after external state changes |
| `details` | object | Closed per error code; allowlisted fields only |

Error classes:

```text
usage
environment
repository
io
privacy
reference
capability
timeout
resource
cancelled
internal
```

Stable error codes include at least:

```text
VCS_USAGE_INVALID_ARGUMENT
VCS_PATH_NOT_FOUND
VCS_PATH_NOT_DIRECTORY
VCS_POLICY_SCHEMA_INVALID
VCS_NOT_A_REPOSITORY
VCS_GIT_BINARY_MISSING
VCS_GIT_BINARY_UNSUPPORTED
VCS_PERMISSION_DENIED
VCS_PATH_ENCODING_UNSUPPORTED
VCS_PRIVACY_BOUNDARY_VIOLATION
VCS_REF_NOT_FOUND
VCS_REF_UNSAFE
VCS_CAPABILITY_UNSUPPORTED
VCS_REPOSITORY_STATE_UNSUPPORTED
VCS_TIMEOUT
VCS_OUTPUT_LIMIT
VCS_CANCELLED
VCS_PROVIDER_MALFORMED_OUTPUT
VCS_INTERNAL_ERROR
```

Raw command lines, environment blocks, unredacted stderr, remote credentials, absolute client-data paths, and tracebacks are prohibited from machine error output.

---

## 11. Canonical examples

### 11.1 Non-repository validation with allowed repository absence

```json
{
  "capabilities": {
    "diff_summary": true,
    "ignored_detection": true,
    "inspect": true,
    "list_files": true,
    "local_tracking_diff": true,
    "rename_detection": true,
    "sha256_object_format": false,
    "submodule_status": true,
    "validate": true
  },
  "extensions": {},
  "findings": [
    {
      "disposition": "allow",
      "message": "Repository presence is allowed by policy.",
      "observed": {"is_repository": false},
      "outcome": "PASS",
      "reason_id": "VCS_RULE_ALLOWED_BY_POLICY",
      "rule_id": "VCS_RULE_REPOSITORY_REQUIRED"
    },
    {
      "disposition": "fail",
      "message": "Clean-worktree evaluation requires a repository.",
      "observed": {"prerequisite": "repository"},
      "outcome": "NOT_APPLICABLE",
      "reason_id": "VCS_RULE_PREREQUISITE_ABSENT",
      "rule_id": "VCS_RULE_CLEAN_WORKTREE"
    },
    {
      "disposition": "fail",
      "message": "Allowed-branch evaluation requires a repository.",
      "observed": {"prerequisite": "repository"},
      "outcome": "NOT_APPLICABLE",
      "reason_id": "VCS_RULE_PREREQUISITE_ABSENT",
      "rule_id": "VCS_RULE_ALLOWED_BRANCH"
    },
    {
      "disposition": "fail",
      "message": "Detached-HEAD evaluation requires a repository.",
      "observed": {"prerequisite": "repository"},
      "outcome": "NOT_APPLICABLE",
      "reason_id": "VCS_RULE_PREREQUISITE_ABSENT",
      "rule_id": "VCS_RULE_NO_DETACHED_HEAD"
    },
    {
      "disposition": "fail",
      "message": "Exact-tag evaluation requires a repository.",
      "observed": {"prerequisite": "repository"},
      "outcome": "NOT_APPLICABLE",
      "reason_id": "VCS_RULE_PREREQUISITE_ABSENT",
      "rule_id": "VCS_RULE_EXACT_TAG_REQUIRED"
    },
    {
      "disposition": "fail",
      "message": "Tracking-ref evaluation requires a repository.",
      "observed": {"prerequisite": "repository"},
      "outcome": "NOT_APPLICABLE",
      "reason_id": "VCS_RULE_PREREQUISITE_ABSENT",
      "rule_id": "VCS_RULE_TRACKING_REF_EQUAL"
    }
  ],
  "not_applicable_count": 5,
  "operation": "validate",
  "passed": true,
  "policy_id": "pyprojectmgr-default",
  "provider_id": "git_cli",
  "provider_version": "git version 2.x",
  "schema_id": "https://specs.equitable.dev/schemas/vcs/vcs_validate_v1.json",
  "schema_version": "1.0.0",
  "skipped_count": 0,
  "tool_version": "0.2.2",
  "violation_count": 0,
  "warning_count": 0,
  "warnings": []
}
```

### 11.2 Binary rename diff entry

```json
{
  "change_type": "renamed",
  "deletions": null,
  "insertions": null,
  "is_binary": true,
  "original_path": "assets/old-logo.png",
  "path": "assets/new-logo.png"
}
```

### 11.3 Portable repository fields

```json
{
  "branch": "main",
  "commit_sha": "0123456789abcdef0123456789abcdef01234567",
  "exact_tags": ["v2.1.123"],
  "is_clean": true,
  "is_detached": false,
  "is_repository": true,
  "is_unborn": false,
  "object_format": "sha1"
}
```

No local path, remote, user, host, process, or timestamp field is permitted in the portable repository field set.

---

## 12. Machine-artifact acceptance requirements

Before this contract is frozen:

1. All eight `.json` files MUST parse as JSON and validate against Draft 2020-12 metaschema.
2. All `$ref` values MUST resolve from package resources without network access.
3. Every schema MUST have at least one positive fixture and negative fixtures for required fields, closed objects, enums, nullability, conditional invariants, ordering validators where applicable, and wrong `schema_id`.
4. Examples in this document MUST validate after envelope completion.
5. Source-tree, wheel, and sdist schema bytes MUST match recorded SHA-256 values.
6. The Python serializer, CLI JSON output, and frozen fixture bytes MUST agree where byte parity is claimed.
7. A schema compatibility test MUST prove that the executable does not silently emit fields rejected by the packaged schema.
8. The evidence register MUST identify the exact schema artifacts and reviewers.

---

## 13. Ratification conditions

This data contract becomes normative only when:

- George approves the field, nullability, enum, extension, and versioning model;
- John confirms implementation feasibility and supplies generated schema/fixture evidence;
- Paul accepts policy invariants, deterministic projections, privacy exclusions, and cross-product mapping;
- Ringo approves portable provenance content and host-policy defaults; and
- the corresponding gates are recorded `CONTRACT_FROZEN` with artifact hashes.

Until then, this document remains a candidate contract.

---

— **Version 0.2.2 Data Contract Draft for Team Review**
