# Bundle File Tool v2.1 Build 100
## Implementation Readiness Decision and Delivery-Standard Plan

**Prepared by:** Paul, Lead Analyst  
**For:** Ringo, Product Owner; George, Lead Architect; John, Lead Developer  
**Date:** 2026-07-23  
**Decision:** **NOT READY FOR APPLICATION IMPLEMENTATION**

---

## 1. Executive decision

The Build 100 direction is sound, but the implementation package is not yet complete enough to begin safely in the live legacy repository.

The service-facade architecture, tri-UI goal, deterministic profiles, phased implementation order, and delivery-governance intent should be approved. However, work should pause at a short ratification and baseline-normalization phase because several decisions still change runtime behavior or the release contract:

1. The authoritative version/build policy is contradictory.
2. File-filter defaults and precedence remain proposed rather than approved.
3. The Web framework is not locked.
4. The delivery kit layout and installer contract disagree across documents.
5. The current stager is not operational with any of its documented command-line options.
6. The live repository is not a clean, governed baseline.
7. The canonical installer helper block required by the team standard is not identified.
8. The current full test result is not independently established.

Accordingly, this document is the required implementation plan. No application or delivery-process files in the BFT repository were changed during this review.

---

## 2. Evidence reviewed

The decision is based on direct review of:

- `BFT_v2_1_Build100_Tri_UI_Feature_and_System_Spec.pdf`
- `Addendum_B_BFT_Build100_Filtering_and_Repo_Assessment.pdf`
- `TEAM_delivery_standard_v2.md`
- `PREP_AND_STAGE_LET.bat`
- `INSTALL_LET_v1_0_0_build104_react16_result_render_fix_r1.bat`
- `BFT_v2_src_build_101.txt`
- The live repository at `bundle_file_project\bundle_file_tool_v2`
- The live BFT stager, metadata, configuration, tests, source imports, and Git state

The attached Build 101 source bundle contains 21 source files. After normalizing line endings for comparison, all 21 files match the corresponding files in the live `src` tree. The source bundle is therefore a reliable representation of the current source tree, but it is not yet a release baseline because the tree remains uncommitted and the wider repository contains additional modified, deleted, and untracked material.

---

## 3. Readiness assessment

| Area | Status | Finding |
|---|---|---|
| Product direction | Ready | A safe bidirectional bundle tool with CLI, Tkinter, and local Web UI is a coherent Build 100 target. |
| Core architecture | Ready with clarification | `BundleToolService` is the correct shared boundary, but request DTOs and error/result taxonomy need to be locked. |
| Profile scope | Ready | `plain_marker`, `md_fence`, and `jsonl` are a reasonable mandatory set with deterministic detection order. |
| Filtering design | Not ready | Default posture and cross-surface precedence still require approval. |
| Web implementation | Not ready | Flask versus FastAPI remains open. |
| Version/build identity | Not ready | Five incompatible version signals exist in the current materials. |
| Repository baseline | Not ready | The live tree is materially dirty and contains legacy delivery artifacts and open selection-manifest issues. |
| Delivery standard | Not ready | The standard is still draft, its canonical skeleton is unspecified, and its described helper structure does not match the supplied LET installer. |
| BFT stager | Not ready | `/dryrun`, `/y`, and `/norun` corrupt script-root resolution because argument shifting occurs before `%~dp0` is captured. |
| BFT installer/builder | Missing | No Build 100 installer, canonical installer template, delivery builder, or delivery validator exists. |
| Test baseline | Not ready | Historical material reports drift; the current suite was not independently executable in the review environment. |

---

## 4. What is already strong enough to retain

### 4.1 Service-facade dependency direction

Retain the required direction:

```text
CLI adapter       ─┐
Tkinter adapter   ─┼─> BundleToolService ─> parser / writer / validators / config / logging
Web adapter       ─┘
```

No UI adapter may construct `BundleParser`, `BundleWriter`, `BundleCreator`, or `ProfileRegistry` directly. The current source violates this rule in `cli.py`, `ui\bundle_frame.py`, and `ui\unbundle_frame.py`, confirming that the facade is necessary rather than cosmetic.

### 4.2 Implementation order

Retain this order:

1. Normalize the baseline and version contract.
2. Add the service facade.
3. Complete the profile registry and JSONL profile.
4. Refactor CLI to the service.
5. Refactor Tkinter to the service.
6. Add Web UI/API over the service.
7. Complete governed delivery tooling.
8. Freeze and run full QA/QC.

Delivery tooling may be developed as an isolated foundation slice after baseline ratification, but it must not package an unapproved application baseline.

### 4.3 Filtering mechanism

Retain `GlobFilter` as the single enforcement engine. Extension controls are convenience inputs translated to glob rules, not a second filter implementation.

### 4.4 LET delivery behavior

Use the LET R4 stager and Build 104 installer as behavioral references for:

- upgrade/bootstrap/recovery modes;
- snapshot before mutation;
- temporary archive followed by verified promotion;
- pre-extract Gate B;
- pre-copy and post-copy SHA256 verification;
- per-file backups;
- content-marker verification;
- acceptance gates;
- success-only teardown;
- retained rollback material after failure.

They are not yet safe to designate as the byte-canonical BFT template because the documented team standard and the supplied installer do not have the same helper-block structure, and the LET stager shares the option-parsing defect described below.

---

## 5. Blocking findings and required resolutions

### B1. Establish one authoritative baseline

Current Git state includes modified source and test files, deleted verification/catalog files, and many untracked governance and generated artifacts. The 21 live source files match the attached Build 101 bundle, but that agreement alone does not establish which tests, scripts, configs, and governance assets belong in the baseline.

**Required action**

1. Freeze all current work.
2. Produce a catalog of tracked, deleted, and untracked files.
3. Classify each item as product source, test, delivery/governance, generated output, local runtime data, backup, or obsolete.
4. Resolve the four open items in `SELECTION_MANIFEST.txt`.
5. Restore or formally retire the deleted verification/catalog files.
6. Commit the approved baseline on a dedicated Build 100 branch before feature work.
7. Tag or otherwise record the baseline commit/hash in the Build 100 record.

**Exit gate**

- `git status --short` is clean.
- A baseline catalog names every retained production and test file.
- The attached bundle and live source are reconciled to the approved commit.

### B2. Replace the current version policy

Observed version signals:

- Build 100 specification target: `2.1.100`
- Specification post-install state: `2.1.101`
- Live `VERSION.txt`: `2.0.101`
- `pyproject.toml`: `2.1.0`
- `bundle_config.json`: `2.1.0`
- Source headers: mixed `2.1.0`, `2.1.1`, `2.1.10`, and `2.1.11`
- Legacy `BUILT.md` / `TEAM.md`: Build 198

The stager currently increments the build after installation. That makes a package named Build 100 install itself as Build 101, weakening stale-kit detection and making installed identity differ from artifact identity.

**Recommendation**

Adopt package-owned versioning:

- Build 100 payload contains `VERSION.txt = 2.1.100`.
- `src\core\version.py`, packaging metadata, runtime displays, and API output all derive from the same value.
- The installer verifies that the installed result is exactly `2.1.100`.
- `PREP_AND_STAGE_BFT.bat` does not increment versions.
- Build 101 is created only by a later Build 101 payload.

**Exit gate**

A version-contract test proves equality among `VERSION.txt`, `core.version`, packaging metadata, CLI `--version`, Tkinter display, and Web `/api/version`.

### B3. Ratify filtering behavior

The current and proposed defaults differ in kind:

- current source: primarily directory-oriented allow rules;
- live config: extension-oriented allow rules;
- Build 100 spec: a narrower extension allow-list;
- Addendum recommendation: safety deny-list by default.

**Recommendation**

Approve the Addendum's deny-list default:

1. Mandatory safety denies always apply.
2. Config allow/deny globs and extension lists apply next.
3. Invocation-specific CLI options replace the corresponding configurable list for that invocation.
4. Tkinter/Web operation selections refine the current request only unless explicitly saved.
5. Deny always wins at a given or higher safety layer.

Every discovered file must receive a reason code:

- `included`
- `excluded_by_user_rule`
- `excluded_by_config_rule`
- `blocked_by_safety_rule`
- `blocked_by_size_limit`
- `unreadable`

This closes the service-result taxonomy gap and allows all UIs to explain omissions consistently.

**Exit gate**

Ringo approves default posture; George approves precedence; Paul adds migration and parity tests.

### B4. Lock the Web stack

**Recommendation:** Flask for Build 100, local-only on `127.0.0.1`, with an approved compatible version pinned in project metadata. Keep write operations behind explicit user confirmation.

**Exit gate**

The dependency, launch command, bind address, port behavior, browser-open behavior, request-size limit, and write-confirmation rule are recorded in the ratified specification.

### B5. Complete the service contract

The existing result shape is useful but too generic for parity and filtering.

**Required request DTOs**

- `DiscoverFilesRequest`
- `DiscoverFileTypesRequest`
- `BundlePreviewRequest`
- `CreateBundleRequest`
- `ParseBundleRequest`
- `ValidateBundleRequest`
- `PlanExtractRequest`
- `ExtractBundleRequest`
- `ConfigPatchRequest`

**Required common result fields**

```text
success
operation
request_id
profile
summary
warnings
errors
files
output_text
output_path
log_file
```

**Required structured error fields**

```text
code
message
category      # input, filter, safety, conflict, parse, write, config, internal
field
path
recoverable
```

**Exit gate**

CLI JSON, Tkinter status rendering, and Web JSON are all generated from the same service result without adapter-specific reinterpretation.

### B6. Ratify one unambiguous delivery-kit layout

The Build 100 spec lists payload files at zip root while also requiring `_bundletool_incoming`. The team standard and LET implementation place payload under the incoming folder.

**Required BFT kit layout**

```text
INSTALL_BUNDLETOOL_v2_1_100_build100_<slug>.bat
built_build100.md
team_build100.md
CHANGELOG_BFT_v2_1_100_build100.csv
_bundletool_incoming\
    _delivery\
        delivery_manifest.sha256
        delivery_markers.txt
        delivery_metadata.json
    VERSION.txt
    pyproject.toml
    requirements.txt
    bundle_config.json                  # only if approved as a managed payload
    src\...
    tests\...
    docs\...
    config\...
```

No application payload file may appear at zip root. Exactly one installer must appear at zip root.

The generic `BUILT.md` and `TEAM.md` names are retired for new deliveries. Existing legacy copies are retained as history until a separate cleanup decision.

### B7. Repair and upgrade the stager

The current BFT and LET stagers parse options using `shift` before capturing `%~dp0`. In Windows batch, `shift` changes positional argument zero. As a result, all documented options can make the script resolve the wrong root. The BFT `/dryrun` was directly observed resolving the root as `C:` and aborting.

**Required correction**

Capture immutable script location before argument parsing, or use `shift /1` so `%0` is preserved.

**Required BFT stager revision**

1. Exact project-folder guard.
2. Upgrade/bootstrap/recovery mode detection.
3. Immutable script-root capture before option parsing.
4. Create `archives` when absent, subject to approved project policy.
5. Snapshot before staging.
6. Archive to a temporary name.
7. Verify archive exists and is non-empty.
8. Promote temporary archive to final name.
9. Apply retention only after successful promotion.
10. Pre-extract Gate B that verifies:
    - exactly one installer;
    - required incoming folder;
    - required build/team/change documents;
    - no unexpected root-level payload.
11. Preserve governed recovery state after an aborted installer.
12. Extract and verify post-extract structure.
13. Move kit to archives.
14. Chain to installer unless `/norun`.
15. Return non-zero after installer failure.
16. Do not increment version/build.

**Dry-run contract**

`/dryrun` performs all read-only resolution and archive-list validation possible, reports the exact selected kit and intended snapshot/archive paths, and makes zero filesystem changes.

### B8. Identify a canonical installer template

The team standard requires a byte-identical helper block with `:hashVerify`, `:backup`, `:place`, `:grepHas`, and `:abort`. The supplied LET Build 104 installer has `:hashVerify`, `:place`, `:grepHas`, and `:abort`, but backup behavior is inline and there is no `:backup` helper.

**Required action**

1. Designate the actual ratified canonical helper block, or revise the standard to match the ratified implementation.
2. Store the canonical template under source control.
3. Record its SHA256 in the delivery standard.
4. Make the builder verify the helper-block hash before producing a kit.
5. Permit only parameter blocks, manifests, markers, gate commands, and success text to vary.

The LET installer is a behavioral reference until this reconciliation is complete.

### B9. Establish the test baseline

The historical selection manifest reports 13 pre-existing failures and a reconstructed `conftest.py`. The live tree now has `tests\conftest.py`, but no current authoritative full-suite result was provided.

The review environment could read the project but was not permitted by Windows to execute the user-installed Python runtime, so this review does not claim a current pass or fail count.

**Required action**

1. Recreate or repair the project virtual environment from declared dependencies.
2. Run the full suite without excluding legacy tests.
3. Record total, passed, failed, skipped, and duration.
4. Classify every failure as product defect, obsolete test, or environment defect.
5. Fix production monkeypatches in `writer.py`; do not modify built-ins to satisfy tests.
6. Re-run until the approved baseline is green.

**Exit gate**

Full `pytest` returns zero failures, and the result is captured in `built_build100.md`.

---

## 6. Delivery-standard implementation design

### 6.1 Permanent stager

`PREP_AND_STAGE_BFT.bat` remains the operator's only entry point. It is project-generic across builds and contains no build-specific file list or hashes.

### 6.2 Build-specific installer

The kit contains exactly one installer. It performs:

1. Project-root and incoming-folder guards.
2. Tool/runtime prerequisites.
3. Source/target version and stale-kit checks.
4. Manifest and marker-file validation.
5. Pre-mutation SHA256 verification for every payload file.
6. Backup of every existing target.
7. Placement of complete payload files.
8. Post-copy SHA256 verification.
9. Content-marker verification.
10. Version-contract verification.
11. Acceptance gates.
12. Success-only deletion of backups and incoming payload.

Any failure returns non-zero and retains backups plus incoming payload for recovery.

### 6.3 Delivery builder

Add `scripts\build_bft_delivery.py`. It must:

- require explicit target version, build, and slug;
- require a clean approved baseline;
- read a checked-in payload manifest;
- classify files as added or modified;
- calculate SHA256 hashes;
- validate marker safety;
- generate `delivery_manifest.sha256`;
- generate `delivery_markers.txt`;
- generate `delivery_metadata.json`;
- generate or parameterize the installer from the canonical template;
- verify the canonical helper-block hash;
- include build-stamped documentation;
- create exactly one correctly named zip;
- list and validate the finished archive;
- calculate the final zip SHA256;
- emit a machine-readable build report;
- never mutate the live application tree.

### 6.4 Delivery validator

Add `scripts\validate_bft_delivery.py`. It validates a kit without extraction into the live project:

- filename pattern;
- exactly one root installer;
- incoming-folder presence;
- root allow-list;
- manifest completeness;
- no duplicate or traversal paths;
- no unmanifested payload;
- no missing payload;
- hash correctness;
- marker-manifest coverage;
- build-document presence;
- installer helper-block hash;
- version/build consistency across filename, metadata, payload, and docs.

### 6.5 Installer acceptance gates for BFT

Minimum binding gates:

1. Python byte-compilation/import smoke for production modules.
2. Full `pytest` with zero failures.
3. CLI smoke:
   - `profiles --json`
   - canonical bundle
   - validate
   - dry-run unbundle
4. Canonical round trip for `plain_marker`, `md_fence`, and `jsonl`.
5. Version-contract test.
6. Direct-import boundary test proving adapters use the service facade.
7. Delivery recovery test in a disposable copy, not the live tree.

---

## 7. Application implementation work packages

### WP0 — Ratification and baseline normalization

**Owner:** John  
**Review:** George and Paul  
**Approval:** Ringo

Deliver:

- approved decision record for versioning, filtering, Web stack, and repo-awareness non-goal;
- clean Build 101 baseline commit used as Build 100 starting point;
- reconciled selection manifest;
- green full test baseline;
- retired or restored legacy verification assets;
- source-of-truth version module plan.

### WP1 — Delivery governance foundation

Deliver:

- `docs\TEAM_delivery_standard_v3.md`;
- canonical BFT installer template;
- repaired `PREP_AND_STAGE_BFT.bat`;
- `scripts\build_bft_delivery.py`;
- `scripts\validate_bft_delivery.py`;
- delivery-unit tests using disposable directories and synthetic kits.

No application feature payload is released from this package.

### WP2 — Core service facade

Deliver:

- `src\core\version.py`;
- `src\core\operations.py`;
- `src\core\service.py`;
- typed request/result/error contracts;
- service tests for discover, preview, create, parse, validate, plan, extract, config, logs, and version.

### WP3 — Profile completion

Deliver:

- deterministic profile registration;
- `src\core\profiles\jsonl.py`;
- canonical samples;
- three-profile round-trip and auto-detection tests;
- explicit ambiguity behavior when multiple detectors match.

### WP4 — Filtering completion

Deliver:

- extension-to-glob normalization;
- mandatory safety-deny layer;
- discovery reason codes;
- `discover_file_types`;
- config migration rules;
- CLI extension flags;
- parity tests for config, CLI, Tkinter, and Web behavior.

### WP5 — CLI adapter

Deliver:

- facade-only CLI handlers;
- `profiles` command;
- structured `--json` output;
- stable exit-code table;
- preserved legacy command syntax;
- CLI boundary and regression tests.

### WP6 — Tkinter adapter

Deliver:

- facade-only bundle and unbundle frames;
- settings tabs;
- file-type checklist;
- status/error rendering from structured service results;
- background execution/progress handling for long operations;
- manual smoke record plus automated contract tests where practical.

### WP7 — Web adapter

Deliver:

- local Flask application and launcher;
- specified endpoints;
- stable DOM IDs and `showTab(tabName, buttonEl)`;
- file-type checklist endpoint and controls;
- confirmation for write operations;
- endpoint, request-size, path-safety, and parity tests.

### WP8 — QA/QC freeze and Build 100 kit

Deliver:

- full test report;
- code catalog comparison;
- relationship/API-to-UI mapping;
- element-loss catalog;
- changelog CSV;
- updated specifications;
- `built_build100.md`;
- `team_build100.md`;
- validated delivery zip and SHA256;
- successful `/dryrun`;
- successful install and recovery rehearsal in a disposable clone;
- final team approval.

---

## 8. Expanded acceptance matrix

| Test ID | Area | Acceptance |
|---|---|---|
| BFT-B100-001–015 | Original spec | Retain after correcting table formatting and assigning one scenario/result per ID. |
| BFT-B100-016–019 | Filtering | Retain Addendum tests for PDF inclusion, CLI override, discovery counts, and UI/CLI manifest parity. |
| BFT-B100-020 | Version | All runtime and packaging version surfaces equal `2.1.100`. |
| BFT-B100-021 | Filtering migration | A current config migrates without silent broadening or narrowing unless the approved migration explicitly says so. |
| BFT-B100-022 | Error taxonomy | Excluded-by-choice and blocked-by-safety are distinct structured outcomes in all three UIs. |
| BFT-B100-023 | Service boundary | CLI/Tkinter/Web contain no direct parser/writer/profile construction. |
| BFT-B100-024 | Delivery options | `/dryrun`, `/y`, and `/norun` preserve the correct script root. |
| BFT-B100-025 | Dry run | Dry run makes no filesystem changes. |
| BFT-B100-026 | Gate B | Missing incoming payload is rejected before extraction. |
| BFT-B100-027 | Gate B | Zero or multiple installers are rejected before extraction. |
| BFT-B100-028 | Archive safety | Traversal, absolute, duplicate, and unexpected root paths are rejected. |
| BFT-B100-029 | Pre-hash | Tampered staged payload is rejected before live-tree mutation. |
| BFT-B100-030 | Post-hash | Copy corruption is detected before acceptance. |
| BFT-B100-031 | Marker | Missing or unsafe markers fail the kit validator or installer. |
| BFT-B100-032 | Abort recovery | Failed acceptance retains backups and incoming payload. |
| BFT-B100-033 | Resume | Corrected installer can resume a governed aborted installation without destroying the original backups. |
| BFT-B100-034 | Stale kit | Installer refuses an incompatible source version or already-installed target. |
| BFT-B100-035 | Success teardown | Backups and incoming payload are removed only after every binding gate passes. |
| BFT-B100-036 | Build identity | Kit filename, installer banner, metadata, docs, payload, and installed runtime agree. |
| BFT-B100-037 | Full suite | Full `pytest` returns zero failures. |
| BFT-B100-038 | Round trip | All three profiles restore canonical files with expected content, encoding, and EOL. |
| BFT-B100-039 | UI parity | Equivalent requests produce equivalent manifests/results in CLI, Tkinter, and Web. |
| BFT-B100-040 | Installer template | Helper-block SHA256 equals the ratified canonical value. |

---

## 9. Definition of Ready

Application development may begin when all of the following are true:

- Ringo approves Build 100 mandatory scope and explicit non-goals.
- George approves service contract, filtering precedence, default posture, and Flask choice.
- John produces a clean approved baseline.
- Version policy is changed to package-owned identity or another single unambiguous policy is ratified.
- The full current test suite is green or every exception has a written, approved disposition.
- The delivery standard names a canonical installer template and helper hash.
- The BFT stager's option/root defect is fixed and tested.
- The kit layout is ratified.

---

## 10. Definition of Done

Build 100 is done only when:

- service, CLI, Tkinter, and Web acceptance tests pass;
- all three profiles pass canonical round trips;
- filtering behavior and migration are proven;
- no adapter bypasses the service facade;
- no production runtime monkeypatches Python built-ins;
- full `pytest` reports zero failures;
- the code catalog reports no unreviewed element loss;
- build/team/changelog documents are build-stamped;
- the kit validator passes;
- stager dry run passes with zero changes;
- disposable install, failure, recovery, and success rehearsals pass;
- installed version identity is exact;
- Ringo, George, John, and Paul record approval.

---

## 11. Recommended immediate team decision

Approve the architecture, but do not start feature coding in the live tree yet.

Authorize **WP0 — Ratification and baseline normalization** first. Once its exit gates are met, begin **WP1 — Delivery governance foundation** and **WP2 — Core service facade** as separate reviewed change sets. This preserves the strong Build 100 design while preventing the current version, baseline, and delivery contradictions from becoming code.

