# BFT Build 117 Interactive Release Handoff

**Status:** Awaiting George's exact-diff approval  
**Interactive operator:** Authorized repository account  
**Prepared:** 2026-08-26

## Preconditions

1. George approves `docs/architecture/phase0/BUILD117_RELEASE_IDENTITY_EXACT_DIFF_2026-08-26.md`.
2. The live baseline hashes still match the “Live baseline” column in that record.
3. The operator reviews the existing dirty worktree and separates Build 117 from unrelated/user-owned changes.
4. The candidate archive hash and fidelity receipt match the final values recorded after sealing.

## Controlled release sequence

1. Apply only the approved release-identity fields through the approved release/governance mechanism. Do not copy the broader Phase 0 structural proposal into the manifest.
2. Recompute all nine proposed file hashes and require exact agreement with the approval record.
3. Confirm `bundle_config.json` is read-only and its digest equals the manifest value.
4. Run the full suite and require 1,453 passing tests and coverage at or above 85%.
5. Stage only the reviewed Build 117 source, tests, governed identity, installer, and release records. Do **not** use `git add -A` in this dirty tree.
6. Inspect the complete staged diff and staged file list before committing.
7. Commit from the authorized interactive account using the repository's approved message convention.
8. Create the approved Build 117 tag only after the commit and verification evidence agree.
9. Publish/move the final kit only after the release commit and tag exist.

## Automation boundary

`.pyprojectmgr/project_spec.json` defines `governance.repository_controls.git_metadata_write_policy` as separation of duties:

- `automated_agents: deny`
- `authorized_interactive_accounts: allow`
- protected paths: `.git/index` and `.git/refs/`

Accordingly, the candidate preparation intentionally stops before staging, committing, or tagging.
