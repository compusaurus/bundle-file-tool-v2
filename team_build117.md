# BFT v2.1 Build 117 — Team Communication

**From:** Paul, Lead Developer / Lead Analyst  
**To:** Ringo (Owner), George (Lead Architect), John (Lead Developer)  
**Date:** 2026-08-26  
**Subject:** Build 117 ratified and release candidate verified

Team,

Ringo's Build 117 Governance ratification is recorded, and the governed release candidate is now assembled and verified.

## Outcome

The byte-final installer completed a clean Build 116 → 117 upgrade in isolation. It verified all **74 payload hashes**, all **73 content markers**, restored read-only protection to the governed config, reported `bundle-tool 2.1.117`, and passed the complete suite: **1,453 tests, zero failures, 90.82% coverage**. An independent post-install pass compared every installed payload file to the delivery manifest and found zero mismatches.

## What Build 117 closes

- The bundle-open and bundle-write dialogs remember their own last folders, and Create Bundle receives a suggested name.
- Folder rows toggle selection on a normal single click while the native expander only opens/closes the row.
- Unbundle size is no longer perpetually `?`; legacy sizes are inferred when safe.
- Horizontal and vertical scrollbars are wired and proven to activate under real overflow.
- UTF-8 BOM ingress is accepted at the read boundary, including George's NodeThermX bundle shape.
- UTF-16/32, invalid UTF-8, NUL-bearing input, and unsupported explicit encodings fail closed with transport diagnostics.
- CLI, service, and GUI share the same selection plan, and the emitted artifact is reconciled against it before atomic publication.

## Release-verification finding

The clean-room installer test did its job twice before the final seal. It caught a blank version-capture path and then a stale `67 files placed` display label. Neither defect escaped into RC1: the probe and count were corrected, and the exact final installer was rerun through all 1,453 tests.

## Governance boundary and next owner

Ringo has approved the build. George now needs to approve the exact nine-file release-identity diff. The live governed identity is intentionally still `2.1.116`.

After George's approval, an authorized interactive account must apply and verify the proposed hashes, stage only the approved release scope, inspect the staged diff, create the commit, and create the release tag. Automation will not write `.git/index` or `.git/refs/`; that is the repository's enforced separation-of-duties contract.

The approval record is `docs/architecture/phase0/BUILD117_RELEASE_IDENTITY_EXACT_DIFF_2026-08-26.md`. The detailed candidate receipt and interactive handoff are under `docs/implementation/`.

— Paul
