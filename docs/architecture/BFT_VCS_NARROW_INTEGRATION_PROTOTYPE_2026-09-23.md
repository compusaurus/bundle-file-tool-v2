# BFT/VCS Narrow Integration Profile

**Status:** `IMPLEMENTED_CANDIDATE` — design-and-prototype authority only  
**Date:** 2026-09-23  
**Scope:** Bundle File Tool source selection and repository-target extraction  
**Transport impact:** None  
**Git mutation authority:** None

## Decision

BFT may consume a read-only repository inventory and plan-bound source bytes
supplied by the standalone VCS Tool. VCS Tool never writes, stages, commits,
resets, checks out, deletes, or restores repository content. It does not parse
or write bundle artifacts and does not participate in extraction writes.

The responsibility boundary is:

```text
Repository -> VCS identity/inventory -> BFT safety and selection
           -> VCS verified source bytes -> BFT bundle
Bundle -> BFT validation/preflight/extraction -> VCS observes repository state
```

BFT remains authoritative for hard denials, selection rules, metadata snapshots,
bundle formatting, integrity checking, extraction collision handling, writes,
and plan-to-artifact reconciliation. In `tracked` mode VCS Tool owns the secure
opening and plan verification of source bytes; filesystem mode remains a direct
BFT read.

## Distribution boundary

The prototype consumes the standalone package through its public Python facade,
never an editable checkout or provider-internal import:

- distribution pin: `vcs-tool==0.5.0a1`;
- runtime version: `0.5.0-alpha.1`;
- verified wheel SHA-256:
  `0cce15d1648adc99475490520ef9908ae97583e8706e98f6f7f06f91319530b9`;
- adapter: `core.vcs_repository.VcsToolRepositoryReader`.

The dependency is an optional `repository` extra. Ordinary filesystem use does
not import or require VCS Tool.

## Prototype slice

### Repository source

The prototype adds two source modes:

| Mode | Behavior |
|---|---|
| `filesystem` | Existing BFT behavior. This remains the default and requires no VCS Tool. |
| `tracked` | BFT scans and evaluates normally, intersects included paths with VCS Tool's tracked-file inventory, then consumes approved bytes through a VCS content-digest read session. |

The intersection occurs after BFT rule and emission-safety evaluation. Repository
evidence can only remove an included path. It cannot include an excluded path,
unblock a blocked path, change an unknown path to known, or bypass file-size and
containment checks.

The prototype requires the selected BFT base directory to be the exact repository
root. Bundling a subdirectory whose repository root is above it is deferred until
the allowed-root user experience is designed.

Immediately before emission, BFT opens a new tracked-only working-tree session.
Its inventory must equal the reviewed inventory. VCS Tool captures a
`content_digest` plan and every `read_bytes()` result must report plan
verification with matching path, size, and SHA-256 evidence. BFT never silently
falls back to direct reads when repository mode was approved.

Only current-worktree files are in scope. Reading blobs from a branch, tag, or
commit without checking it out is not part of this profile.

### Repository extraction target

BFT parses and checks the bundle before repository preflight. The read-only
preflight then:

1. verifies that the output directory is the exact repository root;
2. records whether worktree cleanliness is clean, dirty, or unknown;
3. requests tracked, untracked, and ignored inventory;
4. checks every bundle path against the actual filesystem;
5. classifies existing targets as tracked, untracked, ignored, or other; and
6. evaluates explicit overwrite authorization.

The conservative prototype policy requires a clean worktree and refuses every
existing destination class unless that class is explicitly authorized. BFT's
ordinary overwrite policy remains a second required authorization: repository
permission does not silently convert `prompt` or `skip` to `overwrite`.

No post-extraction Git mutation occurs. A future UI may display a fresh read-only
inventory after extraction, but that observation is not required for the first
prototype gate.

## BFT adapter contract

BFT depends on an injected `RepositoryReader` protocol with two operations:

```python
inspect(root, *, allowed_root) -> RepositoryStatus
list_files(
    root,
    *,
    allowed_root,
    include_tracked,
    include_untracked,
    include_ignored,
) -> RepositoryInventory
```

The protocol is a host seam, not a second VCS implementation. The adapter
translates the standalone VCS Tool's typed API into BFT records and exposes a
context-managed `open_read_session()` operation for verified bytes. BFT does
not import `GitCliProvider`, invoke Git directly, or parse VCS Tool CLI text.

Inventory paths are unique, safely relative, slash-normalized, and classified as
exactly one of tracked, untracked, or ignored. The adapter supplies local absolute
root paths only in memory. Plan-report repository evidence excludes those paths.

## Snapshot and race contract

A repository-backed plan binds a deterministic digest of the approved inventory.
BFT requests the inventory again immediately before and after reading content and
requires the read session's own inventory to match. A membership or
repository-state change fails with `PlanDriftError`; the operator must re-plan
and review. Existing BFT metadata checks independently detect file size,
timestamp, identity, and containment drift, while VCS Tool reconciles the exact
consumed bytes against its content-digest session plan.

The two checks are complementary:

- VCS evidence proves that selection membership still matches the reviewed
  repository inventory and that each consumed byte stream matches the session
  plan.
- BFT evidence proves that the files it reads still match the reviewed filesystem
  snapshot and that the final manifest equals the approved emission list.

Neither check claims to prevent mutation by another process. They fail closed on
observed drift.

## VCS Tool candidate capability

The 0.5.0-alpha.1 candidate provides the installable package, typed
`inspect`/`list_files` results, bounded working-tree read sessions, content
digest plan reconciliation, and packaged schemas required by this prototype.
The adapter uses no `validate`, `diff-summary`, historical commit read, Lab, CLI,
or write operation. Independent gate acceptance and the full claimed
platform/runtime matrix remain release obligations rather than prototype claims.

## BFT work required after this prototype

The prototype intentionally does not expose UI or CLI controls. Promotion to a
user-facing feature requires:

- promotion of the adapter from its exact alpha pin to an accepted VCS Tool
  release;
- availability/capability presentation without changing filesystem defaults;
- CLI and desktop controls for source mode;
- extraction preflight review showing cleanliness and collision classes;
- explicit operator approval for each permitted overwrite class;
- post-extraction read-only status presentation;
- Windows, Linux, and macOS qualification for every platform where the feature
  is enabled; and
- accepted evidence for the BFT integration tests in SPEC-VCS-001.

## Prototype acceptance criteria

- Filesystem mode behaves identically without a repository reader.
- Tracked mode includes only the intersection of tracked paths and BFT-approved
  paths.
- A tracked path cannot override a BFT block or exclusion.
- A repository inventory change after planning blocks checking and creation.
- Repository-mode bundle and selection-check bytes come only from the
  plan-verified VCS read session.
- A mismatched session inventory, unverified read, path mismatch, size mismatch,
  or content-digest mismatch blocks artifact creation.
- Plan reports contain no absolute repository path.
- Extraction preflight examines tracked, untracked, ignored, and filesystem-only
  collisions before writes.
- The default repository extraction policy blocks dirty/unknown worktrees and all
  existing paths.
- Explicit repository authorization and BFT overwrite authorization are both
  required before replacement.
- No Git command or VCS Tool implementation is embedded in BFT.

## Deferred decisions

- optional inclusion of untracked source files;
- repository-aware annotation without filtering;
- repository roots above a selected source or extraction subdirectory;
- historical commit/tag content reads;
- portable provenance in bundle formats;
- deletion manifests, patch application, staging, commits, branch creation, and
  rollback; and
- required versus optional VCS availability in installers.

This document authorizes prototype work only. It does not advance `VCS-G13` to
`IMPLEMENTED` or `EVIDENCE_ACCEPTED`.
