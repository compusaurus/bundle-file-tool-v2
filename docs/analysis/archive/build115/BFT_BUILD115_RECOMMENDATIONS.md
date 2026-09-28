# BFT Build 115 — Recommendations

**Analyst:** Paul (lead analyst pseudonym)  
**For:** Ringo, George (Lead Architect), and John (Lead Developer)  
**Review date:** 2026-08-26  
**Recommended decision:** **Retire Build 115, contain current deployment risk, and release a clean successor through explicit P0/P1 gates**

## 1. Immediate product decision

1. Mark Build 115 **superseded/no-install** everywhere users can obtain it.
2. Keep Build 116 as the minimum field baseline because it fixes the four confirmed Build 115 defects.
3. Do not declare Build 116 complete v2.2 acceptance while the two open P0 findings remain.
4. If internal use must continue, require selection-aware bundle invocation and independent final-manifest review; disable or clearly warn on classic/legacy creation paths.

## 2. Recommended remediation order

The sequence below is intentionally dependency-aware. The first objective is one selection truth; the second is artifact truth; only then should the team optimize and persist it.

### Phase 0 — Establish a reproducible candidate

**Suggested accountable roles:** George for architecture/release shape, John for implementation baseline, Paul for acceptance evidence, Ringo for release disposition.

Actions:

1. Preserve the current working tree without overwriting user changes.
2. Reconcile intended source files and remove only generated diagnostics/build output from the candidate.
3. Commit the exact candidate on a `codex/`-prefixed or team-approved release branch.
4. Create an annotated build tag and export a source archive plus installer artifact.
5. Record SHA-256 hashes for source archive, installer, governed config, rules schema, and release documents.
6. Capture Python, Tk, pytest, OS, and optional-dependency versions used for verification.
7. Make `.pyprojectmgr/project_spec.json` and `project_manifest.json` agree about version, entry points, and infrastructure.

Exit gate:

- a clean checkout can reproduce the version, test result, installer, and artifact hashes without relying on untracked files;
- the exact candidate under test is the candidate delivered.

### Phase 1 — Close critical selection and artifact truth gaps

#### 1A. Make `SelectionService` the only bundle-selection authority

**Suggested owner:** John; architecture sign-off by George.

- Remove the implicit legacy branch in `src/cli.py::_uses_selection_workspace()`.
- Route every `bundle`, `plan`, workspace create, classic create, preview, and report operation through one service request/plan contract.
- If backward compatibility is required, define an explicit `--selection-profile legacy` or a named governed profile that is itself implemented as rules in the canonical engine.
- Deprecate direct file discovery inside UI/CLI adapters.

Required acceptance tests:

```text
test_default_bundle_manifest_equals_default_plan_emission
test_default_bundle_excludes_detected_environment
test_classic_and_workspace_modes_use_same_ordered_decisions
test_no_adapter_invokes_legacy_discovery_directly
```

Exit gate:

- the same effective inputs produce byte-identical ordered decision records and manifest paths from service, CLI plan, CLI bundle, workspace, and supported classic mode.

#### 1B. Define and enforce plan-to-artifact snapshot semantics

**Suggested owners:** George for contract, John for implementation, Paul for acceptance fixtures.

Recommended contract:

- planning records normalized path, size, modification time, and optionally a cheap/strong content fingerprint according to risk;
- creation verifies the snapshot before opening each selected file;
- any missing, changed, unreadable, outside-root, active-output, oversize, or path-collision condition aborts before publication and produces a serializable reason;
- the UI offers **Re-plan** rather than silently continuing;
- publication is transactional: write to a temporary artifact, validate/reconcile, then atomically replace the destination;
- final manifest embeds the plan digest and source/rule digests.

If the team chooses reconciliation instead of strict abort, every changed outcome must produce a final `STALE`, `SKIPPED`, `UNKNOWN`, or `BLOCKED` decision and require renewed confirmation before publication.

Required acceptance tests:

```text
test_deleted_selected_file_aborts_without_publishing
test_changed_selected_file_requires_replan
test_oversize_selected_file_is_visible_before_or_reconciled_after_creation
test_read_error_is_a_serializable_decision
test_final_manifest_paths_equal_final_plan_emission_exactly
test_plan_digest_is_embedded_and_verifiable
```

Exit gate:

- no successful artifact can differ from its approved final plan;
- SEL-F006 is demonstrated by comparing actual parsed artifact entries, final manifest, skips, and text/JSON reports.

#### 1C. Move all writer invariants into plan-time safety

**Suggested owners:** George and John.

Create explicit P0 reason codes for at least:

- outside declared source root;
- unsafe `..` or absolute normalized path;
- active output path/self-ingestion;
- destination collision after case and separator normalization;
- unsupported/unreadable entry;
- genuine nested bundle;
- source/output alias through symlink or junction where supported.

Keep defensive writer checks, but treat a writer-only rejection as an internal contract failure and block publication.

Exit gate:

- every deterministic writer rejection has a plan-time fixture and visible reason chain;
- outside-base direct probe returns Blocked, not Included-then-exception.

### Phase 2 — Repair release-validity and integration blockers

#### 2A. Make governed configuration both intact and valid

**Suggested owner:** John; acceptance by Paul.

- Add or correctly migrate `global_settings.ui_layout.buttons_position`, or revise the schema if it is no longer part of the contract.
- Run `ConfigManager.validate()` during installer Gate E and startup, in addition to digest verification.
- Derive profile format validation from the runtime formatter registry.
- Add a release test that loads, validates, and exercises every shipped profile.

Exit gate:

- the shipped config passes both digest and schema validation;
- no validator option lacks a runtime implementation.

#### 2B. Close main-window/mode seams

**Suggested owner:** John.

- Define a small common interface for workspace/classic frames (`create`, `copy`, `validate`, selection/report capabilities).
- Disable menu items based on explicit capabilities rather than assumptions.
- Implement or remove the Validate Bundle placeholder.
- Scope/unbind global Ctrl-Z/Ctrl-Y bindings with frame lifecycle.

Required acceptance test:

- instantiate the main window in each governed mode and invoke every enabled menu/toolbar command without `AttributeError` or placeholder behavior.

#### 2C. Harden nested-bundle detection

**Suggested owner:** John; policy sign-off by George.

- Replace basename-only stale-header classification with normalized full-path and structural bundle evidence.
- Add cases for a single-entry real bundle, identical basename/different directories, copied header, truncated bundle, multiple blocks, and malformed delimiters.
- Preserve Build 116's false-positive fix while closing the false-negative edge.

## 3. Complete the rule contract before expanding persistence

**Suggested owners:** Paul for contract publication, George for model review, John for implementation.

1. Publish the promised integrated Specification Revision 1.1.
2. Publish a formal JSON Schema and schema versioning/migration policy.
3. Choose one canonical shape. The recommended direction is the previously agreed:

```json
{
  "schema_version": "1.0",
  "name": "project rules",
  "base_action": "include",
  "rules": [
    {
      "id": "exclude-build",
      "enabled": true,
      "order": 10,
      "action": "exclude",
      "match": {"type": "glob", "pattern": "build/**"},
      "group": "generated"
    }
  ],
  "groups": []
}
```

4. Validate unique IDs, safe relative POSIX patterns, supported matcher types, types/ranges, and schema version.
5. Preserve unknown fields losslessly while ignoring them during v1 evaluation.
6. Decide whether project files may request presets. Either resolve and digest them canonically or reject the field; notices without effect are not acceptable.
7. Implement one typed matcher evaluator shared by file load, UI preview, CLI, and service.
8. Upgrade the editor to manage ordered enabled rules, action, label, typed match, group, live changed-count preview, reorder, and explicit save destinations.
9. Only after this contract is stable, implement WP6 personal preset persistence outside the governed root with corruption quarantine/recovery.

Exit gate:

- schema examples round-trip without data loss;
- CLI/UI/service evaluate the same loaded rules;
- both promised persona fixtures execute and produce checked-in golden plans;
- incompatible future versions fail loudly and safely.

## 4. Make the workspace scalable and accessible

### 4.1 Incremental rendering and virtualization

**Suggested owner:** John; acceptance thresholds ratified by Ringo/Paul.

- Stop calling whole-workspace `refresh_all()` for a single toggle.
- Give folder and decision nodes stable IDs.
- Update only affected descendants/ancestors, counts, and detail rows.
- Populate collapsed children lazily or use a windowed/virtual view.
- perform expensive filtering/replanning off the Tk event loop, with cancellation and generation IDs to discard stale results;
- keep the complete immutable plan in the model so virtualization never reduces programmatic accessibility.

Performance gate:

- measure event-to-idle-render with real Tk on a declared reference environment;
- enforce median and p95 for initial usable viewport, single-file toggle, folder toggle, search, and clear-search at 4,000, 10,000, and a chosen stress size;
- report widget item count and memory as well as time;
- do not substitute model timing for UI timing.

### 4.2 Accessibility completion

**Suggested owners:** John for widgets, Paul for acceptance script, Ringo for product sign-off.

- expose state as role/name/value or checked/mixed semantics through supported platform mechanisms;
- keep `[x]/[-]/[ ]` as redundant visual/text cues, not the only semantic channel;
- separate focus movement, expand/collapse, and selection toggle commands;
- preserve focus and selection by stable ID after recompute/filter;
- announce summary changes and validation errors through an accessible status mechanism;
- verify full keyboard operation, high contrast, Windows scaling, and conditional bulk confirmation;
- document manual screen-reader passes (for example Narrator and NVDA on Windows) until reliable automation is available.

Exit gate:

- the complete acceptance workflow can be executed without a mouse;
- focus never jumps to the top after a local change;
- mixed/blocked/unknown state and reason are announced without relying on color or punctuation alone.

### 4.3 Complete review and bounded preview

- Add the agreed on-demand **Preview Output** surface limited to 10 files or 50 KB, with explicit truncation text and deterministic ordering.
- Extend final review with grouped totals by rule, group, file family, and outcome.
- Ensure review displays final oversize/missing/read-error status from the same record used to publish.

## 5. Finish WP5 and WP6 only behind equivalence gates

### WP5 cache

- Cache metadata/detector results by stable keys and rule/source digests.
- Never cache final decisions independently of all effective inputs.
- Corrupt or incompatible caches must be discarded safely.
- Run cold and cache-assisted planning on every reference fixture and compare canonical JSON byte for byte.
- Keep cache optional; disabling it must change performance only, never decisions.

### WP6 personal persistence

- Store personal presets outside the governed project tree using an OS-appropriate user-data directory.
- Use atomic write/rename, backups, schema validation, and corruption quarantine.
- Keep project rules opt-in and never mutate them merely by opening a project.
- Persist UI/group preferences separately from selection policy unless the product explicitly promotes them.

## 6. Decide and correct the packaging model

**Suggested decision owner:** George; implementation by John.

Choose one of two honest models:

1. **Installable BFT package:** include `core`, `ui`, database, top-level modules, package data, and working `bft`/GUI entry points; add the missing README; test an install into an empty virtual environment and run smoke/round-trip tests from outside the source tree.
2. **Source-copy application with internal core wheel:** rename/describe the wheel accordingly, prevent users from treating it as the product, and make the batch installer the sole documented distribution with equivalent reproducibility gates.

Do not leave a wheel named as the application that installs only its core library.

## 7. Strengthen verification where current evidence is weak

Recommended new release-test groups:

| Test group | Purpose |
|---|---|
| Default cross-surface matrix | Same fixture and no flags across service, plan, bundle, workspace, and supported classic mode |
| Artifact mutation matrix | Delete, edit, chmod/deny, rename, oversize, output collision, and time-of-check/time-of-use changes |
| Main-window capability matrix | Invoke every enabled command in every UI mode |
| Real Tk latency harness | Measure keypress/search/create-review to idle render, not model-only work |
| Accessibility acceptance | Stable focus, keyboard path, state semantics, scaling/high contrast, manual screen reader evidence |
| Rule-schema conformance | Golden valid/invalid files, unknown-field round trip, migration, unique IDs, safe paths |
| Permission/error matrix | Unreadable files/directories, serializable warnings, cancellation at each stage |
| Installed-artifact smoke | Clean virtual environment or clean installer destination, invoked outside repo |
| Release reproducibility | Clean checkout/archive yields identical version, tests, config digest, and artifact hashes |

Coverage recommendations:

- include `main_window`, selection/classic mode integration, and startup in the release coverage target;
- use branch coverage for rule/source/error logic;
- retain statement coverage but stop treating the aggregate percentage as sufficient evidence;
- require zero unexplained skips and publish the skip list even when zero.

## 8. Release gates for the next candidate

The next candidate should not ship until all of the following are true:

- [ ] Exact source and installer are immutable, tagged, and hashed.
- [ ] Default `bundle`, `plan`, service, and every supported GUI mode produce identical ordered decisions.
- [ ] Final artifact, manifest, text report, JSON report, and skips reconcile exactly.
- [ ] Filesystem mutation cannot silently change a successful artifact.
- [ ] All writer invariants appear as plan-time decisions.
- [ ] Shipped configuration passes integrity and full schema validation.
- [ ] All enabled menu actions work in all supported modes.
- [ ] The formal rule schema and persona fixtures are published and executable.
- [ ] Actual Tk performance meets ratified median/p95 gates.
- [ ] Keyboard/focus/assistive acceptance is documented and passed.
- [ ] No P0 or P1 issue in the gap register remains open without an explicit, owner-approved release waiver.
- [ ] Canonical QC is passing or each tool false positive has a versioned waiver and clean superseding report.

## 9. Suggested delivery sequence

To keep scope controlled, use three clearly named milestones:

1. **Containment successor:** one service path, strict plan/artifact reconciliation, plan-time safety, valid config, fixed menu integration, reproducible release.
2. **Contract/UI successor:** formal rule schema/editor, accessibility/focus, virtualized/incremental workspace, bounded preview, full report aggregates.
3. **Persistence/distribution successor:** WP5 cache, WP6 personal persistence, and the chosen complete packaging model.

Each milestone should have its own immutable acceptance bundle and should not inherit a green status solely from the prior milestone's aggregate suite.

## 10. Related deliverables

- [Project alignment analysis](BFT_BUILD115_PROJECT_ALIGNMENT_ANALYSIS.md)
- [Accuracy analysis](BFT_BUILD115_ACCURACY_ANALYSIS.md)
- [Completeness analysis](BFT_BUILD115_COMPLETENESS_ANALYSIS.md)
- [Gaps and potential issues](BFT_BUILD115_GAPS_AND_POTENTIAL_ISSUES.md)
- [Conclusions](BFT_BUILD115_CONCLUSIONS.md)
