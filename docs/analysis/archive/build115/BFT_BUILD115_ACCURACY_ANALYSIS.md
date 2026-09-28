# BFT Build 115 — Accuracy Analysis

**Analyst:** Paul (lead analyst pseudonym)  
**For:** Ringo, George (Lead Architect), and John (Lead Developer)  
**Review date:** 2026-08-26  
**Assessment:** **Core decision logic is generally accurate; release-level claims and artifact accuracy are not yet reliable**

## 1. Meaning of accuracy in this review

Accuracy is evaluated at five levels:

1. **release accuracy** — whether the reviewed files are provably the Build 115 release;
2. **decision accuracy** — whether equal inputs produce the intended selection and reason chain;
3. **artifact accuracy** — whether the created bundle exactly represents the approved plan;
4. **reporting accuracy** — whether counts, warnings, and reports describe the artifact that was actually written;
5. **verification accuracy** — whether tests and performance evidence measure the behavior claimed.

## 2. Verification performed

### 2.1 Current-suite baseline

Using the repository's own virtual environment, the complete current test suite produced:

```text
1402 passed in 84.08s
TOTAL: 4690 statements, 352 missed, 91.21% coverage
```

There were no skipped tests. A complete bytecode compilation pass also succeeded.

This independently confirms the current Build 116 record's 1,402-pass/91.21% claim. It does **not** independently reproduce Build 115's stated 1,378-pass/91.29% result, because the exact Build 115 tree is unavailable.

An initial run under a mixed Anaconda/project environment produced four progress-subprocess failures because those subprocesses could not import an optional dependency. Re-running with the repository's own virtual environment eliminated all four. Those failures were environmental, not counted as product defects.

### 2.2 Source-to-runtime probes

Focused probes were used where the formal suite did not exercise an important boundary:

- default `plan` versus default `bundle` on a project containing an environment-like directory;
- plan creation followed by file deletion;
- plan creation followed by an oversize limit;
- a source outside the selected base directory;
- actual Tk refresh cost for a 4,000-file workspace;
- governed configuration integrity versus schema validation;
- wheel contents from the declared `pyproject.toml` package configuration.

These probes revealed material discrepancies described below.

## 3. Accuracy strengths

### 3.1 Deterministic decision engine

The selection engine's basic behavior is accurate and well-factored:

- paths are normalized to forward-slash relative form;
- a fixed layer ladder controls evaluation order;
- decisions retain a winning entry and a full reason chain;
- hard blocks cannot be moved by ordinary include/exclude overrides;
- group membership and emission order are deterministic;
- source digests make effective rule inputs inspectable;
- detector evidence produces explicit rule codes and details.

The associated tests cover core matching, layer priority, environment detection, nested bundle handling, ambiguity, groups, and override behavior. `src/core/service.py` has particularly strong statement coverage (98% in the current suite), while `src/ui/workspace_model.py` reaches 95%.

### 3.2 Output-channel discipline

The current CLI has good separation between machine-readable stdout and human progress/status output. Tests cover JSON purity, progress rendering, cancellation, and no-progress modes. That supports scripting accuracy and reduces the risk of corrupted JSON pipelines.

### 3.3 Actual Tk execution

The suite includes real Tk construction and interaction tests with no skips in the verified environment. This is better evidence than mock-only GUI coverage and confirms that the major workspace widgets can be created and exercised.

### 3.4 Build 116's documented fixes are credible

The current source and tests support the four deltas stated in `built_build116.md`: stale extracted headers are treated differently from genuine nested bundles, workspace panes have scrollbars, the decisions pane has a folder hierarchy, and blocked items can be hidden. These fixes substantiate the conclusion that the corresponding behaviors in Build 115 were defects.

## 4. Accuracy failures and limitations

### 4.1 The reviewed tree is not provably Build 115

The current `VERSION` is 2.1.116. There is no Build 115 tag, commit, source archive, or retained installer kit that maps the build record to an immutable tree. Git status contains extensive changes and untracked files. Consequently:

- individual code observations are observations of the current Build 116 superset unless explicitly documented as a Build 115 condition;
- the Build 115 test count is a historical claim, not a result reproduced by this review;
- no cryptographic comparison can prove which files shipped in Build 115.

This is an accuracy problem in release provenance even if the source itself behaves correctly.

### 4.2 Default `plan` and default `bundle` disagree

The most significant runtime accuracy defect is caused by `src/cli.py::_uses_selection_workspace()`. `plan` always uses the selection service. `bundle` uses it only when at least one selection flag is supplied; otherwise it invokes legacy `BundleCreator` directly.

Observed fixture:

```text
Project files:
  app.py
  .venv312/pyvenv.cfg
  .venv312/Scripts/python.exe
  .venv312/junk.py

Default plan --list:
  app.py

Default bundle:
  Found 4 files
  emitted app.py and all three .venv312 files
```

Both commands were given the same base path and no selection overrides. The results should be identical under SEL-X001. Instead, the default bundle is inaccurate relative to the product's canonical plan and can include detected environment contents.

The current parity tests do not catch this because CLI-to-service comparisons exercise `plan`, and plan-to-bundle tests add at least one selection flag, which switches `bundle` onto the new service.

### 4.3 The approved plan is not the final artifact truth

`BundleCreator.create_manifest()` can skip or reject files after planning:

- deleted/missing files are silently continued over;
- read/stat errors are continued over;
- files above the maximum size are omitted and recorded as skipped;
- a selected path outside the base is rejected later by `relative_to()`;
- active output-path and post-plan filesystem changes are not fully reconciled into final selection decisions.

Observed results:

| Probe | Plan | Artifact result | Accuracy consequence |
|---|---|---|---|
| Delete selected file after planning | `planned.txt` Included | Success with zero files; no updated decision | Approved plan overstates artifact |
| Apply oversize threshold after planning | `planned.txt` Included | Zero files plus a manifest skip | Plan/report decision remains Included |
| Source lies outside base | `../source/planned.txt` Included | Creation raises `ValueError` | Plan approves something artifact logic forbids |

`State.SKIPPED` and `State.STALE` exist in the model but are not produced by the implementation. The names suggest an intended reconciliation mechanism that is currently dormant.

This violates the practical meaning of an immutable approved plan: either creation must strictly fail if the snapshot changes, or it must emit a reconciled final plan/manifest that makes every change visible.

### 4.4 Reports are accurate about the plan, not necessarily the artifact

The text and JSON report serializers are deterministic for a given `SelectionPlan`. However, the report is generated before the content loop's final skip/error outcomes. Therefore deterministic serialization is not the same as end-to-end truth.

The reports also lack some specified summaries, including meaningful aggregation by rule, group, and file family and a complete post-creation account of missing/oversize/read-error cases. Acceptance item SEL-F006 requires the report to reconcile exactly with the manifest and skips; current behavior cannot guarantee that.

### 4.5 Configuration integrity and configuration validity give conflicting answers

On the shipped current configuration:

- `ConfigManager().check_config_integrity()` succeeds;
- `ConfigManager().validate()` raises `ConfigValidationError` because `global_settings.ui_layout.buttons_position` is missing.

This means the digest accurately says “this file has not been modified,” while the schema validator accurately says “this governed file is invalid.” The installer gate described in the build records checks integrity, not full schema validation, so an invalid but untampered configuration can pass release installation checks.

There is also a profile-validation mismatch: `_validate_profile` accepts `jsonl`, while the formatter registry exposes only the supported registered formats. Validation and runtime capability should use the same authoritative registry.

### 4.6 Unreadable-directory warnings may break JSON reporting

The metadata scanner passes `result.warnings.append` directly as `os.walk(onerror=...)`. `os.walk` supplies an `OSError`, but plan warnings are treated as strings. If such a warning reaches `json.dumps`, it is not JSON-serializable. The scanner also does not create the specified Unknown/Blocked directory decision for an unreadable root. This edge case is source-confirmed but was not forced in the Windows test environment.

### 4.7 Nested-header fix may have a remaining false-negative edge

Build 116's stale-header heuristic compares the declared source basename with the stored block basename. That solves the Build 115 false positive for common extracted bundles. A residual edge remains: a genuine single-entry nested bundle that stores `backup/app.py` while declaring `src/app.py` has matching basenames and can be classified as stale rather than nested. This is a **post-Build-115 residual risk**, not one of the four confirmed Build 115 defects.

## 5. Accuracy of performance claims

Build 115 reports a 4,000-file toggle result of about 128 ms against a 150 ms target. The test behind that number (`tests/integration/test_selection_performance.py`) times `WorkspaceModel.set_folder()`, not the Tk event handler and redraw.

The actual space-key path calls `refresh_all()`, which deletes and rebuilds the summary, folder tree, rules list, and complete decision tree. On the review machine, a 4,000-file local probe measured five toggles at approximately:

```text
514.4 ms, 596.9 ms, 520.9 ms, 571.3 ms, 526.2 ms
```

The decision tree contained 4,041 widget items. This is a local diagnostic rather than a controlled cross-machine p95 benchmark, but it proves that the reported 128 ms does not measure the user-visible operation described by the acceptance target. The current view uses hierarchy/collapse, yet still inserts all rows and is not virtualized.

## 6. Test evidence calibration

The 1,402-test result is strong evidence of regression discipline, but coverage is uneven at product boundaries:

- `src/main.py` is measured at 0%;
- classic `main_window`, `bundle_frame`, `unbundle_frame`, and mode integration are omitted from the coverage target;
- the main-window menu integration is not tested;
- default `bundle` parity is not tested;
- plan-to-artifact mutation/reconciliation is not tested;
- the UI performance test does not time the UI;
- accessibility tests assert descriptive text rather than assistive-technology semantics.

One concrete symptom is the enabled main-window **Copy Bundle to Clipboard** menu. It calls `bundle_frame.copy_to_clipboard()`, but `SelectionWorkspaceFrame` has no such method. In default workspace mode, that action raises `AttributeError`; the full suite remains green because the integration seam is outside the tested surface.

## 7. Accuracy conclusion

The current selection core is deterministic and generally trustworthy for a stable metadata snapshot when every caller actually uses it. The product as a whole is not yet accurate enough for Build 115 acceptance because:

- the release tree cannot be proven;
- default artifact creation bypasses the canonical planner;
- post-plan filesystem and size outcomes are not reconciled;
- reports describe the intended plan more reliably than the final artifact;
- the UI performance evidence measures the model rather than the UI;
- configuration integrity can pass while configuration validation fails.

The correct conclusion is therefore **strong core accuracy with unresolved release- and artifact-level accuracy defects**.

## 8. Related deliverables

- [Project alignment analysis](BFT_BUILD115_PROJECT_ALIGNMENT_ANALYSIS.md)
- [Completeness analysis](BFT_BUILD115_COMPLETENESS_ANALYSIS.md)
- [Gaps and potential issues](BFT_BUILD115_GAPS_AND_POTENTIAL_ISSUES.md)
- [Conclusions](BFT_BUILD115_CONCLUSIONS.md)
- [Recommendations](BFT_BUILD115_RECOMMENDATIONS.md)
