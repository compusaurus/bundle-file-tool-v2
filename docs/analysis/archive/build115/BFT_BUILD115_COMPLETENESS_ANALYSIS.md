# BFT Build 115 — Completeness Analysis

**Analyst:** Paul (lead analyst pseudonym)  
**For:** Ringo, George (Lead Architect), and John (Lead Developer)  
**Review date:** 2026-08-26  
**Assessment:** **A substantial WP1–WP4 increment, but functionally and contractually incomplete for full v2.2 acceptance**

## 1. Scope calibration

The current Build 116 superset contains 40 Python source files (about 15,043 physical lines) and 72 Python test files (about 19,820 physical lines). The verified suite contains 1,402 passing tests. This is a serious implementation, not a prototype shell.

Completeness must nevertheless be measured against the requested product contract, not code volume or test count. Build 115's own record explicitly defers WP5 cache persistence and WP6 personal-preset/group persistence. In addition, several WP1–WP4 acceptance details remain incomplete or are only partially connected end to end.

## 2. Work-package completeness

### 2.1 WP1 — Selection core: substantially complete

Delivered:

- immutable selection-plan and decision data structures;
- Included, Excluded, Blocked, Skipped, Unknown, and Stale state vocabulary, plus separate ambiguity and confirmation metadata;
- deterministic layer ladder and order;
- include/exclude/block actions;
- full reason chains and visible winning rules;
- relative path normalization and deterministic emission order;
- groups, rule-source digests, warnings, confirmations, and pruned-root metadata;
- glob matching with `**` support;
- strong unit coverage of layer behavior and selection decisions.

Incomplete or dormant:

- `STALE` and `SKIPPED` are declared but not produced;
- plan-time outside-base/output/self-ingestion safety is incomplete;
- matcher types are represented as a single glob `pattern`, not typed `glob`, `path`, `extension`, `detector`, and `size` match objects;
- no final snapshot-reconciliation contract ensures the plan remains authoritative during creation.

### 2.2 WP2 — Detectors and service: substantially complete on the new path

Delivered:

- metadata scanning that avoids full-content reads during planning;
- environment evidence detection;
- nested-bundle, generated/minified, binary, VCS, and related selection sources;
- project, CLI, preset, detector, and session rule composition;
- deterministic plan/report service methods;
- progress and cancellation support;
- source digesting and notices.

Incomplete:

- default `bundle` and classic GUI do not consistently call the service;
- unreadable directories do not become the specified Unknown/Blocked root decisions;
- `os.walk` errors may enter a string warning collection as raw `OSError` objects;
- nested-header classification remains heuristic rather than structurally validated;
- project-file `presets` requests are announced but not actually applied by `load_rules_file()`.

### 2.3 WP3 — CLI and reporting: partially complete

Delivered:

- `plan` verb with text, JSON, and list output;
- selection-aware `bundle` when selection flags are present;
- shared option vocabulary for base action, rules, presets, include/exclude, groups, review output, and progress;
- clean machine-readable stdout behavior;
- cancellation and progress contract;
- report generation and deterministic JSON serialization;
- output format and validation infrastructure in the legacy/core product.

Incomplete:

- default `bundle` parity with default `plan`;
- one authoritative adapter path for all CLI invocations;
- post-creation report/manifest reconciliation;
- complete stale, skipped, oversize, missing, and read-error presentation;
- aggregate summaries by rule, group, and file family;
- an installed console entry point in `pyproject.toml`.

### 2.4 WP4 — Tk selection workspace: substantial but incomplete

Delivered in the current Build 116 superset:

- main-window workspace integration and a governed classic/workspace mode;
- folder and decision trees with tri-state text indicators;
- summary counts, search, detail/trace pane, rules-in-effect surface, reset/undo/redo, review report, and create workflow;
- real Tk integration tests;
- Build 116 fixes for the four confirmed Build 115 field defects: stale extracted-header handling, pane scrollbars, hierarchical decisions, and hide-blocked filtering.

Incomplete against the design:

- no native checkbox accessibility semantics;
- selection refresh deletes/reinserts all rows and does not preserve focus/selection;
- no virtualization/windowing for large decision lists;
- actual Tk toggle cost is not within the stated 150 ms budget in the local 4,000-file probe;
- rule editor is a small session-override dialog rather than the specified full ordered-rule editor;
- no personal-preset save path;
- no complete bounded **Preview Output** tab limited to 10 files/50 KB with an explicit truncation boundary;
- main-window Copy Bundle integration calls a method missing from `SelectionWorkspaceFrame`;
- main-window Validate Bundle remains a “Feature Not Implemented” dialog despite core/CLI validation capability;
- screen-reader/live-region behavior, high-contrast scaling, and focus-retention acceptance are not demonstrated;
- merely selecting a folder-tree row toggles its expanded model state and refreshes the view, which conflicts with predictable arrow-key navigation.

### 2.5 WP5 — Cache: not delivered

The specification requires cache-assisted and cold plans to be byte-identical, with a safe invalidation strategy and measurable large-project behavior. Build 115 explicitly defers this work. No full acceptance can be claimed while the quality gate that compares cold and cached plans is absent.

### 2.6 WP6 — Persistence: not delivered

The specification requires personal presets outside the governed project root, safe corrupt-file handling, explicit project opt-in, and persisted group state. Build 115 explicitly defers personal preset and group persistence. The current editor only exports a project rule file; it does not provide the required personal lifecycle.

## 3. Acceptance-criteria completeness

### 3.1 Functional acceptance

| Criterion | Result | Basis |
|---|---|---|
| SEL-F001: default plan excludes environment artifacts by evidence | **Pass for `plan`/service; fail for default `bundle`** | Direct probe showed the plan excluded `.venv312`, while default bundle emitted it |
| SEL-F002: visible decision state, winning rule/layer, reason chain, group, size, emission | **Substantial pass** | Model and detail/report surfaces expose these fields |
| SEL-F003: scoped manual override preserves unrelated decisions | **Pass at model level** | Unit/integration coverage exercises folder/file overrides and undo/redo |
| SEL-F004: summary counts match visible plan | **Pass for the pre-creation plan** | Model tests reconcile counts; post-creation divergence remains |
| SEL-F005: deterministic groups with no duplicate membership | **Pass** | Group construction and ordering are tested |
| SEL-F006: text/JSON reports reconcile exactly with final manifest/skips | **Fail end to end** | Missing and oversize files can disappear after the report plan is formed |

### 3.2 Cross-surface acceptance

| Criterion | Result | Basis |
|---|---|---|
| SEL-X001: service, CLI, and Tk produce the same ordered decisions | **Partial/fail** | New paths share the service; default bundle and classic GUI bypass it |
| SEL-X002: adapters do not reimplement selection logic | **Fail** | Legacy `BundleCreator` discovery remains an active adapter behavior |

### 3.3 Governance acceptance

| Criterion | Result | Basis |
|---|---|---|
| SEL-GOV-001: runtime does not write governed config | **Substantial pass** | Write protections and digest tests exist |
| SEL-GOV-002: personal presets live outside root and corruption fails safely | **Not delivered** | WP6 deferred |
| SEL-GOV-003: project rules are explicit opt-in | **Pass** | Rule file is inactive unless supplied; UI export does not auto-arm it |
| SEL-GOV-004: integrity, oversize, cancellation, and stdout gates pass | **Partial** | Cancellation/stdout behavior is strong; config schema validation fails; oversize is not reconciled into the plan |

### 3.4 Quality acceptance

| Quality gate | Result |
|---|---|
| Existing bundle/unbundle round trips | Covered by the broader regression suite |
| Cold/cache byte identity | Not delivered (WP5) |
| No skipped Tk tests | Pass in the verified environment |
| Windows/POSIX separators, Unicode, spaces, nested bundles, multiple sources | Broad coverage exists, though exact formal Revision 1.1 fixtures were not found |
| Both named personas executable | Not demonstrated as the promised governed persona fixtures |
| Actual usable Tk viewport performance | Not demonstrated; local direct probe misses the stated target |

## 4. Rule-system completeness

The interim Revision 1.1 direction defines a formal object with `schema_version`, name, base action, ordered uniquely identified rules, enabled state, action, a typed `match` object, and group membership. It also requires safe relative POSIX paths, rejection of absolute/`..` patterns, loud failure for unsupported versions, and preservation of unknown fields.

The implementation instead supports:

```json
{
  "version": 1,
  "allow": ["src/**"],
  "deny": ["**/*.log"],
  "rules": [
    {"action": "exclude", "pattern": "docs/**", "label": "drafts", "group": "docs"}
  ]
}
```

It is usable, but incomplete relative to the governing direction:

- numeric `version` rather than string `schema_version`;
- no `base_action` application;
- flat glob only, no typed match object;
- no ID uniqueness check;
- no absolute/parent-traversal rejection;
- unknown fields are discarded, not preserved;
- requested nested presets become a notice only;
- the Tk editor cannot manage most supported fields and exports only session action/pattern pairs.

The source comment itself says Paul's formal JSON Schema is pending. The promised Revision 1.1 schema file was not located, so this contract remains both incompletely specified in the repository and incompletely implemented.

## 5. Distribution and operational completeness

The batch installer is the real operational deployment mechanism. As a Python project, however, the package definition is incomplete:

- `pyproject.toml` references a missing `README.md`;
- package discovery includes only `core*`;
- UI, CLI, `main`, `cli_plan`, `cli_progress`, and database modules are absent from the built wheel;
- project scripts/entry points are commented out;
- a wheel built successfully only with a warning, and inspection confirmed it contained only `core/*` plus distribution metadata.

A pip-installed wheel therefore does not reproduce the source application. If pip distribution is intentionally unsupported, the metadata should say so and the wheel build should be disabled or scoped as an internal core library. If it is supported, packaging is incomplete.

## 6. Documentation and release completeness

Present:

- extensive build records and team handoff records;
- the design specification and interim decision correspondence;
- WP0 baseline and QC documents;
- installation automation for Build 116;
- strong in-code contracts and test descriptions.

Missing or unresolved:

- immutable Build 115 source tag/archive and checksum ledger;
- Build 115 kit in the working copy;
- formal integrated Specification Revision 1.1;
- formal JSON Schema artifact;
- executable governed persona fixtures explicitly promised before WP1/WP2 acceptance;
- a clean, passing canonical QC release report;
- a consistent `.pyprojectmgr` entry-point/infrastructure declaration;
- a valid top-level README required by packaging metadata.

## 7. Completeness conclusion

Build 115 is **substantively complete as an implementation milestone for much of WP1–WP4**, especially the core selection model, detectors, service, CLI planning, and initial Tk workspace. It is **not complete as the final BFT v2.2 Selection Workspace release**.

The distinction matters: WP5/WP6 were knowingly deferred, while several WP1–WP4 items—default adapter parity, artifact reconciliation, full rule editor/schema, accessibility semantics, true UI performance, and a few main-window integrations—remain unfinished. Build 116 improves the WP4 field usability baseline but does not close the full acceptance set.

## 8. Related deliverables

- [Project alignment analysis](BFT_BUILD115_PROJECT_ALIGNMENT_ANALYSIS.md)
- [Accuracy analysis](BFT_BUILD115_ACCURACY_ANALYSIS.md)
- [Gaps and potential issues](BFT_BUILD115_GAPS_AND_POTENTIAL_ISSUES.md)
- [Conclusions](BFT_BUILD115_CONCLUSIONS.md)
- [Recommendations](BFT_BUILD115_RECOMMENDATIONS.md)
