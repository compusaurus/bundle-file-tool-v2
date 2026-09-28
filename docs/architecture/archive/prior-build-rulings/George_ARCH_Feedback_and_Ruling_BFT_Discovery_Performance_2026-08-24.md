# ARCHITECTURAL RULING & TEAM MEMORANDUM

**Document Ref:** `ARCH-RULING-2026-08-24-01`  
**From:** George, Lead Architect & Collaborative Developer  
**To:** Ringo (Product Owner), John (Lead Developer), Paul (Lead Analyst)  
**Date:** August 24, 2026  
**Subject:** Architectural Evaluation, Root Cause Confirmation, and Formal Rulings on BFT Discovery Performance & Oversize Asset Handling  
**Responds to:** `bft_discovery_performance_analysis_john.md` (John)  
**Status:** Architectural Rulings Enacted; Build 109 Scope Expansion Approved; Implementation Cleared.

---

## 1\. Executive Summary & Architectural Disposition

I have reviewed John’s comprehensive forensic analysis and benchmark report (`bft_discovery_performance_analysis_john.md`) concerning the folder discovery latency and apparent UI freeze observed during Ringo's screen recording on the `pyprojectmgr_project/pyprojectmgrV2` tree.

John’s empirical investigation demonstrates textbook systems-engineering rigor: isolating the exact mechanism of telemetry starvation (D1, D2, D3), quantifying filesystem traversal overhead with microsecond precision, proving bit-identical payload equivalence, and strictly honoring our team governance policy by not mutating governed source out-of-band.

### Summary of Architectural Rulings:

1. **Discovery Performance Remediation (D1, D2, D3):** **APPROVED & RATIFIED.** John's 3-part patch (directory-level `os.walk` pruning, lazy `path.resolve()` evaluation, and throttled scan-level progress emission) is adopted into the permanent baseline for **Build 109**.  
2. **Oversize Asset Policy & Manifest Resilience:** **RULING: Soft Exclusion with Actionable Warning.** Fatal exceptions on oversized files during manifest generation are permanently retired. BFT will gracefully skip oversized files, record them in `manifest.skipped_entries`, and allow bundle generation for valid files to proceed uninterrupted.  
3. **Safety Deny-List (`safety.deny_globs`) Expansion:** **APPROVED IN TWO TIERS.** Canonical infrastructure caches and environments (`venv`, `node_modules`, `.pytest_cache`, `.ruff_cache`, `.mypy_cache`, `*_bak*`) are added to the default shipped policy in Build 109\. Output directories (`deliverables`, `htmlcov`, `reports`) remain user-governed.  
4. **Build 109 Integration Clearance:** John is authorized to merge the discovery performance engine and oversize file handler directly into the Build 109 delivery candidate.

---

## 2\. Technical Evaluation & Forensic Findings

\+-----------------------------------------------------------------------------------+

| FORENSIC BREAKDOWN: BFT DISCOVERY LATENCY & PROGRESS STARVATION                    |

|                                                                                   |

|  Legacy Pipeline (Builds 101–108):                                                |

|  Path.rglob("\*") ────────────────► path.resolve() ──────────────► should\_include() │

|  \[19,157 nodes walked\]            \[4.08s spent resolving\]        │                │

|                                                                  ├─► TRUE: emit() │

|                                                                  │   (1,336 hits) │

|                                                                  │                │

|                                                                  └─► FALSE: SILENT│

|                                                                      (17,821 nodes│

|                                                                      \= 7.82s hang)|

|                                                                                   |

|  Ratified Architecture (Build 109):                                               |

|  os.walk(top) ───\[Prune dirs\[:\]\]──► Candidate Stream ──► should\_include()         │

|  \[1,433 nodes walked\]              \[Lazy resolve()\]     ├──► emit(throttled 100ms)│

|  (92.5% I/O reduction)             (0.57s total elapsed)└──► Bit-pure Manifest    │

\+-----------------------------------------------------------------------------------+

### 2.1 Confirmation of John's Three Root-Cause Defects

* **D1 — Post-Walk Filtering via `rglob("*")`:** Traversing 16,685 nodes within `.venv` despite active deny patterns created an unmitigated filesystem I/O penalty on Windows NTFS. Pruning `dirs[:]` in-flight eliminates 87%+ of directory recursion upfront.  
* **D2 — Eager `path.resolve()` Invocation:** Normalizing symlinks and canonical paths across 19,157 unvetted nodes consumed 44% of total runtime. Deferring `resolve()` until a path survives candidate filtering is architecturally sound.  
* **D3 — Telemetry Starvation:** Confining `emit()` to the positive match branch starved the PyThermX progress consumer during dense negative subtrees. Emitting throttled events based on *scanned* nodes while reporting `matched / scanned` restores true observability and eliminates misleading throughput metrics.

### 2.2 Corrections to Initial Architectural Hypotheses

John's direct measurements successfully refined two initial observations:

1. **Filter Target Discrepancy:** The target workspace indeed used dotted `.venv` which was already present in `deny_globs`. This confirmed the defect was architectural (traversal mechanics) rather than configuration omission.  
2. **Oversize Asset Identification:** The offending payload was `pyprojectmgr_splash.mp4` (20.58 MB), exceeding the 10 MB ceiling.

---

## 3\. Formal Architectural Rulings

### Ruling 3.1: Directory-Level Pruning & Throttled Progress Protocol

* **Mechanism:** `BundleCreator.discover_files` must derive a top-level directory skip set from configured `deny_globs` (specifically matching `**/<name>/**` patterns) and mutate `dirs[:]` in-place during `os.walk`.  
* **Telemetry Protocol:**  
  * Progress events during the `discover` phase must emit periodically (minimum interval: 100ms) to prevent UI thread message saturation.  
  * The `OperationProgress` message must reflect dual-counter state: `f"Scanning: {len(matched)} included / {scanned_count} scanned"`.  
* **Purity Assertion:** The discovery patch must produce an identical file manifest to the baseline implementation across all supported platforms.

### Ruling 3.2: Resolution of Secondary Finding — Oversize Asset Handling

* **Problem:** In Build 108, `FileSizeError` raised during manifest generation triggers a total UI preview wipe and blocks bundle creation across thousands of healthy files.  
* **Ruling:**  
  1. `max_file_mb` enforcement is formally repositioned from a **fatal operation crash** to a **non-blocking discovery-time exclusion**.  
  2. Oversized files must be categorized as `skipped_oversize` in the manifest summary and excluded from the payload.  
  3. The GUI info panel and CLI summary must display a clear, non-blocking diagnostic:  
     `"Skipped 1 oversized file (> 10.00 MB): assets/splash/pyprojectmgr_splash.mp4 (20.58 MB). Adjust --max-size or deselect to clear."`  
  4. Bundle creation remains fully enabled for all remaining valid candidate files.

### Ruling 3.3: Safety Deny-List Governance (`safety.deny_globs`)

* **Tier 1 (Ratified Shipped Defaults for Build 109):**  
  To protect against common developer workstation overhead, the default configuration in `config.py` is expanded to include:  
    
  DEFAULT\_DENY\_GLOBS \= \[  
    
      "\*\*/.venv/\*\*",  
    
      "\*\*/venv/\*\*",  
    
      "\*\*/\_\_pycache\_\_/\*\*",  
    
      "\*\*/.pytest\_cache/\*\*",  
    
      "\*\*/.mypy\_cache/\*\*",  
    
      "\*\*/.ruff\_cache/\*\*",  
    
      "\*\*/node\_modules/\*\*",  
    
      "\*\*/\*\_bak\*/\*\*",  
    
      "\*\*/\_legacy\_backup/\*\*",  
    
      "\*\*/\_governance\_backups/\*\*",  
    
      "\*.log",  
    
      "\*\*/\*\_bundle\_\*.txt",  
    
      "\*\*/\*.zip",  
    
      "\*\*/\*.tar",  
    
      "\*\*/\*.tar.\*",  
    
      "\*\*/\*.whl",  
    
      "\*\*/archives/\*\*",  
    
  \]  
    
* **Tier 2 (Project & User Governance):**  
  Output directories (`deliverables/`, `reports/`, `htmlcov/`) shall not be denied by hardcoded default. They remain configurable by Ringo or individual project manifests via `bundle_config.json`.

---

## 4\. Build 109 Scope & Sequencing Matrix

With these rulings, Build 109 consolidates our immediate defect resolutions, governance hardening, and performance optimizations:

\+===================================================================================+

|                              RATIFIED BUILD 109 SCOPE                             |

\+===================================================================================+

| 1\. \[PERF-BFT-001\] In-Flight os.walk Directory Pruning (16x Discovery Speedup)     |

| 2\. \[PERF-BFT-002\] Throttled Dual-Counter Telemetry (Eliminates 7.8s Silence Hang)  |

| 3\. \[UX-BFT-001\]   Non-Blocking Oversize File Skipping & Diagnostic Preview Banner  |

| 4\. \[GOV-BFT-002\]  Expanded Default Deny Patterns (venv, caches, backup trees)     |

| 5\. \[DEFECT-BFT-001\] Option B+ Comment Header Allow-List (Byte-Pure Structured Text)|

| 6\. \[GOV-BFT-001\]  Tri-Layer Defense (Layer C attrib \+R & Layer A Startup Checksum) |

| 7\. \[F-02\]         Anchor GUI ConfigManager to Governed Installation Directory     |

| 8\. \[TEST-SUITE\]   Bit-Identical Equivalence & Inter-Event Max Gap (\<= 250ms) Gates|

\+===================================================================================+

---

## 5\. Team Action Items

### For Ringo (Product Owner):

1. **Authorize Build 109 Execution:** Approve inclusion of the discovery performance patch and oversize asset soft-skipping into Build 109\.  
2. **Review Operational Workflows:** Verify that the Tier 1 default deny list matches team expectations across active project workspaces.

### For John (Lead Developer):

1. **Apply Discovery Patch:** Move `docs/discover_files_performance_patch_proposed.py` into `src/core/writer.py` under the Build 109 development branch.  
2. **Implement Oversize Soft-Skip:** Update `BundleCreator.create_manifest()` and `src/ui/bundle_frame.py` to record and warn on oversize files without throwing fatal UI errors.  
3. **Implement Telemetry & Equivalence Gates:**  
   * `test_discover_files_output_identical_to_unpruned_baseline`  
   * `test_discover_files_max_telemetry_gap_under_250ms`  
   * `test_oversized_file_warns_and_allows_bundling`

### For Paul (Lead Analyst):

1. **Harness Integration:** Integrate John’s synthetic benchmark repository into the automated QA verification suite for Build 109 staging.  
2. **Governance Ledger:** Log rulings `PERF-BFT-001`, `PERF-BFT-002`, and `UX-BFT-001` into the permanent BFT governance ledger.

---

**George**  
Lead Architect & Collaborative Developer  
`ARCH-RULING-2026-08-24-01`  
