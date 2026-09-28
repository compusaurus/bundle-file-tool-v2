# BFT v2.1 Build 100 — WP0 Ratification Decision Record

**Record ID:** BFT-WP0-DR-001
**Prepared by:** Paul, Lead Analyst
**Date:** 2026-07-23
**Last updated:** 2026-07-24
**Status:** John accepts substantive evidence as represented; Gate 1 remains conditional on canonical QC or a bounded Ringo-approved waiver

## 1. Authorization

Ringo authorized **WP0 — Ratification and baseline normalization** on 2026-07-23.

This authorization permits baseline discovery, cataloging, reconciliation, validation, and preparation of a protected baseline commit. It does not silently convert Paul's technical recommendations into George's architecture approval or John's implementation acceptance. Those approvals are recorded explicitly below.

## 2. Team roles for WP0

| Role | Team member | WP0 responsibility |
|---|---|---|
| Product Owner | Ringo | Approve Build 100 scope, user-facing defaults, and explicit non-goals |
| Lead Architect | George | Approve service boundary, version contract, filtering precedence, and Web stack |
| Lead Developer | John | Confirm baseline contents, resolve test defects, and accept implementation constraints |
| Lead Analyst | Paul | Reconcile evidence, define gates, validate element preservation, and record approval state |

## 3. Operating decisions

### D-001 — Candidate source baseline

**Decision:** Use `BFT_v2_src_build_101.txt` as the entry-state candidate source because all 21 bundled source files matched the live `src` tree exactly after line-ending normalization. The nine deliberate WP0 source deltas—three functional corrections and six whitespace-only cleanups—are recorded in `WP0_SOURCE_RECONCILIATION.md`.

**Status:** Entry state reconciled and normalized candidate validated.
**Limit:** This does not yet approve the wider repository baseline or a release.

### D-002 — Build 100 scope

**Decision:** Retain the mandatory Build 100 scope:

- one shared `BundleToolService`;
- CLI, Tkinter, and local Web adapters over that service;
- `plain_marker`, `md_fence`, and `jsonl` profiles;
- cross-interface parity;
- filtering surfaced consistently across CLI, config, Tkinter, and Web;
- governed delivery tooling and acceptance gates.

**Status:** Product direction accepted by Ringo through WP0 authorization.
**Architecture review:** George ratified the normalized Build 100 architecture on 2026-07-23.

### D-003 — Repository awareness

**Decision:** Treat repository-aware behavior as an explicit Build 100 non-goal. Record it as future feature `BFT-2.1-B101-REPO-AWARE`, read-only and opt-in when later approved.

**Status:** Closed — Ringo confirmed repository awareness is deferred to Build 101 on 2026-07-23.

### D-004 — Version ownership

**Decision:** The delivery payload owns the installed version. The approved package installs and verifies `2.1.102`; the stager does not increment it to `2.1.103`.

**Reason:** Artifact identity, installed identity, stale-kit checks, runtime identity, and rollback evidence must agree.

**Status:** Closed — George ratified, John concurred, and Ringo approved the updated `2.1.102` value on 2026-07-23. Runtime, packaging, UI, configuration, manifest, and stager contracts were synchronized.

### D-005 — Filtering default

**Recommendation:** Use a safety deny-list default. Permit files unless a mandatory safety rule, configured rule, operation rule, size rule, or read failure excludes them.

**Status:** Closed — George ratified and Ringo confirmed on 2026-07-23. Both code and shipped configuration now use `allow_globs: ["**/*"]` with the five archive/bundle safety denies synchronized.

### D-006 — Filtering precedence

**Recommendation:**

1. Mandatory safety denies.
2. Config allow/deny globs and extension lists.
3. Invocation-specific CLI options, replacing the corresponding config list for that invocation.
4. Tkinter/Web operation refinements, session-only unless explicitly saved.
5. Deny wins at the same or higher safety layer.

**Status:** Closed — George ratified on 2026-07-23.

### D-007 — Web stack

**Recommendation:** Flask, bound to `127.0.0.1`, with explicit confirmation before write operations.

**Status:** Closed — George ratified and John concurred on 2026-07-23. Any future non-loopback bind requires a new explicit gate.

### D-008 — Delivery documents

**Decision:** New deliveries use `built_build<N>.md` and `team_build<N>.md`. Generic `BUILT.md` and `TEAM.md` are retained only as legacy history until a separate archive action is approved.

**Status:** Existing PO directive; active.

### D-009 — Delivery entry point

**Decision:** `PREP_AND_STAGE_BFT.bat` is the single operator entry point. The kit contains exactly one build-specific installer.

**Status:** Existing PO directive; active.

## 4. Ratification checklist

| Gate | Required owners | Ringo | George | John | Current status |
|---|---|---|---|---|---|
| 1. Accept normalized candidate baseline | George + John | WP0 authorized | Ratified | Conditional accept | Open pending John's review of the added evidence and ratification implementation |
| 2. Defer repository awareness to Build 101 | Ringo | Confirmed | N/A | N/A | Closed |
| 3. Package-owned installed version `2.1.102` | Ringo + George + John | Approved updated value | Ratified | Concurred | Closed |
| 4. Safety deny-list filtering default | Ringo + George | Confirmed | Ratified | Advisory concern resolved | Closed |
| 5. Filtering precedence contract | George | N/A | Ratified | N/A | Closed |
| 6. Flask on `127.0.0.1` | George + John | N/A | Ratified | Concurred | Closed |
| Build-stamped documents | Existing PO directive | Approved | N/A | N/A | Closed |
| Single stager entry point | Existing PO directive | Approved | N/A | N/A | Closed |

## 5. WP0 exit rule

WP0 may be committed as the authoritative baseline only when:

- the repository baseline catalog has no unclassified file;
- deleted verification assets are restored or have an approved replacement/retirement mapping;
- the active header-policy path resolves;
- the current Python validation environment runs;
- the full test suite has zero failures or each exception has an approved written disposition;
- the baseline branch exists;
- the final staged diff contains no local runtime data, backups, logs, sessions, generated reports, or emergency scripts.
- canonical pyprojectmgr QC runs or has an approved written disposition for the tool's non-idempotent schema-remediation failure;
- required `.pyprojectmgr/project_spec.json` is present and governed.

## 6. Execution record

The WP0 technical normalization completed with the following evidence:

- all baseline files classified;
- active header-policy path resolved;
- local and generated artifacts excluded;
- legacy verification retirements mapped to passing replacement tests;
- production test shims removed;
- 480 tests passed with zero failures after the ratification changes;
- 88.49% coverage passed the 85% requirement;
- all intentional source divergence recorded by file, reason, size, and SHA256.
- `.pyprojectmgr/project_spec.json` now follows the family-app governance shape and records the intentional Git separation-of-duties policy.
- the approved `2.1.102` version and deny-list contracts have executable regression tests.

The protected branch and commit could not be created because the review environment permits repository content changes but denies writes to `.git`. The team will not remove that deny entry until its owner confirms whether it is an intentional separation-of-duties control. If intentional, an authorized interactive account must perform the commit.

## 7. Team review record

- **George, Lead Architect (2026-07-23):** Ratified Gates 1, 3, 4, 5, and 6 on architectural authority.
- **John, Lead Developer (2026-07-23):** Concurred on Gates 3 and 6; marked Gate 1 conditional on test-count arithmetic and defect-level traceability; corrected the shared gate-ownership model.
- **Paul disposition:** Added the requested evidence to `WP0_VALIDATION_REPORT.md`, restored `deny_additions.json` to the governed candidate, verified governed paths against `.gitignore`, mapped supplemental checks to canonical QC vocabulary, and left Gate 1 open for John's final review.
- **Ringo, Product Owner (2026-07-23):** Closed Gates 2–4; set installed version to `2.1.102`; confirmed the Git ACL is intentional; required standardized project specification governance.
- **Paul follow-up (2026-07-24):** Confirmed that George's and John's attached reviews predate the ratification implementation and issued `WP0_REQUEST_FOR_JOHN_FINAL_GATE1_REVIEW.md`. No John approval is inferred before an explicit response.
- **John, Lead Developer (2026-07-24):** Accepted all six prior evidence conditions as represented and agreed the protected commit is separate from Gate 1. Gate 1 remains conditional until canonical strict QC either completes cleanly on the exact candidate or receives a named, scoped, time-bounded waiver from Ringo or an explicitly delegated owner. John also requested the six primary records and the actual QC failure evidence for direct audit.
- **Paul disposition (2026-07-24):** Recorded John's response without closing Gate 1, assigned blocker `BFT-WP0-QC-001`, prepared the six-record primary-evidence package, and preserved the intentional `.git` ACL.
