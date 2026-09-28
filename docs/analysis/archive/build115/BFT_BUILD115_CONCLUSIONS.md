# BFT Build 115 — Conclusions

**Analyst:** Paul (lead analyst pseudonym)  
**For:** Ringo, George (Lead Architect), and John (Lead Developer)  
**Review date:** 2026-08-26  
**Release conclusion:** **Do not approve or reinstall Build 115; treat Build 116 only as a better interim candidate, not yet full v2.2 acceptance**

## 1. Executive conclusion

Build 115 is a substantial and technically credible development milestone. It establishes most of the intended selection core, detector/service architecture, explainable plans, CLI planning, reports, and a real Tk Selection Workspace. The current Build 116 superset passes all 1,402 tests with 91.21% statement coverage and no skipped Tk tests in the verified repository environment.

Those strengths do not support release approval for Build 115.

Build 116's own record confirms four Build 115 field defects: ordinary projects could be blocked by stale extracted bundle headers, the workspace's three main panes lacked scrollbars, large decision sets were presented as one flat list, and blocked content could not be hidden. Build 116 should therefore always be preferred over 115.

More importantly, direct review found two critical end-to-end issues that survive in the current superset:

1. default `bundle` bypasses the canonical selection service and can emit files that default `plan` excludes;
2. an approved plan is not reconciled with the artifact when a selected file is deleted, unreadable, oversize, or otherwise rejected during creation.

Until those are fixed, the product cannot truthfully promise that “what I reviewed is what BFT bundled.” That promise is the center of the v2.2 design.

## 2. Conclusions by requested dimension

### Project alignment

**Conclusion: partially aligned.**

The internal architecture is moving toward the intended single-service, reasoned-decision design. The immutable models, layer ladder, detectors, service facade, and workspace are sound choices. Alignment breaks at active legacy adapters, plan-time safety/reconciliation, the incomplete rule contract/editor, accessibility, and deferred WP5/WP6 work.

Build 115 is appropriately described as a **WP1–WP4 implementation candidate**. It is not appropriately described as complete v2.2 conformance.

### Accuracy

**Conclusion: strong core accuracy, insufficient artifact and release accuracy.**

For stable metadata and callers that use the service, decisions are deterministic and well tested. Across the whole product, default commands can select different files, and the final artifact can differ from the approved plan without a final decision update. The Build 115 source itself is not recoverable as an immutable Git or archive baseline, so historical claims cannot be independently reproduced.

### Completeness

**Conclusion: substantial but incomplete.**

WP1 and WP2 are mostly present, WP3 and WP4 are partial, and WP5/WP6 are explicitly deferred. Several promised WP1–WP4 acceptance items also remain incomplete: full CLI/Tk/service parity, final report reconciliation, formal rule schema, complete rule editor, bounded output preview, accessible native semantics/focus retention, and actual UI performance at the stated target.

### GAPs and foreseeable issues

**Conclusion: high residual risk.**

The principal risks are not obscure code-style concerns. They affect selection truth, sensitive-content exclusion, artifact auditability, large-project usability, accessibility, packaging, and release reproducibility. The detailed register identifies two P0 open findings, multiple P1 findings, and four Build 115 field defects, one of which was itself P0 in the Build 115 context.

## 3. What the team got right

The review should not obscure the quality of several decisions:

- the domain model is separated from Tk and CLI presentation;
- decisions carry useful explanatory evidence rather than booleans alone;
- detector conjunction and layer order have explicit regression tests;
- hard blocks are protected from ordinary user override;
- JSON stdout, progress, and cancellation behavior show good automation discipline;
- the test suite is broad and larger than the source by physical line count;
- actual Tk tests run instead of being skipped;
- Build 116 responded directly to real-user evidence rather than defending Build 115 behavior.

These foundations make remediation practical. The recommendation is not to replace the architecture; it is to complete it and remove remaining alternate truths.

## 4. Why the green suite is not a release verdict

The verified 1,402 green tests are valuable but do not cover several decisive seams:

- default `bundle` parity tests switch onto the new engine by supplying selection flags;
- plan-to-artifact tests do not mutate or oversize planned inputs and demand reconciliation;
- the UI performance test stops at the model and does not measure Tk redraw;
- accessibility assertions verify descriptive strings, not platform semantics or focus behavior;
- main-window/classic-workspace integration is outside the measured coverage set;
- `src/main.py` has 0% measured coverage.

This explains how a menu action can call a missing workspace method and how the default bundle can diverge while the suite remains green. The solution is targeted acceptance coverage, not simply more tests of already-covered functions.

## 5. Release disposition

| Candidate | Disposition | Rationale |
|---|---|---|
| Build 115 | **No-go / superseded** | Four confirmed field defects; exact artifact not reproducible; Build 116 explicitly replaces it |
| Current Build 116 as a Build 115 replacement | **Prefer over 115, with restrictions** | Fixes all four documented field defects and passes 1,402 tests |
| Current Build 116 as full v2.2 general release | **Hold** | Critical default parity and plan/artifact reconciliation remain open; rule/accessibility/performance/config gates incomplete |
| A clean successor after P0/P1 closure | **Re-evaluate** | Must be immutable, fully validated, and verified against end-to-end acceptance gates |

If the current build must be used internally before a successor is ready, the safest temporary operating posture is:

- do not use Build 115;
- avoid classic GUI mode;
- do not use a flagless `bundle` invocation;
- generate and review a plan, then run selection-aware bundle creation on an unchanged source tree;
- verify the final manifest independently before distributing the artifact;
- do not treat the current review report as proof of final artifact equality.

These are operational mitigations, not substitutes for repair.

## 6. Final conclusion

The BFT team has built the correct **center** of the new product but has not yet made it the only product path. Build 115 should remain superseded. Build 116 is demonstrably better, yet acceptance should wait until every adapter uses the canonical service and the final artifact is cryptographically or structurally reconciled with the approved plan.

Once those two P0 issues, the configuration failure, the Build 115 provenance problem, and the main P1 UI/rule/accessibility items are closed under a clean release baseline, the existing core and test foundation should support a credible v2.2 release.

## 7. Related deliverables

- [Project alignment analysis](BFT_BUILD115_PROJECT_ALIGNMENT_ANALYSIS.md)
- [Accuracy analysis](BFT_BUILD115_ACCURACY_ANALYSIS.md)
- [Completeness analysis](BFT_BUILD115_COMPLETENESS_ANALYSIS.md)
- [Gaps and potential issues](BFT_BUILD115_GAPS_AND_POTENTIAL_ISSUES.md)
- [Recommendations](BFT_BUILD115_RECOMMENDATIONS.md)
