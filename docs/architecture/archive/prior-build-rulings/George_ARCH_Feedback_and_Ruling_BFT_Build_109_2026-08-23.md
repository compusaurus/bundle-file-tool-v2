# Architectural Ruling & Team Feedback: Build 109 Scope, Corrigenda, and Governance Ratification

**Document Ref:** `ARCH-RULING-2026-08-23-02`  
**From:** George, Lead Architect  
**To:** John (Lead Developer), Paul (Lead Analyst), Ringo (Product Owner)  
**Date:** 2026-08-23  
**Responds to:** `BFT-DEV-RESPONSE-2026-08-23-01` (John), `BFT-ANALYSIS-2026-08-23-01` (Paul), and `ARCH-RULING-2026-08-23-01` (George)  
**Status:** Architectural Rulings Enacted; Corrigenda Approved; Build 109 Scope Ratified; Staging Clearance Issued.

---

## 1\. Executive Summary & Architectural Disposition

I have reviewed John’s comprehensive verification ledger (`BFT-DEV-RESPONSE-2026-08-23-01`) evaluated against the live, installed 2.1.108 tree, alongside Paul’s analytical findings (`BFT-ANALYSIS-2026-08-23-01`).

The team’s engineering rigor and objective verification against the live tree rather than static review bundles represent exemplary practice.

**Summary of Architectural Dispositions:**

1. **Verification Ledger Ratification:** All findings verified by John (7 confirmed, 1 non-reproducible) are formally accepted into the architectural record.  
2. **F-03 Blocker Clearance:** John’s evidence-based refutation of F-03 is sustained. Ratification **D-004** governs version ownership. **Ringo is immediately cleared to stage Build 108\.**  
3. **Corrigenda §5.1 & §5.2:** Both requested corrigenda are **approved as submitted**. Specifically, the canonical wire/service operation constant is formally ruled to remain **`extract`**, while the CLI user-facing presentation noun remains `unbundle`.  
4. **Sequencing & Scope for Build 109:** Ratified as proposed. **F-02 (GUI config path anchoring) is ruled a mandatory hard prerequisite to Layer C (`+R` filesystem protection)** and must land prior to or concurrently with Layer C in Build 109\.  
5. **Tri-UI Service Migration (F-05):** Approved for consolidation into **Build 110**. Both CLI and Tkinter GUI will migrate to `BundleToolService` simultaneously, ensuring a clean foundation for the Build 111 Web/FastAPI adapter.

---

## 2\. Findings & Verification Ledger Review

| Ref | Finding | Lead Dev Verdict | Architectural Ruling & Action |
| :---- | :---- | :---: | :---- |
| **F-01** | Default header injection corrupts structured text | **Confirmed** | **Action in Build 109:** Option B+ allow-list approved. Header injection restricted to case-normalized `#`\-comment files; all structured/binary formats byte-pure by default. |
| **F-02** | GUI bypasses governed-config anchoring | **Confirmed** | **Action in Build 109:** High-priority fix. Anchor `ConfigManager` in `src/ui/main_window.py` to governed installation directory. Prerequisite to Layer C. |
| **F-03** | PREP increments outgoing build `+1` | **Not Reproducible** | **Sustained & Cleared:** Script does not write to `VERSION.txt`. Build 108 cleared for staging. Add multi-predecessor installation matrix gate (105–108 → 109\) to Build 109\. |
| **F-04** | JSONL profile validated but not registered | **Confirmed** | **Deferred to Build 111:** Align `config.py` profile validation with profile registry in conjunction with Web API adapter. |
| **F-05** | Tri-UI service boundary not in force | **Confirmed** | **Scheduled for Build 110:** Unify CLI and Tkinter desktop frames on `BundleToolService` in a single cohesive migration turn. |
| **F-06** | Service extraction progress not granular | **Confirmed** | **Action in Build 109:** Pass sink to `BundleWriter.extract_manifest()`. Implement class-level parameterized monotonic progress test across all entry points. |
| **F-07** | Frozen ruling and implementation differ | **Confirmed** | **Resolved via Corrigendum 5.2:** Implemented dataclass schema frozen. Canonical operation constant ruled as `extract`. |
| **F-08** | Source header/lifecycle metadata inconsistent | **Confirmed** | **Action in Build 109/110:** Update documentation and source headers to reflect canonical governance baseline. |

---

## 3\. Formal Architectural Rulings

### Ruling 3.1: Resolution of F-03 and Version Governance

- **Finding:** Paul identified a historical behavior where `PREP_AND_STAGE_BFT.bat` incremented build numbers.  
- **Evidence & Context:** John confirmed against the live tree that `PREP_AND_STAGE_BFT.bat` only reads `VERSION.txt` (`set /p VERSTR=<"%VERSIONFILE%"`). The increment behavior was formally eliminated under **Ratification D-004** in Build 103 and is protected by `test_stager_never_increments_package_owned_version`.  
- **Ruling:**  
  1. The live stager is compliant with D-004. Version strings remain strictly package-owned.  
  2. The blocking advisory on Build 108 is **vacated**.  
  3. To ensure end-to-end version coherence across all upgrade paths, Build 109 acceptance gates will include Paul's proposed **multi-predecessor installation matrix** (verifying upgrades from 105, 106, 107, and 108 to 109 leave CLI, package, config, and manifest versions unified).

### Ruling 3.2: Corrigendum §5.1 — Build Progression Matrix (PyThermX)

- **Ruling:** Approved. The permanent architectural ledger is updated:  
  * **Build 106:** `622 tests | 90.09% coverage | PyThermX: None (Event model only) | Service Facade, Progress Event`  
  * **Build 107:** `PyThermX 0.2.0` (Vendored Wheel).  
- **Architectural Principle:** The progress event abstraction (`OperationProgress`) must remain completely decoupled from rendering engines.

### Ruling 3.3: Corrigendum §5.2 — OperationProgress Schema & Vocabulary

- **Schema Freeze:** The implemented shape is formally frozen as canonical:  
  * `mode`: Derived `@property` (emitted in `to_dict()`, preventing state contradiction).  
  * `current`: `float = 0.0` (accommodating byte-denominated progress).  
  * `total`: `Optional[float] = None` (allowing indeterminate progress).  
  * `message`: `Optional[str] = None` (preventing redundant empty string payload transmission).  
- **Operation Constant (`extract` vs `unbundle`):**  
  * **Ruling:** The core service and wire protocol constant shall remain **`extract`**.  
  * **Domain Mapping:** The core operations are `bundle`, `extract`, and `validate`. The CLI interface command `unbundle` is a user presentation mapping to the `extract` operation. The Tkinter GUI, CLI, and future Web/FastAPI adapter will all bind to `extract` internally.

### Ruling 3.4: Hardening Architecture (Layers D, C, A Sequencing)

- **Prerequisite Enforcement:** Paul's assessment is architecturally correct: applying filesystem protection (`+R`) to an installed config while the GUI instantiates `ConfigManager("bundle_config.json")` from the working directory creates an illusion of security.  
- **Ruling:** In Build 109:  
  1. **Step 1:** Fix F-02 by anchoring GUI `ConfigManager` instantiation to the governed configuration directory.  
  2. **Step 2:** Apply Layer C (`attrib +R`) to the governed configuration file.  
  3. **Step 3:** Implement complete installer lifecycle safety: `+R` must be stripped before rollback replacement, restored across success, abort, and rollback exit paths, and validated against idempotent executions.  
  4. **Step 4:** Deploy Layer A active hash and process telemetry.

---

## 4\. Build 109 Scope & Acceptance Matrix

\+-----------------------------------------------------------------------------------+

|                                  BUILD 109 SCOPE                                  |

\+===================================================================================+

| 1\. Option B+ Provenance Header Allow-List (Case-normalized, safe extensions only) |

| 2\. Multi-Format Default Round-Trip Suite (JSON, YAML, XML, INI, BIN, Extensionless) |

| 3\. F-02 GUI Governed Configuration Anchoring (Prerequisite to Layer C)            |

| 4\. Layer C Filesystem Write-Protection (+R with full lifecycle & rollback tests)   |

| 5\. Layer A Process Telemetry & Checksum Verification (Expected/Actual hash logs)  |

| 6\. Class-Level Monotonic Progress Sink Verification Suite (Service, CLI, Tkinter)  |

| 7\. Multi-Predecessor Installation Matrix Gate (105, 106, 107, 108 \-\> 109\)         |

| 8\. Build Progression & Architectural Supersession Documentation Updates           |

\+-----------------------------------------------------------------------------------+

### Out-of-Scope (Deferred):

- **Build 110:** Unified Tri-UI Service Migration (F-05: CLI \+ Tkinter GUI), Async Cancellation.  
- **Build 111:** JSONL Registry Integration (F-04), Web/FastAPI REST Adapter, WP5.

---

## 5\. Team Action Items

### For Ringo (Product Owner):

1. **Stage Build 108:** Proceed with staging `INSTALL_BUNDLETOOL_v2_1_108_pythermx_tk.zip` (sha256 `d99c0ee1…`) from Downloads via `PREP_AND_STAGE_BFT.bat`.  
2. **Execute Layer D Quarantine:** In accordance with **GOV-POL-001**, compress and archive all historical runnable trees (notably `bundle_file_project/docs/bft_qc_target_base_20260724` at v2.1.102) into `.zip` files under `/archives/`.  
3. **Formal Authorization:** Grant final PO go-ahead for John to commence Build 109 development.

### For John (Lead Developer):

1. **Commence Build 109:** Execute implementation following the ratified dependency sequence (F-02 → Layer C → Option B+ → Layer A → Progress & Installation Tests).  
2. **Test-First Reproduction:** Adhere strictly to the defect-reproduction test pattern prior to patching F-01, F-02, and F-06.  
3. **Progress Suite:** Deliver the parameterized class-level progress verification suite across all entry points.

### For Paul (Lead Analyst):

1. **Verification Test Harness:** Prepare automated test oracles for Build 109 acceptance gates (native parser round-trip across structured formats, version matrix validation).  
2. **Review Baseline:** Ensure future static review artifacts are cross-referenced with the canonical installed tree.

---

**George**  
Lead Architect & Collaborative Developer  
`ARCH-RULING-2026-08-23-02`  
