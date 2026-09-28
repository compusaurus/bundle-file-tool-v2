# SPEC-VCS-001 v0.2.2 Conformance Gate and Evidence Register

**Document reference:** `SPEC-VCS-001-GATES` — Version 0.2.2 Draft  
**Architecture:** `DRAFT_SPEC-VCS-001_v0.2.2_Repository_Support_Specification.md`  
**Data contract:** `DRAFT_SPEC-VCS-001_v0.2.2_Data_and_Policy_Contracts.md`  
**Provider profile:** `DRAFT_SPEC-VCS-001_v0.2.2_Git_Provider_Security_and_Privacy_Profile.md`  
**Date:** August 31, 2026  
**Status:** **Draft Governance Register — No VCS Gate Is Yet Contract-Frozen or Evidence-Accepted**

---

## 1. Purpose

This register prevents a specification label, test count, or author assertion from being mistaken for a completed phase gate. It records the artifacts, tests, owners, reviewers, and residual risk required before the VCS contracts, implementation, or host integrations advance.

The initial state is conservative. Text present in the draft is evidence of design work, not proof that a machine contract exists or that an implementation conforms.

This register is the source of truth for the status of SPEC-VCS-001 Phase 0 through Phase 3.

---

## 2. Status model

| Status | Meaning |
|---|---|
| `PROPOSED` | Requirement or direction identified; normative contract is incomplete |
| `PARTIAL` | Material design exists, but artifacts, decisions, or evidence remain |
| `CONTRACT_FROZEN` | Exact versioned normative artifacts are approved; scoped implementation may begin |
| `IMPLEMENTED` | Reference implementation exists and required automated tests pass |
| `EVIDENCE_ACCEPTED` | Named reviewers accept tests, exercises, exceptions, and residual risk for a stated profile |
| `DEFERRED` | Explicitly outside the current slice with owner and revisit trigger |
| `REJECTED` | Proposal intentionally excluded with rationale |

Only `EVIDENCE_ACCEPTED` closes an implementation or integration gate for a named product, platform, Python runtime, Git profile, and package revision. Acceptance on Windows does not imply Linux/macOS acceptance; acceptance for BFT does not imply `pyprojectmgr` or matrimonial-system acceptance.

A document author cannot self-mark `CONTRACT_FROZEN`, `IMPLEMENTED`, or `EVIDENCE_ACCEPTED`.

---

## 3. Required evidence record

Every transition to `CONTRACT_FROZEN` or beyond records:

```text
evidence_id
gate_id(s)
scope:
  product/application
  operating system/platform profile
  Python version
  Git version/object-format profile
  package/source revision
status
artifact_paths_or_uris
artifact_versions_and_sha256
implementation_revision
test_command_and_result
fixture_revision
exercise_or_manual_review_result
owner
reviewers
approval_date
retest_or_expiry_date
residual_risk
exceptions_and_compensating_controls
```

An evidence record without artifact hashes, scope, result, owner, and reviewer is incomplete.

---

## 4. Gate register

| Gate | Priority | Initial status | Accountable owner | Contract/evidence required before acceptance |
|---|---|---|---|---|
| **VCS-G01** Scope, package, and ownership | Blocker | `PARTIAL` | Ringo + George | Approved scope/non-scope; exact package/import/CLI; license; version source; release owner; offline delivery; supersession record |
| **VCS-G02** Schema and common envelope | Blocker | `PARTIAL` | George + Paul | Eight valid packaged schemas; offline `$ref`; const schema IDs; closed objects; fixtures; source/wheel hashes; compatibility evidence |
| **VCS-G03** Inspect and repository-state semantics | Blocker | `PARTIAL` | George + John | State/nullability decision table; non-repo, unborn, detached, shallow, bare, linked worktree, upstream, tags, SHA-1/SHA-256 or typed unsupported evidence |
| **VCS-G04** Two-dimensional file inventory | Blocker | `PARTIAL` | John + Paul | Complete porcelain-v2 mapping; all unmerged states; rename/type/submodule rules; unique paths; ordering; NUL behavior; malformed-output tests |
| **VCS-G05** Policy and validation | Blocker | `PARTIAL` | George + Paul | Policy schema; pattern grammar; dependency rules; all five outcomes; count invariants; exact exit/stream behavior; `pyprojectmgr` default decision |
| **VCS-G06** Diff summary | Blocker | `PARTIAL` | George + John | Endpoint model; ref resolution; binary null counts; rename/copy source; totals; threshold; ordering; API/CLI; endpoint-pair tests |
| **VCS-G07** Process supervision and no-network boundary | Blocker | `PARTIAL` | John + Paul | Qualified executable; environment/config/helper suppression; bounded concurrent capture; timeout/cancel/tree cleanup; command allowlist; no-network proof |
| **VCS-G08** Ref, path, and root safety | Blocker | `PARTIAL` | John + Paul | Ref grammar/resolution; literal path behavior; canonical containment; symlink/junction/nested-root tests; denied-root enforcement |
| **VCS-G09** Errors, stream purity, and determinism | Blocker | `PARTIAL` | George + John | Stable exit/error catalog; one-document streams; redaction; canonical JSON; repeatability; API serializer/CLI JSON byte parity |
| **VCS-G10** Privacy projections and logs | Blocker | `PARTIAL` | Ringo + Paul | Portable schema; prohibited-field tests; remote sanitizer; log allowlist; timestamp decision; matrimonial/client-data policy |
| **VCS-G11** Packaging and platform qualification | High | `PROPOSED` | John | Wheel/sdist schemas; offline install; Python 3.11–3.13 matrix; each claimed OS/Git profile; source-versus-wheel test parity |
| **VCS-G12** `pyprojectmgrV2` integration | High | `PROPOSED` | George + John | Governance schema binding; migration/defaults; QTC evidence; portable provenance; five-pillar invariance tests |
| **VCS-G13** BFT integration | High | `PROPOSED` | Paul + John | Three-mode behavior; BFT safety precedence; unique reconciliation; plan-to-artifact evidence; no serialized-provenance claim |
| **VCS-G14** EDSS/EDSM/EDV isolation | Blocker for those hosts | `PROPOSED` | Ringo + Paul | Explicit source/vault roots; canonical containment; filename-metadata classification; privacy fixtures; host sign-off |
| **VCS-G15** Release and ratification governance | Blocker | `PROPOSED` | Ringo | Approval record; document/schema hashes; exceptions; supported-profile statement; changelog; retest policy |

---

## 5. Gate 0 artifact checklist

The following artifacts must reach `CONTRACT_FROZEN` before Phase 1B implementation begins:

- [ ] core specification and all three companion documents agree on names, fields, operations, exits, owners, and gates;
- [ ] `vcs_common_v1.json`;
- [ ] `vcs_status_v1.json`;
- [ ] `vcs_files_v1.json`;
- [ ] `vcs_validate_v1.json`;
- [ ] `vcs_diff_summary_v1.json`;
- [ ] `vcs_error_v1.json`;
- [ ] `vcs_policy_v1.json`;
- [ ] `vcs_portable_provenance_v1.json`;
- [ ] positive and negative schema fixtures;
- [ ] repository-state decision table;
- [ ] porcelain-v2/file-state mapping table;
- [ ] validation dependency and outcome table;
- [ ] diff endpoint and aggregation table;
- [ ] Git executable/command/environment/configuration matrix;
- [ ] root/privacy projection matrix;
- [ ] stable warning, error, and reason ID catalog;
- [ ] source, wheel, and offline schema-resolution plan;
- [ ] fixture-repository construction manifest;
- [ ] automated conformance inventory with traceability to every blocker/high finding;
- [ ] product decisions for timestamp, machine logs, platform scope, and repository defaults; and
- [ ] named approval record with hashes.

The Phase 1A disposable provider spike MAY begin before this checklist closes. Its output is evidence input, not a stable interface.

---

## 6. Required fixture profiles

| Fixture ID | Repository/profile | Required state |
|---|---|---|
| `FX-NONREPO` | Ordinary directory | No `.git`; readable |
| `FX-CLEAN` | Worktree | Clean attached branch; exact and nearest tags available |
| `FX-DIRTY` | Worktree | One path staged and unstaged; untracked and ignored files |
| `FX-UNBORN` | Empty repository | Attached unborn branch; no commit |
| `FX-DETACHED` | Worktree | Detached at known commit |
| `FX-SHALLOW` | Local shallow fixture | No network needed during test |
| `FX-BARE` | Bare repository | No worktree |
| `FX-LINKED` | Main plus linked worktree | Shared common dir; different worktree dirs |
| `FX-CONFLICTS` | Generated conflict set | `DD`, `AU`, `UD`, `UA`, `DU`, `AA`, and `UU` |
| `FX-RENAMES` | Worktree/index | Rename, copy, delete, type change, and mode change |
| `FX-BINARY` | Worktree/index | Binary add, modify, rename, and delete |
| `FX-SUBMODULE` | Local nested fixtures | Clean, HEAD changed, modified content, untracked content |
| `FX-UPSTREAM` | Local refs only | Missing, equal, ahead, behind, and diverged tracking refs |
| `FX-NAMES` | Worktree | Spaces, tab, newline, leading dash, Unicode, glob/pathspec characters |
| `FX-HOSTILE-CONFIG` | Worktree plus fake helpers | External diff/textconv/pager/fsmonitor/askpass/helper attempts |
| `FX-LARGE` | Fake provider/process | Timeout, cancellation, oversized stdout/stderr, partial records |
| `FX-PRIVACY` | Allowed/denied tree | Case variants, symlink/junction, nested repo, vault/client-data paths |
| `FX-SHA256` | SHA-256 repository when profile claims support | Full 64-character IDs; otherwise typed unsupported evidence |

Fixture creation MUST be scripted, deterministic, offline, and identified by revision/hash. Tests MUST NOT depend on a developer's active repository state.

---

## 7. Phase 0 contract tests

| Test ID | Requirement | Expected result |
|---|---|---|
| `CT-001` | Parse eight schema files | All parse as JSON and validate against Draft 2020-12 metaschema |
| `CT-002` | Resolve all `$ref` values from source tree | No network; all refs resolve |
| `CT-003` | Resolve all `$ref` values from installed wheel | Bytes and behavior match source tree |
| `CT-004` | Wrong `schema_id` in each instance | Rejected by applicable schema |
| `CT-005` | Missing standard-envelope field | Rejected |
| `CT-006` | Unknown top-level/nested governed field | Rejected except explicit `extensions` |
| `CT-007` | Enum, nullability, and conditional negative fixtures | Rejected with expected validation path |
| `CT-008` | Positive fixture for every schema | Accepted |
| `CT-009` | Schema bytes in source, wheel, and sdist | SHA-256 identical to register |
| `CT-010` | Cross-document identifier scan | No conflicting operation, field, rule, reason, error, exit, or gate identifiers |
| `CT-011` | Canonical serializer fixture | Exact UTF-8 bytes, one LF, no BOM, no NaN/float |
| `CT-012` | Compatibility guard | Implementation cannot emit an instance rejected by packaged schema |

All `CT-*` tests are required before `VCS-G02` reaches `CONTRACT_FROZEN`, except implementation-dependent serializer tests, which may transition with Phase 1B.

---

## 8. Inspect conformance tests

| Test ID | Scenario | Required evidence |
|---|---|---|
| `IN-001` | Valid non-repository directory | Exit 0; `is_repository=false`; all repository fields null; no stderr |
| `IN-002` | Missing path | Exit 2; one valid error JSON |
| `IN-003` | Permission-denied path | Exit 20; sanitized structured error |
| `IN-004` | Clean attached branch | Correct root, object format, HEAD, branch, clean counts |
| `IN-005` | Detached HEAD | Branch null; `is_detached=true`; full commit ID valid |
| `IN-006` | Unborn branch | Commit and short ID null; `is_unborn=true` |
| `IN-007` | Shallow repository | `is_shallow=true` without network |
| `IN-008` | Bare repository | `repository_kind=bare`; worktree null; supported operations constrained |
| `IN-009` | Linked worktree | Correct worktree/common-dir interpretation; contained root |
| `IN-010` | Multiple exact tags | Complete UTF-8-byte-sorted array |
| `IN-011` | Nearest tag and distance | Matches frozen provider behavior |
| `IN-012` | Missing upstream | `upstream=null`; not equal-zero ambiguity |
| `IN-013` | Equal/ahead/behind/diverged local upstream | Exact local counts; `freshness=not_checked`; no network |
| `IN-014` | SHA-1 object format | 40-character full ID and declared format |
| `IN-015` | SHA-256 object format | 64-character ID when supported, otherwise exit 31 typed capability/state error |
| `IN-016` | Repeated local output | Canonical non-timing fields and bytes identical |
| `IN-017` | Portable projection | No prohibited path/user/remote/time fields |
| `IN-018` | Local remote sanitizer | Credentials/query/fragment removed or value becomes null with warning |
| `IN-019` | Clean state cannot be fully determined | `worktree.is_clean=null` with stable warning; no false clean claim |

---

## 9. File inventory conformance tests

| Test ID | Scenario | Required evidence |
|---|---|---|
| `LF-001` | No inclusion flags | Effective `include_tracked=true` only |
| `LF-002` | Clean tracked files | Every tracked file exactly once, including unmodified files |
| `LF-003` | Same path staged and unstaged | Independent non-`none` index/worktree states |
| `LF-004` | Untracked selection | Included only when selected; booleans/status invariant |
| `LF-005` | Ignored selection | Included only when selected; expanded to files, not directory placeholders |
| `LF-006` | Rename | Current and original paths; index state `renamed` |
| `LF-007` | Copied working content | Inventory represents the destination as `added`; no false index copy identity |
| `LF-008` | Delete | Correct index/worktree dimension |
| `LF-009` | Type change | `type_changed` in applicable dimension |
| `LF-010` | All seven conflict codes | Exact `DD/AU/UD/UA/DU/AA/UU` mapping |
| `LF-011` | Submodule states | Head/content/untracked dimensions or typed unsupported result |
| `LF-012` | Special filenames | Lossless JSON/text/NUL behavior for supported UTF-8 names |
| `LF-013` | Unsupported encoding | Exit 20 typed error; no replacement characters |
| `LF-014` | Duplicate/conflicting provider record | Exit 20 malformed-provider error |
| `LF-015` | Deterministic order | Unsigned UTF-8 path/original-path ordering |
| `LF-016` | NUL format | One trailing NUL per path; zero bytes for empty result; no status parity claim |
| `LF-017` | Non-repository/bare repository | Exit 10 or 31 according to exact unsupported condition |
| `LF-018` | Bounded large inventory | Exit 41 at limit; process cleaned; one error document |

---

## 10. Policy conformance tests

| Test ID | Scenario | Required evidence |
|---|---|---|
| `VP-001` | Valid policy | Accepted with exact defaults/parameters |
| `VP-002` | Unknown rule/property/parameter | Exit 2 policy-schema error |
| `VP-003` | Invalid/empty branch patterns | Exit 2 before repository evaluation |
| `VP-004` | Rule disabled | Finding `SKIPPED`; skipped count increments |
| `VP-005` | Condition satisfied | Finding `PASS` |
| `VP-006` | Violation disposition `allow` | `PASS` with allowed-by-policy reason |
| `VP-007` | Violation disposition `warn` | `WARN`; exit 0; warning count increments |
| `VP-008` | Violation disposition `fail` | `FAIL`; exit 1; violation count increments |
| `VP-009` | Non-repo with repository allowed | Repository finding passes; dependent rules `NOT_APPLICABLE` |
| `VP-010` | Non-repo with repository required/fail | One repository `FAIL`; dependent rules `NOT_APPLICABLE` |
| `VP-011` | Clean rule dimensions | Staged, unstaged, untracked, conflict, and dirty submodule each violate; ignored alone does not |
| `VP-012` | Exact tag rule | Exact tag satisfies; nearest-only does not |
| `VP-013` | Tracking rule | Missing/equal/ahead/behind/diverged behavior matches parameter/disposition |
| `VP-014` | Branch patterns | Case-sensitive `fnmatchcase`; `*` may match `/`; invalid syntax rejected |
| `VP-015` | Multi-violation | All rules evaluated; deterministic order/counts; no fail-fast |
| `VP-016` | JSON stream behavior | Exit 0 result on stdout; exit 1 result on stderr; other stream empty |
| `VP-017` | Unknown clean state | Treated as a violated condition; `allow`/`warn`/`fail` disposition determines outcome |

---

## 11. Diff conformance tests

| Test ID | Scenario | Required evidence |
|---|---|---|
| `DF-001` | Ref → Ref | Resolved full IDs; correct files/text totals |
| `DF-002` | Ref → Index | Staged changes only relative to base |
| `DF-003` | Ref → Worktree | Index plus tracked worktree changes relative to base |
| `DF-004` | Index → Worktree | Unstaged tracked changes only |
| `DF-005` | Untracked file present | Excluded; `untracked_files_included=false` |
| `DF-006` | Binary add/modify/delete | Per-file counts null; binary count increments; totals exclude binary |
| `DF-007` | Binary rename | Null counts plus original path |
| `DF-008` | Text rename/copy | Original path, consistent thresholds, correct counts |
| `DF-009` | Type change | Correct change type and count semantics |
| `DF-010` | Missing ref | Exit 30 structured error |
| `DF-011` | Leading-dash/unsafe ref | Rejected before diff command |
| `DF-012` | Ambiguous short ID | Rejected |
| `DF-013` | Malformed/inconsistent numstat and name-status | Exit 20 malformed-provider error |
| `DF-014` | Deterministic order/repeat | Canonical byte-identical JSON for unchanged state |

---

## 12. Security and process conformance tests

| Test ID | Scenario | Required evidence |
|---|---|---|
| `SP-001` | Command construction | Argument vectors; no shell; exact qualified executable reused |
| `SP-002` | Missing/unsupported/fake executable | Exit 11/12 as applicable |
| `SP-003` | Inherited hostile `GIT_*`/`SSH_*` variables | Excluded from child environment |
| `SP-004` | Hostile global Git config | Not loaded |
| `SP-005` | Local external diff/textconv | Helper never executes |
| `SP-006` | Pager/editor/askpass/SSH askpass | Helper never executes; no prompt |
| `SP-007` | Filesystem monitor/helper configuration | Helper never executes |
| `SP-008` | Ref option injection | User value cannot become option or path |
| `SP-009` | Special/pathspec filenames | Treated literally |
| `SP-010` | No-network proof | Approved command suite produces no network attempt in monitored fixture |
| `SP-011` | Per-process timeout | Exit 40; process group cleaned |
| `SP-012` | Whole-operation timeout | Exit 40; remaining commands not launched |
| `SP-013` | Stdout overflow | Exit 41 before unbounded retention; cleanup complete |
| `SP-014` | Stderr overflow | Exit 41; no raw stderr leak |
| `SP-015` | API cancellation | Exit/error state 42; cleanup idempotent |
| `SP-016` | CLI Ctrl+C | One cancellation error in JSON mode; no traceback |
| `SP-017` | Completion/cancel race | One terminal state and one document |
| `SP-018` | Child/descendant process | Platform-profile cleanup evidence and residual risk recorded |
| `SP-019` | Raw Git diagnostic with credentials/path | Machine error remains allowlisted and redacted |
| `SP-020` | Command allowlist audit | No invoked subcommand outside profile |

---

## 13. Privacy and integration conformance tests

| Test ID | Scenario | Required evidence |
|---|---|---|
| `PR-001` | Requested root outside allowlist | Exit 21 before repository data returned |
| `PR-002` | Requested/discovered root inside deny root | Exit 21 |
| `PR-003` | Repository root above CLI path | Rejected unless explicit API boundary permits it |
| `PR-004` | Symlink/junction/reparse escape | Exit 21; platform-specific evidence |
| `PR-005` | Case/separator variation | Same canonical boundary decision |
| `PR-006` | Nested repository | Correct contained root; no upward privacy escape |
| `PR-007` | Vault/client-data root | Rejected before `list-files` or diff |
| `PR-008` | Portable prohibited-field injection | Schema/serializer rejects every prohibited field |
| `PR-009` | Machine log default | No paths, refs, tags, remote/repo IDs, user/host, arguments, or raw stderr |
| `PR-010` | Remote URL forms | Credentials/query/fragment/local path removed; malformed becomes null warning |
| `INT-001` | `pyprojectmgr` schema binding | Invalid policy rejected; valid policy canonicalized |
| `INT-002` | Pentagon invariance | Repository policy/provenance does not change five-pillar definition/digest input |
| `INT-003` | Non-repo `pyprojectmgr` profile | Passes or warns exactly as configured; dependent findings N/A |
| `INT-004` | BFT filesystem mode | Identical selection with and without VCS availability |
| `INT-005` | BFT tracked mode | Intersection applied after BFT hard denials; no tracking override |
| `INT-006` | BFT repository-aware mode | Annotation only; no duplicate/missing plan entries |
| `INT-007` | BFT plan-to-artifact reconciliation | Final artifact equals approved safe plan |
| `INT-008` | BFT provenance scope | Runtime metadata only; no false serialized-provenance claim |
| `INT-009` | EDSS/EDSM/EDV source profile | Only approved source root accessible; case/vault roots denied |

---

## 14. Packaging and platform evidence

| Test ID | Scenario | Required evidence |
|---|---|---|
| `PK-001` | Source checkout test | Full suite passes on each supported Python version |
| `PK-002` | Wheel installation offline | Installs without network/runtime dependency download |
| `PK-003` | Wheel schema access | Eight package resources available and hash-correct |
| `PK-004` | `python -m vcs_tool` | Same command behavior as console entry point |
| `PK-005` | Console script | Correct exit/stream behavior |
| `PK-006` | sdist rebuild | Reproducible documented inputs; schemas preserved |
| `PK-007` | Claimed OS/Git profile | Entire applicable conformance subset passes |
| `PK-008` | Unsupported platform/Git | Installation/runtime claim fails explicitly, not silently |
| `PK-009` | Source versus wheel JSON | Canonical fixture output byte-identical |
| `PK-010` | License/version metadata | Matches release record and public API version |

---

## 15. Phase transition rules

### 15.1 Phase 0 to Phase 1B

Requires `VCS-G01` through `VCS-G10` and `VCS-G15` at `CONTRACT_FROZEN`. `VCS-G11` may be `PARTIAL` only for platform profiles not claimed by the first implementation slice.

### 15.2 Phase 1B implementation complete

Requires:

- source and built-wheel implementation;
- all applicable `CT`, `IN`, `LF`, `VP`, `DF`, `SP`, `PR`, and `PK` tests passing;
- zero untriaged failure or skipped blocker tests;
- documented unsupported profiles; and
- `VCS-G02` through `VCS-G11` at least `IMPLEMENTED`.

### 15.3 Phase 1 evidence accepted

Requires named review of command traces, negative tests, process cleanup, privacy output, schema artifacts, package contents, and residual risks. A green CI summary alone is not evidence acceptance.

### 15.4 Phase 2 and Phase 3

`pyprojectmgr`, BFT, and matrimonial-system integration gates advance independently. One host's acceptance does not authorize another. Serialized BFT provenance remains deferred until a separate BFT transport contract is accepted.

---

## 16. Evidence record template

```text
Evidence ID:
Gate ID(s):
Status requested:
Product/application:
Operating system/platform profile:
Python version:
Git version/object format:
Package/source revision:
Artifact paths and SHA-256:
Fixture revision:
Test command:
Test result summary:
Security/process trace result:
Privacy/redaction result:
Unresolved findings:
Exceptions/compensating controls:
Residual risk:
Owner sign-off:
Architecture review:
Implementation review:
Contract/privacy review:
Product-owner acceptance:
Approval date:
Retest/expiry date:
```

---

## 17. Current evidence note

As of this draft:

- v0.2.1 supplies substantial architecture text but no machine-readable schema artifacts were found in the reviewed workspace under `docs`, `src`, or `tests`;
- no Phase 1 `src/vcs_tool` implementation or frozen conformance fixture set is claimed by this document;
- the four v0.2.2 Markdown files are design drafts only; and
- no gate in this register is `CONTRACT_FROZEN`, `IMPLEMENTED`, or `EVIDENCE_ACCEPTED`.

These statements must be updated from recorded evidence rather than manually upgraded by optimistic prose.

---

## 18. Approval record

| Role | Name | Decision | Date | Scope/conditions |
|---|---|---|---|---|
| Product Owner | Ringo | Pending | — | Product scope, host defaults, privacy, sequence, ratification authority |
| Lead Architect | George | Pending | — | Architecture, state model, schemas, command and integration boundaries |
| Lead Developer | John | Pending | — | Implementability, provider spike, package and automated evidence |
| Lead Analyst / Collaborative Developer | Paul | Draft prepared | 2026-08-31 | Candidate direction only; no contract/evidence acceptance |

No row is interpreted as approval unless it identifies the exact document/schema artifact hashes and any conditions.

---

## 19. Ratification decision template

```text
Decision: APPROVE | APPROVE_WITH_CONDITIONS | RETURN_FOR_REVISION | REJECT
SPEC-VCS-001 document SHA-256:
Data contract SHA-256:
Git security/privacy profile SHA-256:
Gate register SHA-256:
Schema artifact manifest SHA-256:
Approved gate states:
Authorized implementation scope:
Deferred items:
Exceptions and residual risks:
Approvers and dates:
```

Until that record is complete, v0.2.2 remains a freeze candidate.

---

— **Version 0.2.2 Conformance Gate Register Draft for Team Review**
