# BFT Build 115 — Project Alignment Analysis

**Analyst:** Paul (lead analyst pseudonym)  
**For:** Ringo, George (Lead Architect), and John (Lead Developer)  
**Review date:** 2026-08-26  
**Assessment:** **Partially aligned; not ready to claim full BFT v2.2 Selection Workspace conformance**

## 1. Scope and release-identity limitation

This review was requested for Build 115. The working tree identifies itself as **2.1.116**, and `built_build116.md` states that Build 116 supersedes Build 115 after four field defects were found against a real 1,115-file project. The repository has no Build 115 tag or commit, most Build 103–116 material is untracked, and no Build 115 source kit is present. An exact checkout of the released Build 115 therefore cannot be reconstructed from Git.

The assessment uses:

1. `built_build115.md` and `team_build115.md` for Build 115 claims;
2. `built_build116.md` for the four confirmed Build 115 field defects and the stated Build 116 delta;
3. the current Build 116 source as the closest strict superset, with the documented Build 116 changes separated from residual findings;
4. `docs/BFT_SELECTION_WORKSPACE_DESIGN_SPEC.docx` as the primary v2.2 design authority;
5. the interim Revision 1.1 decisions in `docs/Paul_Team_Communication_BFT_v2_2_Selection_Workspace_2026-08-25.md` and John's response;
6. direct tests, source traces, and adversarial probes performed on the current workspace.

This is enough to assess product direction and expose surviving risks, but it is not enough to certify the exact Build 115 binary/source artifact.

## 2. Intended project alignment

The project is intended to move BFT from a file-discovery utility with multiple selection paths to a governed, explainable selection system. The core architectural commitments are:

- one immutable `SelectionPlan` used by the service, CLI, and Tk workspace;
- deterministic, layered decisions with a full reason chain;
- environment and generated-content detectors;
- explicit session, project, command-line, preset, detector, and default layers;
- hard safety that cannot be overridden;
- one seven-region selection workspace with tri-state selection, search, rules, review, and preview;
- metadata-only planning followed by explicit artifact creation;
- reports that reconcile with what is actually emitted;
- CLI/UI/service parity;
- governed configuration integrity and opt-in project policy;
- accessible keyboard operation and responsive large-tree handling;
- later cache and personal-preset persistence work packages.

Build 115 is best understood as a **WP1–WP4 implementation candidate**, not as completion of the full v2.2 program. Its own build record explicitly defers WP5 cache persistence and WP6 personal preset/group persistence.

## 3. Alignment matrix

| Area | Intended contract | Build 115/current evidence | Alignment |
|---|---|---|---|
| Canonical selection model | One immutable plan with visible state, winning layer/rule, chain, size, group, ambiguity, confirmation, and emission order | `src/core/selection.py` provides immutable decisions/plans and layered reason chains | **Strong** |
| Deterministic layers | Safety, session, project, CLI, personal, shipped/detectors, default | The ladder and first-winning-rule behavior are implemented and well unit-tested | **Strong**, with a project-vs-CLI wording ambiguity |
| Metadata-only planning | Plan without reading full content | `scan_metadata` and the selection service separate planning from content emission | **Strong** |
| Hard safety | Non-overridable path/output/nested-bundle protection at plan time | Nested bundle blocking exists, but outside-base paths can be planned as Included and fail only during creation; output/self-ingestion protection is not fully expressed as a plan-time safety decision | **Partial** |
| Environment detection | Exclude environments by evidence, not directory name alone | Detector support and reason codes exist; direct default `plan` correctly excluded a `.venv312` fixture | **Strong in service/plan path** |
| Selection groups | Deterministic ordered groups, no duplicate membership | Group structures and deterministic membership are present | **Substantial** |
| Tk selection workspace | Seven-region workflow, tri-state tree, search, summary, trace, rules, final review | The workspace exists and has actual Tk integration tests; Build 116 fixed missing scrollbars, tree shape, and blocked filtering | **Substantial but incomplete** |
| Rule editor | Ordered rules, enabled state, action, label, typed matcher, group, preview, reorder, and save destinations | Current editor lists effective rules and adds/clears one glob session override; it cannot edit/reorder full rules, choose matcher type/group, or save personal presets | **Materially incomplete** |
| Rule-file contract | Formal schema, versioning, typed matchers, safe relative paths, unique IDs, unknown-field preservation | Loader uses numeric `version: 1`, flat `pattern`, and glob-only evaluation; it does not implement the interim `schema_version`/`match` contract, preserve unknown fields, enforce safe relative patterns, or reject duplicate IDs | **Not aligned with interim Revision 1.1 direction** |
| Final review | Reconciled counts, warnings, conflicts, blocked/unknown/stale/skipped/oversize, explicit artifact action | Review/report structures exist; `SKIPPED` and `STALE` states are defined but never produced, and creation can silently diverge from the plan | **Partial** |
| Report reconciliation | Text and JSON reports reconcile exactly with final manifest/skips | Deterministic reports exist, but plan decisions are not reconciled after deletion, oversize skipping, or read failure | **Not met end-to-end** |
| Service/CLI/Tk parity | Same ordered decisions for equal effective inputs; adapters do not reimplement selection | `plan` and selection-flagged `bundle` use the service, but default `bundle` deliberately stays on legacy `BundleCreator`; classic GUI also uses the legacy path | **Critical misalignment** |
| Performance | 4,000-path plan and usable Tk viewport within accepted budgets; virtualize large lists | Core planning is fast, but the Build 115 benchmark times the model rather than the Tk refresh. A local 4,000-file UI toggle took roughly 514–597 ms and rebuilt 4,041 decision-tree items | **Not demonstrated; current behavior misses the stated UI target** |
| Accessibility | Native semantics, full keyboard workflow, focus retention, non-color cues, assistive navigation | Text markers and keyboard bindings exist, but `[x]/[-]/[ ]` drawn in a `Treeview` are not native checkbox semantics; full refresh loses focus/selection; no live-summary announcement mechanism is evident | **Partial** |
| Cache equivalence | Cold and cache-assisted plans byte-identical | WP5 was explicitly deferred | **Not delivered in Build 115** |
| Personal persistence | Presets stored outside governed project root; corrupt files fail safely; group state persists | WP6 was explicitly deferred | **Not delivered in Build 115** |
| Governed configuration | No runtime writes; integrity and schema valid | Runtime write protection and digest checking exist, but the shipped configuration fails `ConfigManager.validate()` because `global_settings.ui_layout.buttons_position` is absent | **Integrity aligned; schema validity not aligned** |
| Packaging/distribution | Installable, runnable product with declared entry points | Source-copy installer is the practical deployment path. The declared wheel includes only `core*`, has no active scripts, omits UI/CLI/main/database, and references a missing README | **Not aligned as a Python distribution** |
| Reference personas | Executable enterprise and hobbyist fixtures before WP1/WP2 acceptance | No formal executable Revision 1.1 persona fixture suite was located | **Unclosed contract item** |

## 4. Architecture alignment

### 4.1 What is correctly shaped

The core design is recognizably the requested architecture. `SelectionService` composes detectors, rule sources, metadata, planning, reporting, and creation inputs rather than embedding selection logic inside the Tk widget. The immutable decision structures, fixed priority ladder, source digests, normalized paths, and explicit reason codes are appropriate foundations. The current test suite demonstrates that this foundation is not superficial: rule ordering, detector evidence, session overrides, project opt-in, progress/cancellation, stdout separation, multiple output formats, and real Tk construction are exercised.

This is important progress toward the project's explainability and governance goals.

### 4.2 Where adapters still define different products

The largest architectural exception is deliberate. `src/cli.py::_uses_selection_workspace()` sends `bundle` through `SelectionService` only when a selection-specific flag is present. A plain `bft bundle` uses `BundleCreator` directly. The code comment says wholesale migration is deferred to WP5.

A direct fixture showed the consequence:

- default `plan --list` selected only `app.py`;
- default `bundle` reported four files and included `.venv312/junk.py`, `.venv312/pyvenv.cfg`, and `.venv312/Scripts/python.exe`.

Thus, adding no flags changes the selection engine depending on the verb. The default product path can leak precisely the environment content that the new detector architecture is designed to exclude. The classic GUI remains available through governed `ui.bundle_mode=classic` and also uses direct `BundleCreator`, so it is another divergent adapter.

This conflicts with both SEL-X001 and SEL-X002 and should be treated as a release-blocking alignment defect, not an optional WP5 enhancement.

## 5. Product/work-package alignment

### WP1 — Selection core

Largely aligned. The model is deterministic, typed at the state/action/layer level, and testable. Remaining gaps are plan-time safety coverage, dormant stale/skipped states, and the absence of typed matchers promised by the interim schema direction.

### WP2 — Detectors and service

Largely aligned inside the new service path. Environment, generated/minified/binary, nested-bundle, and rule-source behavior have meaningful coverage. The alignment breaks when the default bundle or classic GUI bypasses the service.

### WP3 — CLI parity and review

Partially aligned. `plan` and selection-enabled `bundle` share the service, and JSON/text/list output behavior is well tested. Default `bundle` parity is not tested and does not hold. Creation does not feed actual skipped/missing outcomes back into a final plan/review artifact.

### WP4 — Tk workspace

Substantially delivered as an integration candidate. Build 116 confirms that Build 115 still had four user-visible defects: stale extracted bundle headers blocked ordinary projects, all three workspace panes lacked scrollbars, the decision view was an unstructured 1,100-row list, and blocked content could not be hidden. Build 116 fixes those four items, but rule editing, accessibility semantics, focus retention, preview-output limits, and large-tree rendering remain below the full contract.

### WP5 and WP6

Not delivered by design. That is acceptable only if Build 115 is labeled as an interim WP1–WP4 candidate. It is not acceptable if represented as full v2.2 acceptance.

## 6. Governance and repository alignment

The repository itself is not a reliable release ledger:

- HEAD is a generic commit on `master`, with no Build 115 tag;
- the working tree contains extensive modified/deleted/untracked material;
- Build 115 cannot be reproduced from the commit graph;
- `.pyprojectmgr/project_manifest.json` says 2.1.116 but has no entry points and uses an infrastructure map that differs from `.pyprojectmgr/project_spec.json`;
- the latest stored QC report is marked failed with 135 reported issues, although several error findings appear to be analyzer false positives;
- WP0 records describe canonical QC as tool-blocked/conditional rather than conclusively closed.

The code may be functionally useful, but release governance is not aligned with the project's stated repeatability and auditability goals.

## 7. Alignment conclusion

Build 115 moved the project materially in the correct direction and established a credible selection core, service, reporting model, and Tk workspace. It should receive credit as a strong implementation increment.

It should **not** be approved as the fully aligned BFT v2.2 Selection Workspace. The default artifact path still bypasses the canonical planner; the plan is not an authoritative snapshot of the artifact; the rule schema/editor and accessibility contract are incomplete; WP5/WP6 are deferred; and the exact Build 115 release is not reproducible. Build 116 corrects four important Build 115 field defects but does not, by itself, close these broader alignment findings.

## 8. Related deliverables

- [Accuracy analysis](BFT_BUILD115_ACCURACY_ANALYSIS.md)
- [Completeness analysis](BFT_BUILD115_COMPLETENESS_ANALYSIS.md)
- [Gaps and potential issues](BFT_BUILD115_GAPS_AND_POTENTIAL_ISSUES.md)
- [Conclusions](BFT_BUILD115_CONCLUSIONS.md)
- [Recommendations](BFT_BUILD115_RECOMMENDATIONS.md)
