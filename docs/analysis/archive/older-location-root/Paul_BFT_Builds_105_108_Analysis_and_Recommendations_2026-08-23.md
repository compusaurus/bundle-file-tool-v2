# BFT v2.1 Builds 105-108 - Analysis, Conclusions, and Recommendations

**Document Ref:** BFT-ANALYSIS-2026-08-23-01  
**From:** Paul, Lead Analyst and Collaborative Developer  
**To:** Ringo, Product Owner; George, Lead Architect; John, Lead Developer  
**Date:** 2026-08-23  
**Subject:** Review of Builds 105-108, Build 108 ratification ruling, governing specifications, source/test evidence, and Build 109-111 sequencing

---

## 1. Executive disposition

I concur with George's ratification of Builds 105-108 **as governed development increments within their stated scopes**. The sequence is technically sound and materially advances BFT:

- Build 105 establishes the stabilized post-104 baseline: Markdown Fence registration, CLI stdout purity, governed-config diagnostics, and delivery-template recovery.
- Build 106 introduces the shared `BundleToolService` and BFT-owned `OperationProgress` event model.
- Build 107 adds the CLI PyThermX adapter, offline optional dependency packaging, stdout-safe rendering, and the `.whl` deny rule.
- Build 108 upgrades PyThermX to 0.3.1, adds the Tkinter progress adapter, moves long GUI work off the UI thread, corrects the CLI unbundle progress omission, and improves dependency-pin testing.

This ratification must not be read as a declaration that the Build 100 tri-UI program is complete or that Build 108 is ready for unrestricted production use. The Web UI is absent; CLI and Tkinter still orchestrate lower-level core classes directly; JSONL remains unresolved; and the default extraction policy corrupts structured text by injecting `#` headers. George correctly assigns that last defect to Build 109.

My review also found three additional issues that should be added to the governed roadmap:

1. The Build 108 GUI still constructs `ConfigManager("bundle_config.json")`. That explicit relative path bypasses Build 105's application-root anchoring and can create a new configuration in the process working directory.
2. The supplied `PREP_AND_STAGE_BFT.bat` increments the **outgoing** build number after installation. If Build 108 supersedes Build 105 or 106 as the delivery records permit, the script can overwrite `VERSION.txt` with 2.1.106 or 2.1.107 after installing 2.1.108.
3. Configuration validation still accepts `jsonl`, but `ProfileRegistry` registers only `plain_marker` and `md_fence`. A configuration can therefore validate and then fail at runtime.

Accordingly, my disposition is:

> **RATIFY the delivered Build 105-108 scope; HOLD any claim of Build 100 completion; and EXPAND Build 109/110 acceptance gates to close the configuration-path, delivery-version, JSONL, facade-migration, and progress-contract discrepancies documented below.**

If the live installation is still Build 105 or 106, I do **not** recommend staging Build 108 through the currently supplied PREP script until the version-ownership issue is ruled on or corrected. If the live tree is Build 107, the current `+1` happens to produce 108, but that does not cure the defective supersession contract.

---

## 2. Evidence reviewed

This review considered:

- John's team summaries and build records for Builds 105, 106, 107, and 108.
- George's `ARCH-RULING-2026-08-23-01` ratification and Build 109-111 roadmap.
- The v2.1 master specification, team directives, technical specification, alternatives analysis, Build 100 Tri-UI Feature and System Specification, and `PREP_AND_STAGE_BFT.bat`.
- Build 102 tests; Build 103 full/source/delivery records; Build 104 source/tests; and Build 108 source, tests, and scripts bundles.

The Build 108 bundles yielded 31 source files, 48 test files, and 2 scripts. All extracted Python source and test files byte-compiled cleanly in the review environment. The reported `702 passed` and 90.29% coverage remain credible documentary evidence, but were not independently reproduced because the supplied review set did not contain the complete Build 108 installation kit, governed `bundle_config.json`, project manifest, vendored PyThermX wheel, or a pytest/PyThermX test environment.

---

## 3. Build-by-build conclusions

| Build | Conclusion | Disposition |
|---|---|---|
| **105** | Correctly refused an in-place Build 104 patch and restored artifact identity. The Markdown Fence registration and stdout-purity fixes are well targeted. Config anchoring is correct for default `ConfigManager()` callers, but the GUI still bypasses it with an explicit relative path. | **Accepted as the stabilized baseline, with the GUI anchoring closure carried into Build 109.** |
| **106** | Establishes a useful, renderer-neutral service and progress seam. Safety gates inside the facade are the correct architectural direction. The facade is not yet the complete Build 100 application contract and no production UI is migrated to it. | **Accepted as facade foundation, not completion of WP2/tri-UI isolation.** |
| **107** | CLI progress is properly isolated in an adapter and rendered on stderr. Optional/offline PyThermX packaging and the `.whl` deny addition are sound. Build 108 correctly repairs the missed CLI unbundle sink. | **Accepted as an intermediate milestone superseded operationally by Build 108.** |
| **108** | The worker-thread/Tk channel design addresses the real freeze mechanism, not merely the visual symptom. The pin test now evaluates the full specifier. The GUI progress adapter is substantively tested. | **Ratified for its declared scope, subject to Build 109 defect/governance gates and later facade migration.** |

The progression from 592 to 622 to 661 to 702 reported passing tests is meaningful, especially because the later builds add boundary and subprocess tests rather than merely increasing low-value unit coverage. Build 108's test for the actual `unbundle --progress bar` command is exactly the kind of end-to-end assertion that Build 107 lacked.

---

## 4. Findings requiring action

### F-01 - Default header injection corrupts structured text

**Severity:** Critical  
**Status:** Confirmed; George has ruled Option B+ for Build 109.

`BundleWriter.write_entry()` prepends a fixed `#` header to every non-binary entry when `add_headers=True`, regardless of file format. The ratified default is `True`. This makes JSON, XML, HTML, JavaScript, CSS, SQL, and other formats invalid or non-identical after extraction.

The historical round-trip suite masked this by repeatedly constructing `BundleWriter(..., add_headers=False)`. I independently exercised Build 108 with default headers against a valid JSON entry; the extracted file began with the repository header and `json.loads()` failed.

**Recommendation:** Implement George's Option B+ exactly as a governed allow-list/filename rule, but define the acceptance contract more precisely:

- Comment-compatible types may receive the canonical header.
- Every other text type must be extracted byte-pure.
- Binary types must remain byte-pure.
- The multi-format test must exercise the real default configuration and both service and UI/CLI paths once those adapters are migrated.
- Include exact-filename and case-normalization tests, plus extensionless files.

### F-02 - The current GUI bypasses governed-config anchoring

**Severity:** High  
**Status:** Newly confirmed.

Build 105 correctly added `ConfigManager.governed_config_path()` and made the no-argument constructor resolve from the installed application root. However, `BundleFileToolApp.__init__()` in Build 108 still calls:

```python
ConfigManager("bundle_config.json")
```

That is explicitly treated by `ConfigManager` as a developer/test path. It resolves against the current working directory and creates the file if absent. I verified that, from an unrelated temporary directory, the default constructor remained anchored while the GUI-style explicit constructor created `bundle_config.json` in that unrelated directory.

This means Build 105's configuration closure is incomplete on the primary GUI surface. It also weakens George's Layer C filesystem protection because the application may use a different, unprotected file.

**Recommendation for Build 109:** Change the GUI to `ConfigManager()` and add a real GUI/application construction test from the project root, `src`, and an unrelated working directory. The test must assert:

- the same application-root config is loaded in every case;
- no `bundle_config.json` is created in the working directory;
- drift warnings are visible on the GUI path as well as the CLI path.

### F-03 - PREP version increment conflicts with multi-build supersession

**Severity:** High, potentially release-blocking  
**Status:** Requires George/Ringo ruling before a skipped-build install.

The supplied `PREP_AND_STAGE_BFT.bat` reads the outgoing `VERSION.txt` before staging and, after a successful installer return, writes `outgoing build + 1`. Builds 107 and 108 explicitly permit installation over several prior builds. Those two contracts are incompatible:

- outgoing 2.1.105 + Build 108 kit -> PREP writes 2.1.106;
- outgoing 2.1.106 + Build 108 kit -> PREP writes 2.1.107;
- only outgoing 2.1.107 happens to leave 2.1.108.

This can create post-install version disagreement after the installer and tests have already passed.

**Recommendation:** Ratify one version owner:

1. **Preferred:** The governed delivery payload/installer owns every version surface. PREP verifies the installed value against delivery metadata and never computes a replacement.
2. **Alternative:** Preserve `+1`, but then the stager must reject any kit that is not exactly the next build and the build records must stop claiming multi-build supersession.

Add an installation matrix proving 105/106/107/108 -> 109 leaves `VERSION.txt`, `core.version`, CLI `--version`, package metadata, config version, and manifest metadata at one identical value.

### F-04 - JSONL remains a validated but unavailable profile

**Severity:** High  
**Status:** Open Build 100 mandatory scope.

`ConfigManager._validate_profile()` accepts `jsonl`, while `ProfileRegistry` registers only `plain_marker` and `md_fence`. I verified that a configuration selecting JSONL validates successfully and then registry resolution raises `ProfileNotFoundError`.

Build 105's statement that every configurable profile is registered is therefore too broad; its tests bind the packaged/governed **default** and the two shipped implementations, not every value accepted by validation. The Build 100 specification requires JSONL unless it is removed from configuration and documentation.

**Recommendation:** Implement JSONL in Build 110 before Web work. If the owner intentionally defers it, remove `jsonl` atomically from validation, documentation, samples, exceptions, and acceptance tables under an explicit ratification amendment. Do not leave a value that validates but cannot execute.

### F-05 - The tri-UI service boundary is still not in force

**Severity:** High architectural debt  
**Status:** Known in part; roadmap needs explicit Tkinter work.

The Build 100 rule is unambiguous: CLI, Tkinter, and Web must call `BundleToolService`, and UI modules must not construct `BundleParser`, `BundleWriter`, `BundleCreator`, or `ProfileRegistry` directly.

Build 108 still has:

- `cli.py` constructing parser/writer/creator directly;
- `ui/bundle_frame.py` constructing `BundleCreator` and using the registry directly;
- `ui/unbundle_frame.py` constructing `BundleParser` and `BundleWriter` directly.

George schedules CLI facade migration in Build 110 but does not explicitly schedule Tkinter facade migration. The Web adapter should not be added while the two existing UIs remain on different orchestration paths.

**Recommendation:** Add **Tkinter facade migration** to Build 110 beside CLI migration. The Build 110 exit gate should AST-check that CLI and both Tkinter frames do not import or construct the lower-level operational classes.

### F-06 - Service extraction progress is not granular

**Severity:** Medium  
**Status:** Open before facade migration/Web.

`BundleToolService.extract_bundle()` emits a write event at 0 and another at completion but does not pass its sink into `BundleWriter.extract_manifest()`. In an executable check with two files, service write currents were `[0, 2]`, not a rising per-file sequence. The current facade test only checks that a completion phase exists, so it cannot catch this omission.

**Recommendation for Build 110:** Pass the sink through without producing duplicated/conflicting events, then assert an end-to-end service sequence with monotonic per-file values. This is required before CLI, Tkinter, or Web relies exclusively on the facade.

### F-07 - The frozen progress ruling and implementation are not textually identical

**Severity:** Medium governance ambiguity  
**Status:** Resolve by corrigendum before Web serializes the contract.

George's ruling presents `mode` as a dataclass field, integer counts, non-optional `message`, and operation examples including `unbundle`. Build 108 actually has:

- dataclass fields `operation`, `phase`, `current: float`, `total: Optional[float]`, `unit`, and `message: Optional[str]`;
- `mode` as a derived property included in `to_dict()`;
- operation constant `extract`, not `unbundle`.

The actual implementation is internally coherent and the derived `mode` is preferable because it prevents contradictory `mode`/`total` combinations. The issue is the claim that the contract is now frozen while the ruling and code describe different schemas.

**Recommendation:** George should issue a short contract corrigendum freezing the **implemented** representation unless he specifically wants code changes. Freeze both the Python object and serialized JSON shape, including operation vocabulary.

### F-08 - Source header/lifecycle metadata remains inconsistent

**Severity:** Low  
**Status:** Documentation/QC debt.

The Build 108 runtime version is 2.1.108, but many source headers still state 2.1.0, 2.1.1, 2.1.103, or 2.1.106 and use mixed lifecycle/status vocabularies. This does not defeat the canonical runtime version module, but it conflicts with the Build 100 normalization objective and the team header/lifecycle rules.

**Recommendation:** Treat source-header version as module-introduction/history metadata only if that is intentional and document the rule. Otherwise normalize headers mechanically during the Build 111 QA freeze and enforce the selected vocabulary with catalog checks.

---

## 5. Assessment of George's architectural rulings

### Option B+ header policy

**Concur.** It is the lowest-risk immediate correction and preserves the ratified `add_headers=True` default. A future comment-syntax registry may be useful, but it should be a separate feature, not part of the integrity repair.

### Tri-layer governed artifact defense

**Concur, with two qualifications.** Operational quarantine is mandatory because current code cannot neutralize a stale executable elsewhere. Filesystem write protection is a useful second boundary. Hash telemetry is appropriate for detection and forensics. However:

1. The current GUI path must first be corrected so all current surfaces address the same governed file.
2. The installer must verify both removal and restoration of protection on every success, failure, rollback, and idempotent path. A failed installation must not leave the config writable.

Telemetry should report the expected/actual hash, application version, executable path, and timestamp, while avoiding unnecessary user data.

### GOV-POL-001 stale-tree policy

**Concur.** The policy should distinguish inert archives from runnable trees and apply to BFT, pyprojectmgr, PyThermX, and EDSM. Owner action is operationally necessary now; automation can prevent reintroduction later.

### OperationProgress freeze

**Concur with the semantics, subject to the F-07 corrigendum.** The renderer-neutral event, `None` for unknown percentage, never-raise sink, six phases, and AST-enforced layering are strong family-standard choices.

---

## 6. Recommended governed sequence

| Build | Required scope | Exit gate |
|---|---|---|
| **109** | Option B+; default multi-format round trip; Layer C/A config defense; current-GUI config anchoring; PREP/version-owner correction; contract corrigendum; supersession cross-references. | Default structured files remain valid/byte-pure; no CWD config creation; OS protection survives success/failure/rollback; every permitted predecessor installs to one consistent 2.1.109 version; full kit tests pass. |
| **110** | CLI **and Tkinter** migration to `BundleToolService`; service extraction progress pass-through; cooperative cancellation; JSONL implementation or explicit ratified removal. | No CLI/Tk operational imports of parser/writer/creator/registry; cancellation reconciles partial work safely; JSONL config/registry/spec agree; per-file service progress is monotonic. |
| **111** | Local Web adapter; headless coverage for remaining Tk frames; full tri-UI parity and Build 100 acceptance matrix. | Same requests produce equivalent service results across CLI/Tk/Web; stable endpoints/DOM IDs pass contract tests; no duplicated business logic; Build 100 specification status is reconciled line by line. |

This sequence avoids a new design cycle. It preserves George's Build 109-111 plan while adding the minimum missing closure items to the builds where they naturally belong.

---

## 7. Immediate responsibility matrix

| Assignee | Immediate action |
|---|---|
| **Ringo** | Archive/quarantine every stale runnable BFT tree and remove superseded delivery zips from active staging locations. Before staging Build 108, confirm the live `VERSION.txt`; do not use the current PREP path for a 105/106 -> 108 jump until F-03 is resolved. |
| **George** | Issue the OperationProgress corrigendum and rule on delivery-version ownership. Add GUI anchoring and version-surface consistency to Build 109's binding gates. |
| **John** | Implement Build 109 with Option B+, config self-defense, GUI anchoring, and the approved version fix. Add tests that reproduce each defect before correcting it. |
| **Paul** | Update the Build 100 readiness/work-package record: WP2 foundation delivered but adapter migration incomplete; WP5 CLI pending; Tkinter facade migration pending; WP7 Web pending; JSONL pending; Build 109 governance gates expanded. |

---

## 8. Final conclusion

Builds 105-108 are strong and disciplined progress. The key architectural choices are correct: a service boundary, renderer-neutral progress, UI-thread isolation, stderr purity, optional PyThermX integration, and governed artifact defense. George's Build 108 ratification is justified for the scope actually delivered.

The project is not yet at the Build 100 target state. The next risk is not lack of progress-bar functionality; it is allowing partial architectural completion to be mistaken for product completion. Build 109 must close the default data-corruption path and configuration/delivery governance gaps. Build 110 must put both existing interfaces onto the service and settle JSONL. Only then should Build 111 add the Web UI and claim tri-UI parity.

**Recommended decision:** Accept the Build 105-108 development baseline and proceed under the expanded Build 109-111 gates above. Do not declare the BFT v2.1 Build 100 program complete until the final parity, profile, delivery, and default multi-format acceptance matrix passes.

---

**Paul**  
Lead Analyst and Collaborative Developer
