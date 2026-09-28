# BFT Build 115 — GAPs and Potential Issues Register

**Analyst:** Paul (lead analyst pseudonym)  
**For:** Ringo, George (Lead Architect), and John (Lead Developer)  
**Review date:** 2026-08-26  
**Overall risk:** **High until P0 findings are closed and a reproducible candidate is re-verified**

## 1. Severity and evidence conventions

- **P0 — Critical:** can make the approved selection materially different from the artifact, defeat a primary safety objective, or invalidate release acceptance.
- **P1 — High:** major user-visible failure, contract violation, or release/governance defect requiring correction before general release.
- **P2 — Medium:** important completeness, reliability, performance, accessibility, or maintainability issue that should be scheduled and gated.
- **P3 — Low:** localized polish or defensive-hardening item.

Evidence labels:

- **B115 confirmed** — explicitly documented as a Build 115 defect in `built_build116.md`;
- **current confirmed** — reproduced or source-traced in the current Build 116 superset;
- **current potential** — credible source-traced edge that needs a dedicated reproducer or product decision;
- **governance** — concerns provenance, configuration, specification, or release controls.

## 2. Summary register

| ID | Severity | Finding | Evidence | Build 116 status |
|---|---:|---|---|---|
| BFT115-GAP-001 | P0 | Default `bundle` bypasses the canonical selection service | Current confirmed by direct CLI probe | **Open** |
| BFT115-GAP-002 | P0 | Plan and artifact can diverge after deletion, oversize, or read failure | Current confirmed by direct creation probes | **Open** |
| BFT115-GAP-003 | P1 | Build 115 exact source/artifact is not reproducible | Governance/source inventory | **Open** |
| BFT115-GAP-004 | P0 | Stale extracted bundle header blocks ordinary project | B115 confirmed | **Fixed in 116** |
| BFT115-GAP-005 | P1 | Workspace panes have no scrollbars | B115 confirmed | **Fixed in 116** |
| BFT115-GAP-006 | P1 | Decision list is a flat 1,100-row surface | B115 confirmed | **Improved in 116** |
| BFT115-GAP-007 | P2 | No hide-blocked view | B115 confirmed | **Fixed in 116** |
| BFT115-GAP-008 | P1 | Outside-base and other emission invariants are not blocked at plan time | Current confirmed | **Open** |
| BFT115-GAP-009 | P1 | UI performance claim measures the model, not the user-visible Tk operation | Current confirmed | **Open** |
| BFT115-GAP-010 | P2 | Decision tree is hierarchical but not virtualized | Current confirmed | **Open** |
| BFT115-GAP-011 | P1 | Rule schema and editor are materially below the interim Revision 1.1 contract | Current confirmed | **Open** |
| BFT115-GAP-012 | P1 | Accessibility semantics and focus behavior are incomplete | Current confirmed/source trace | **Open** |
| BFT115-GAP-013 | P1 | Shipped governed config is hash-valid but schema-invalid | Current confirmed | **Open** |
| BFT115-GAP-014 | P1 | Workspace Copy Bundle menu calls a missing method | Current confirmed/source trace | **Open** |
| BFT115-GAP-015 | P2 | Unreadable-directory warning can be non-serializable | Current potential/source trace | **Open** |
| BFT115-GAP-016 | P2 | Declared wheel omits the runnable application | Current confirmed by wheel inspection | **Open** |
| BFT115-GAP-017 | P2 | Reports lack full post-creation and aggregate reconciliation | Current confirmed/source trace | **Open** |
| BFT115-GAP-018 | P2 | Formal Revision 1.1 schema/persona artifacts are absent | Governance | **Open** |
| BFT115-GAP-019 | P2 | Project-vs-CLI precedence wording is ambiguous | Contract/source comparison | **Open decision** |
| BFT115-GAP-020 | P2 | Build 116 nested-header basename heuristic has a false-negative edge | Current potential | **Introduced/residual in 116** |
| BFT115-GAP-021 | P2 | Configuration format validation can disagree with formatter registry | Current confirmed/source trace | **Open** |
| BFT115-GAP-022 | P2 | Project rule-file preset requests are not applied | Current confirmed/source trace | **Open** |
| BFT115-GAP-023 | P2 | Bounded Preview Output experience is not complete in the workspace | Current confirmed | **Open** |
| BFT115-GAP-024 | P2 | Repository/QC/project-manager metadata do not form a clean release gate | Governance | **Open** |
| BFT115-GAP-025 | P3 | Validate Bundle GUI command is still a placeholder | Current confirmed | **Open** |

## 3. Detailed findings

### BFT115-GAP-001 — Default bundle bypasses canonical selection

**Severity:** P0  
**Evidence:** current confirmed

`src/cli.py::_uses_selection_workspace()` routes a `bundle` command to `SelectionService` only if a selection-specific flag is present. With no such flag, it calls legacy `BundleCreator`. `plan` always uses the service.

In a direct fixture, default `plan` selected only `app.py`, while default `bundle` emitted `app.py` plus three files under an environment detected as `.venv312`. The classic GUI path also invokes legacy `BundleCreator` and remains enabled through governed configuration.

**Impact:** The product has two default selection truths. Users can review a safe plan and then create a different bundle, or use classic mode and unknowingly leak environment content, credentials, binaries, caches, or large generated trees. Cross-surface parity is false.

**Required disposition:** All bundle-producing adapters must call the same service for all invocations, including the no-flag default. Preserve any legacy semantics as an explicit named compatibility profile, never as an implicit engine switch.

### BFT115-GAP-002 — Plan-to-artifact drift is not reconciled

**Severity:** P0  
**Evidence:** current confirmed

After planning, `BundleCreator.create_manifest()` can silently continue over missing/read-failed files and can skip oversize files. The original plan remains Included. Direct probes showed a deleted planned file and an oversize planned file both producing a successful zero-file artifact without a reconciled selection decision. `STALE` and `SKIPPED` states are defined but unused.

**Impact:** Approval and review do not prove artifact contents. Automated consumers cannot distinguish an intentional empty selection from filesystem drift. SEL-F006 cannot be satisfied.

**Required disposition:** Choose and enforce one contract:

1. strict snapshot — fingerprint selected metadata and abort creation on any change; or
2. reconciled final plan — convert every mutation/skip into `STALE`, `SKIPPED`, `UNKNOWN`, or `BLOCKED`, require renewed approval where appropriate, and serialize the final plan with the manifest.

For governed use, strict snapshot plus an explicit re-plan is simpler and safer.

### BFT115-GAP-003 — Build 115 cannot be reproduced

**Severity:** P1  
**Evidence:** governance

The working tree is 2.1.116, has broad uncommitted/untracked content, and has no Build 115 tag or immutable source kit. The generic current commit does not identify the released tree.

**Impact:** Test counts, file contents, installation behavior, and defect provenance cannot be independently audited. A later repair cannot be diffed reliably against what users actually installed.

**Required disposition:** Cut a clean signed/tagged candidate, retain source and installer artifacts, and publish SHA-256 hashes plus the exact command/environment used to build and test them.

### BFT115-GAP-004 — Stale extracted header false-positive block

**Severity:** P0 for Build 115  
**Evidence:** B115 confirmed

Build 115 treated a complete-looking bundle header anywhere in a source file as evidence that the file itself was a nested bundle. On the 1,115-file field project, an extracted file retained a historical header and the workspace blocked the project.

**Impact:** Ordinary source trees become unbundleable with no valid user override because hard safety is intentionally non-overridable.

**Build 116 disposition:** Fixed by distinguishing a header that names its own stored file from a stale header. The residual basename edge is tracked separately as GAP-020.

### BFT115-GAP-005 — Missing workspace scrollbars

**Severity:** P1 for Build 115  
**Evidence:** B115 confirmed

The folder, decision, and detail/rules panes lacked scrollbars.

**Impact:** Large projects and long reason chains are not fully navigable, including by keyboard-only users.

**Build 116 disposition:** Fixed with vertical scrollbars.

### BFT115-GAP-006 — Flat large decision list

**Severity:** P1 for Build 115  
**Evidence:** B115 confirmed

Build 115 displayed roughly 1,100 file decisions as a single flat list.

**Impact:** The interface does not scale cognitively or operationally; folder context and bulk reasoning are obscured.

**Build 116 disposition:** Improved with a nested folder tree. All rows are still inserted, so scalability remains incomplete under GAP-010.

### BFT115-GAP-007 — No hide-blocked filter

**Severity:** P2 for Build 115  
**Evidence:** B115 confirmed

Blocked environment content dominated the view with no way to suppress it.

**Impact:** Relevant included/excluded decisions are difficult to inspect, particularly on environment-heavy projects.

**Build 116 disposition:** Fixed with a `Hide Blocked` control.

### BFT115-GAP-008 — Emission invariants do not all appear in the plan

**Severity:** P1  
**Evidence:** current confirmed

A source outside the selected base was planned as `Included` with a relative path such as `../source/planned.txt`, then rejected during creation. The interim contract specifically requires all known emission-blocking invariants to appear in the plan. Active output self-inclusion and post-normalization containment also need a single plan-time authority.

Rule-file patterns are likewise not rejected for absolute or parent-traversal forms, despite the interim schema direction. A pattern alone does not manufacture a path, so this is not by itself proof of traversal exploitation; it is evidence that the policy boundary is not validated where the contract places it.

**Impact:** Preview/review can approve an artifact that cannot be emitted. Containment reasoning is split between planner and writer.

**Required disposition:** Normalize and resolve every candidate relative to a declared source root and output target during planning; emit an immutable P0 block with a reason code for outside-root, active-output, path-collision, unsafe normalization, and other known writer rejections.

### BFT115-GAP-009 — UI performance gate measures the wrong layer

**Severity:** P1  
**Evidence:** current confirmed

The reported ~128 ms result times `WorkspaceModel.set_folder()`. The actual Tk space-key handler calls `refresh_all()` and rebuilds every workspace pane. Five local 4,000-file toggles took approximately 514–597 ms.

**Impact:** A reported acceptance pass does not represent user-perceived latency. Larger projects will amplify the issue, and full refresh also harms focus stability.

**Required disposition:** Instrument keypress-to-idle-render latency with real Tk, report median and p95, and enforce the accepted viewport budget on a controlled reference machine. Update only affected rows/summary values.

### BFT115-GAP-010 — Hierarchy without virtualization

**Severity:** P2  
**Evidence:** current confirmed

Build 116's hierarchy collapses content visually but still inserts all nodes; the 4,000-file probe created 4,041 decision-tree items. Search/trace refreshes are synchronous.

**Impact:** Initial render, every bulk toggle, search, and recompute remain O(number of visible-plan records) at the widget layer. Very large projects can freeze the event loop.

**Required disposition:** Use lazy child population or a virtual/windowed list and preserve a complete programmatically addressable model outside the widget, as required by the accessibility/performance addendum.

### BFT115-GAP-011 — Rule contract and editor are incomplete

**Severity:** P1  
**Evidence:** current confirmed

The interim Revision 1.1 direction calls for `schema_version`, base action, unique ordered IDs, enabled/action/typed-match/group fields, safe relative paths, unknown-field preservation, and explicit save targets. The loader implements `version: 1` and flat glob patterns. The editor can add one include/exclude session glob, clear all overrides, and export action/pattern pairs.

Missing behavior includes typed matchers, ID uniqueness, safe-path validation, unknown-field round trip, base action, reorder, full field editing, personal preset save/update, and persistence. Formal Revision 1.1/JSON Schema is also absent.

**Impact:** Project files authored to the agreed interim direction are incompatible; UI and file contract can drift; unknown future fields are lost; operators cannot perform the specified rule workflow.

**Required disposition:** Ratify one schema, generate validation/models from it, support lossless load/save, and make CLI/UI use that same model. Do not accept both shapes silently without an explicit migration.

### BFT115-GAP-012 — Accessibility semantics and focus retention

**Severity:** P1  
**Evidence:** current confirmed/source trace

Tri-state selection is rendered as text (`[x]`, `[-]`, `[ ]`) in `ttk.Treeview`, not as native accessible checkbox state. Model `accessible_text()` strings are testable descriptions but do not expose programmatic state through a platform accessibility API. `refresh_all()` deletes and recreates rows, so focus and selection are not retained. Selecting a folder row toggles expanded state, making ordinary keyboard navigation mutate the view.

No live summary announcement, high-contrast/scaling verification, or screen-reader automation/manual acceptance evidence was found.

**Impact:** Keyboard-only and assistive-technology users may lose place, hear incomplete semantics, or unintentionally change view state. This violates explicit design acceptance, not merely polish.

**Required disposition:** Establish an accessibility mapping for state/role/name, separate selection from expand/collapse, restore stable focused IDs after incremental recompute, and execute a documented keyboard plus screen-reader acceptance script.

### BFT115-GAP-013 — Governed configuration is invalid

**Severity:** P1  
**Evidence:** current confirmed

`check_config_integrity()` passes, but `validate()` fails because `global_settings.ui_layout.buttons_position` is missing. The installer Gate E checks integrity but not the complete schema.

**Impact:** The release can certify an untampered but invalid governed configuration. Future code paths that rely on the missing property may fail or silently default differently.

**Required disposition:** Correct the config or schema, make startup and installer execute the same full validation, and retain digest checking as a separate tamper gate.

### BFT115-GAP-014 — Copy Bundle menu integration crash

**Severity:** P1  
**Evidence:** current confirmed/source trace

The main window enables **Copy Bundle to Clipboard** and calls `self.bundle_frame.copy_to_clipboard()`. `SelectionWorkspaceFrame` has no such method.

**Impact:** The enabled command raises `AttributeError` in the default workspace mode. It demonstrates that main-window/mode seams are outside current coverage.

**Required disposition:** Define a common frame capability interface, disable commands when unsupported, and add an integration test that invokes every enabled main-menu command in both modes.

### BFT115-GAP-015 — Unreadable-directory warning serialization

**Severity:** P2  
**Evidence:** current potential/source trace

`os.walk(onerror=result.warnings.append)` appends an `OSError` object to a collection later treated as strings and serialized to JSON. The same branch does not create the specified Unknown/Blocked directory decision.

**Impact:** A permission error can turn a recoverable scan warning into report serialization failure or invisible omission.

**Required disposition:** Convert the error to a stable serializable warning record, create a decision for the unreadable root, and test on both POSIX permissions and Windows access-denied mocks.

### BFT115-GAP-016 — Wheel is not the application

**Severity:** P2  
**Evidence:** current confirmed

The declared wheel includes only `core*`; UI, top-level CLI/main modules, and database are absent. Entry points are commented out, and `README.md` is missing despite being declared. A no-network build succeeded with a missing-README warning, and wheel inspection confirmed the omission.

**Impact:** `pip install` creates a package that cannot launch the documented application. Support and reproducibility differ between source-copy and Python-package deployments.

**Required disposition:** Either complete packaging with all runtime modules, data, and entry points, or explicitly declare the wheel as an internal core-only artifact and prevent it from being mistaken for BFT.

### BFT115-GAP-017 — Review/report aggregation and final reconciliation

**Severity:** P2 (P0 aspect covered by GAP-002)  
**Evidence:** current confirmed/source trace

Current reports provide useful totals, pruned roots, overrides, confirmations, blocks, warnings, decisions, and emission information. They do not fully aggregate by rule/group/file family or merge final missing/read-error/oversize results into the decision stream.

**Impact:** Operators must inspect long lists to understand why a project changed, and archival reports cannot prove exact artifact correspondence.

**Required disposition:** Define a single final-report schema keyed to the artifact manifest, with totals and grouped deltas derived from that same immutable record.

### BFT115-GAP-018 — Missing Revision 1.1 and persona fixtures

**Severity:** P2  
**Evidence:** governance

Paul's team communication promises an integrated Revision 1.1, formal JSON Schema, and two executable persona fixtures before WP1/WP2 acceptance. The repository contains the interim communication and John's agreement, but those promised governed artifacts were not located.

**Impact:** Developers and reviewers can reasonably implement different contracts. Acceptance becomes interpretive rather than executable.

**Required disposition:** Publish and checksum the integrated spec, schema, and fixtures; make the fixture results a release gate.

### BFT115-GAP-019 — Project/CLI layer ambiguity

**Severity:** P2  
**Evidence:** contract/source comparison

The engine evaluates project rules before CLI rules, and first match wins; tests explicitly preserve project policy over a CLI flag. Team wording says CLI is evaluated after project rules “so command line can refine project policy,” which can also be read as CLI override precedence.

**Impact:** A user may expect a CLI emergency override that the engine intentionally refuses, or a future maintainer may reverse the order believing they are fixing it.

**Required disposition:** State the rule unambiguously: either project policy constrains CLI, or later CLI rules override project policy except P0. Add a named acceptance example.

### BFT115-GAP-020 — Build 116 header-basename false negative

**Severity:** P2  
**Evidence:** current potential

The Build 116 stale-header heuristic compares only basenames. A real single-entry nested bundle whose stored path and declared source have different directories but the same basename may be labeled stale and allowed.

**Impact:** The fix for Build 115's false positive could miss a genuine nested artifact and permit recursive/self-hosted bundle content.

**Required disposition:** Parse and validate the full normalized declared/stored path relationship and require corroborating bundle structure, not basename equality alone. Add adversarial single-entry tests.

### BFT115-GAP-021 — Config format allow-list differs from runtime registry

**Severity:** P2  
**Evidence:** current confirmed/source trace

Profile validation accepts `jsonl`, but the registered current profile formats are different. Two independent allow-lists can drift.

**Impact:** A configuration can pass validation and fail when the formatter is selected.

**Required disposition:** Derive validation choices from the formatter registry or a single shared schema authority.

### BFT115-GAP-022 — Requested presets become notices only

**Severity:** P2  
**Evidence:** current confirmed/source trace

`load_rules_file()` reads a `presets` array and adds a notice such as “requests presets,” but does not add the requested preset rules. A caller can see the declaration without receiving its selection effect.

**Impact:** Project policy looks self-contained but produces a different plan unless the same preset is also supplied through another surface.

**Required disposition:** Either apply and digest declared presets through the canonical resolver or reject the field with a clear message. Do not acknowledge without effect.

### BFT115-GAP-023 — Bounded Preview Output is incomplete

**Severity:** P2  
**Evidence:** current confirmed

The service has bundle-preview capability, and the legacy UI has preview concepts, but the Selection Workspace does not provide the agreed distinct on-demand output-preview experience bounded to 10 files/50 KB with explicit truncation. Rule-match preview is not output preview.

**Impact:** Users can review decisions but cannot inspect a safely bounded representation of what formatting will emit before creation.

**Required disposition:** Add the specified tab/action backed by the service and gate its file/byte limits with tests.

### BFT115-GAP-024 — Release governance is conditionally open

**Severity:** P2  
**Evidence:** governance

The latest stored `.pyprojectmgr` QC report is marked failed with 135 issues (14 errors, 120 warnings, one information item). Some errors appear to be analyzer false positives, but no clean superseding report is present. The project manifest and project spec disagree about entry points/infrastructure, and the active header-policy version does not cleanly reflect earlier WP0 statements.

**Impact:** A release gate cannot be distinguished from stale tool output, accepted exceptions, or unresolved defects. Automated project management can act on inconsistent metadata.

**Required disposition:** Re-run canonical QC on an immutable candidate, disposition false positives by rule/version, reconcile project metadata, and retain one passing or explicitly waived signed result.

### BFT115-GAP-025 — Validate Bundle GUI placeholder

**Severity:** P3  
**Evidence:** current confirmed

The main-window Validate Bundle command displays “Feature Not Implemented,” although validation exists in core/CLI paths.

**Impact:** GUI capability is incomplete and parity is confusing.

**Required disposition:** Wire it to the shared validation service or disable/remove it until supported.

## 4. Foreseeable systemic risks

The individual findings combine into several larger risks:

1. **False confidence risk:** high test count and coverage can mask untested adapter seams and mis-scoped benchmarks.
2. **Sensitive-content risk:** the default legacy bundle path can include detected environment or generated content that the reviewed plan excludes.
3. **Audit risk:** pre-creation reports cannot prove final artifact contents when files change or are skipped.
4. **Policy drift risk:** the written schema direction, loader, editor, and CLI each expose overlapping but non-identical rule vocabularies.
5. **scale risk:** the full immutable model is appropriate, but recreating the full widget tree on every action couples correctness recomputation to UI latency and focus loss.
6. **release-recovery risk:** without an immutable Build 115 source kit, fixes cannot be applied or audited against the precise installed baseline.

## 5. Related deliverables

- [Project alignment analysis](BFT_BUILD115_PROJECT_ALIGNMENT_ANALYSIS.md)
- [Accuracy analysis](BFT_BUILD115_ACCURACY_ANALYSIS.md)
- [Completeness analysis](BFT_BUILD115_COMPLETENESS_ANALYSIS.md)
- [Conclusions](BFT_BUILD115_CONCLUSIONS.md)
- [Recommendations](BFT_BUILD115_RECOMMENDATIONS.md)
