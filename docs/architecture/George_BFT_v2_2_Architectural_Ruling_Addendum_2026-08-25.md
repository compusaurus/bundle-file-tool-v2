# Architectural Ruling Addendum — BFT v2.2 Selection Workspace

**Document Ref:** `ARCH-RULING-ADDENDUM-2026-08-25-01`  
**From:** George, Lead Architect  
**To:** John (Lead Developer) · Paul (Lead Analyst) · Ringo (Product Owner)  
**Date:** 2026-08-25  
**Responds to:** `BFT-DEV-REVIEW-2026-08-25-01` (John), `BFT_SELECTION_WORKSPACE_DESIGN_SPEC.docx` (Paul), and `ARCH-RULING-2026-08-25-01` (George)  
**Baseline:** BFT v2.1 Build 112, 897 tests, PyThermX 0.5.0  
**Status:** Ratified Architectural Decisions & Action Plan

---

## 1\. Executive Summary & Team Disposition

John’s empirical review (`BFT-DEV-REVIEW-2026-08-25-01`) provides crucial clarity on the interaction between detector heuristics, precedence laddering, and formatting costs. Paul’s foundational specification remains the target baseline; this addendum provides the definitive architectural rulings on the six core items in §3 and the four operational items in §4, fully unblocking **WP1 (Selection Core)** and **WP2 (Detectors)** without necessitating a broader redesign.

---

## 2\. Rulings on Core Review Items (§3)

### 2.1 Environment Detectors — Conjunction per Family (§3.1)

* **Finding:** Disjunction signatures (`PYTHON_ENV_SIGNATURES`) risk false-positive pruning of repository trees containing isolated scripts (e.g., `bin/activate`).  
* **Architectural Ruling:** **Ratified.** We adopt Paul’s conjunctive requirement across distinct environment families. A directory is pruned prior to descent only when a primary marker is corroborated by expected layout markers:  
  * **venv / virtualenv:** `pyvenv.cfg` **AND** (`Scripts/python*.exe` OR `bin/python*`)  
  * **conda:** `conda-meta/` **AND** `conda-meta/history`  
  * **node:** `node_modules/` **AND** `package.json` at parent  
  * **Ambiguous markers:** Single standalone markers (e.g., standalone `bin/activate`) evaluate to status `Unknown`. They are traversed, indexed into metadata, and flagged in the selection report for user inspection rather than silently pruned.

### 2.2 Precedence Ladder — Hard Safety vs. Governed Defaults (§3.2)

* **Finding:** Merging safety invariants (recursion hazards, archives, nested bundles) with noise reduction rules under a single Priority 5 baseline permits single-click overrides of structural integrity.  
* **Architectural Ruling:** **Ratified.** The baseline configuration is bifurcated into two distinct ladder tiers:  
  * **Priority 0 (Hard Safety Invariants — Non-Overridable):** Nested bundle patterns (`**/*_bundle_*.txt`), binary archives (`**/*.zip`, `**/*.tar*`, `**/*.whl`, `**/archives/**`), path traversal targets, and self-ingestion targets. These cannot be overridden by user session, presets, or CLI flags.  
  * **Priority 5 (Governed Defaults / Policy — Overridable):** Noise reduction and cache globs (`__pycache__`, `.pytest_cache`, `htmlcov`, `.idea`, `*.pyc`). Overridable via explicit Priority 1 session toggles or Priority 2 CLI flags.

### 2.3 Authoritative Plan Evaluation vs. Create-Time Integrity Gates (§3.3)

* **Finding:** Discrepancies between plan decisions (`Included`) and create-time validation (`assert_bundle_clean()` raising `ValidationError`) violate plan authoritativeness.  
* **Architectural Ruling:** **Ratified.** All emit-blocking invariants must be evaluated during plan generation. If an entry matches a Priority 0 safety denial or fails an integrity check, the plan engine must emit `Blocked` with an explicit reason code (e.g., `BLOCKED_NESTED_BUNDLE_RECURSION`). The invariant is: *A plan status of `Included` guarantees emission without downstream validation failure.*

### 2.4 Preview Pane Performance & Viewport Architecture (§3.4)

* **Finding:** Full-payload transport formatting (`plain_marker` boundary token derivation) costs \~1,084 ms at 4,000 files (8.6 MB), exceeding the 250 ms debounce window and starving the UI thread.  
* **Architectural Ruling & Product Recommendation (for Ringo):**  
  * **Core Workspace Role:** The primary workspace view is designed for file triage, boundary inspection, rule matching, and decision-tree manipulation—not serialized text consumption.  
  * **Pipeline Separation:** Decouple Selection Planning (`SelectionPlan` generation, \<50 ms SLA) from Transport Serialization (`plain_marker` / token emission).  
  * **UI Viewport Specification:** The default preview pane displays the interactive Decision Tree, File List, Group Ordering, and Budget Summary (file count, estimated token count, estimated bytes). Text serialization is rendered on-demand in a dedicated "Preview Output" tab or bounded to the first $N$ entries (default: 50 KB / 10 files). Full artifact formatting occurs strictly upon "Create Bundle" execution.

### 2.5 Scoping of Glob Force-Includes on Pruned Subtrees (§3.5)

* **Finding:** Glob patterns targeting pruned roots (e.g., `--force-include ".venv312/**/pytest/**"`) require unbudgeted recursive scans of ignored hierarchies.  
* **Architectural Ruling:** **Ratified.** Force-include globs match strictly against the unpruned metadata index. Reaching into a pruned root requires either an explicit literal file path or an explicit root un-prune flag (`--include-root <dir>`). The selection plan report must annotate any glob matches constrained by this boundary.

### 2.6 CLI `--exclude` Semantics and Migration Strategy (§3.6)

* **Finding:** Transitioning `--exclude` from replacing configured deny lists to appending rules is a breaking change for existing automation scripts.  
* **Architectural Ruling:** **Ratified.** `--exclude` operates as an additive session filter (Priority 2). To preserve backward compatibility and clear deprecation paths:  
  * Introduce `--no-default-rules` to clear Priority 5 baselines explicitly.  
  * The CLI will emit a one-line notice to `stderr` when `--exclude` is supplied alongside configured baseline rules, directing users to `--no-default-rules` if complete baseline replacement is desired.

---

## 3\. Rulings on Operational & Quality Items (§4)

| Ref | Item | Architectural Ruling |
| :---- | :---- | :---- |
| **S-07** | **Virtualization vs. Accessibility (AT)** | The underlying `SelectionModel` remains fully addressable in memory. Virtualization applies strictly to Tk UI widget rendering. Expose search, filter, and structured state navigation paths to AT/screen readers to ensure §14 compliance without viewport rendering bottlenecks. |
| **S-08** | **Rule Integrity & Digest Tracking** | Adhering to Build 109 Layer A provenance standards, every generated `SelectionPlan` and output manifest must embed SHA-256 digests of all active rule sources (governed config, `.bft-selection.json`, presets, and CLI overrides). |
| **S-09** | **Payload Size Estimation** | The estimator must apply a 1.33x multiplier to binary payloads (accounting for Base64 encoding) and account for provenance header overhead. The UI will display "Estimated Payload Size" with subtext differentiating source file size from final bundle footprint. |
| **S-10** | **`plan` Subcommand Stdout Policy** | An explicit exemption from Build 105 output purity is granted for the `plan` introspection command. `plan` outputs structured human/JSON planning data to stdout since it does not emit bundle artifacts. `create` and `bundle` commands retain strict zero-stdout purity. |

---

## 4\. Work Package Execution Plan

1. **Paul (Lead Analyst):** Update `BFT_SELECTION_WORKSPACE_DESIGN_SPEC` to integrate the two-tier safety ladder (Priority 0 vs Priority 5), conjunction detector rules, and rule-file schema/fixtures.  
2. **John (Lead Developer):**  
   * Stand up the performance measurement harness against the Build 112 baseline tree.  
   * Proceed immediately with **WP1 (Selection Core)** and **WP2 (Detectors)** based on the ratified rulings above.  
3. **Ringo (Product Owner):** Review and confirm the viewport presentation model (§2.4).  
4. **George (Lead Architect):** Available for collaborative pairing on `SelectionModel` state transitions and WP1 unit test fixtures.

