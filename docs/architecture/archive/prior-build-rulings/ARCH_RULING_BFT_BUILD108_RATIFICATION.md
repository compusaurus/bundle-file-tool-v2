# ARCHITECTURAL RULING & STRATEGIC RATIFICATION BRIEF

**Document Ref:** `ARCH-RULING-2026-08-23-01`  
**From:** George, Lead Architect & Collaborative Developer  
**To:** Ringo (Product Owner) — *Strategic Awareness & Operational Action*  
**Cc:** Paul (Lead Analyst) — *Governance Sequencing & Work Package Tracking*  
**Cc:** John (Lead Developer) — *Technical Implementation & Build Execution*  
**Date:** 2026-08-23  
**Subject:** Ratification of Builds 105–108, Formal Rulings on DEFECT-BFT-001 & GOV-BFT-001, OperationProgress Contract Freezing, and Roadmap for Build 109+  
**Scope:** Bundle File Tool (BFT) v2.1, with Architectural Governance Implications for `pyprojectmgr`, `PyThermX`, and `EDSS/EDSM`

---

## EXECUTIVE SUMMARY & ARCHITECTURAL DISPOSITION

The forensic and development work completed across Builds 105, 106, 107, and 108 represents exceptional technical discipline. John’s root-cause analyses on **DEFECT-BFT-001** and **GOV-BFT-001** demonstrate exact, evidence-driven engineering: hypothesis testing with byte-level precision, elimination of false culprits (`pyprojectmgr` and the installed Build 107), and total transparency regarding historical test omissions.

As Lead Architect, I issue the following binding rulings and formal ratifications:

1. **DEFECT-BFT-001 (Extract-Time Header Injection):**  
   *Ruling:* Adopt **Option B+ (Strict Comment Extension Allow-List with Safe Skipping)** for Build 109\. Maintain `add_headers=True` as the default shipped setting. Mandate a comprehensive, multi-format round-trip test matrix under default settings across all supported file formats.  
2. **GOV-BFT-001 (Governed Artifact Self-Defense):**  
   *Ruling:* Deploy a **Tri-Layer Defense Model (D \+ C \+ A)**. Layer D (Operational Quarantine of Stale Runnable Trees) is mandatory and effective immediately. Layer C (Filesystem Write-Protection via OS Read-Only Flags managed by the installer) is ratified for Build 109\. Layer A (Startup SHA-256 and Process Telemetry Logging) is ratified for telemetry.  
3. **GOV-POL-001 (Family Policy on Stale Trees):**  
   *Ruling:* Zero stale runnable installations permitted in active development workspaces. Historical/reference copies must reside exclusively as compressed archives (`archives/*.zip`).  
4. **OperationProgress Contract Ratification:**  
   *Ruling:* The `OperationProgress` contract schema, `Optional[float]` percentage semantics, never-raise sink guarantee, canonical 6-phase vocabulary (`discover`, `read`, `format`, `parse`, `write`, `complete`), and strict AST-enforced architectural layering are **formally ratified and frozen**.  
5. **Build 107 & 108 Technical Ratifications:**  
   *Ruling:* The PyThermX 0.3.1 upgrade, worker-thread UI decoupling (`bft-progress`), UI configuration schema (`ui.progress`), `.whl` safety deny-list addition, and the canonical family helper hash (`380037a3…`) are **ratified into the permanent baseline**.  
6. **Strategic Sequencing Directive (Build 109+):**  
   *Ruling:* Build 109 will deliver DEFECT-BFT-001 \+ GOV-BFT-001 defenses \+ Multi-Format Matrix. Build 110 will execute WP5 (CLI Facade Migration) and the Cooperative Cancellation Protocol.

---

## 1\. FORMAL ARCHITECTURAL RULING: DEFECT-BFT-001

### Extract-Time Header Injection Corrupting Structured Text

\+-----------------------------------------------------------------------------------+

| ROOT CAUSE ANALYSIS: DEFECT-BFT-001                                               |

|                                                                                   |

|  BundleWriter.write\_entry                                                         |

|  ├── File Type Check: NONE (applied blindly to all text entries)                  |

|  ├── Header Syntax: Fixed '\#' comment lines                                       |

|  └── Default Setting: add\_headers=True (app\_defaults.add\_headers)                 |

|                                                                                   |

|  TEST SUITE PATHOLOGY:                                                            |

|  └── tests/unit/test\_roundtrip.py hardcoded add\_headers=False across all tests.   |

|      Result: 100% green CI suite asserting a mode our end-users never run\!       |

\+-----------------------------------------------------------------------------------+

### 1.1 Decision on Remedy: Option B+ (Immediate) & Phased Extension

- **Approved Remedy:** **Option B+ (Targeted Header Allow-List with Safe Text Extraction)** for Build 109\.  
- **Mechanics:**  
  `BundleWriter.write_entry` must inspect the entry’s file extension / format identifier against a governed allow-list of known `#`\-comment compatible formats before prefixing `#` header blocks:  
    
  HASH\_COMMENT\_EXTENSIONS \= frozenset({  
    
      ".py", ".pyw", ".sh", ".bash", ".zsh", ".ksh", ".csh",  
    
      ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",  
    
      ".r", ".rb", ".pl", ".pm", ".tcl", ".dockerfile",  
    
      ".env", ".properties", ".ps1", ".psm1"  
    
  })  
    
  \# Exact filename matches (case-insensitive)  
    
  HASH\_COMMENT\_FILENAMES \= frozenset({  
    
      "dockerfile", "makefile", "gemfile", "vagrantfile", "inventory"  
    
  })  
    
- If `entry.ext` (or filename) is not in this set (e.g., `.json`, `.xml`, `.html`, `.css`, `.sql`, `.js`, `.ts`, `.c`, `.cpp`, `.h`, `.java`, `.csv`, `.md`), the writer **must omit the `#` comment header** and extract the raw, untouched text payload.  
- **Why Not Option A Now?** Option A (comment syntax mapping per language) is architecturally desirable for polyglot codebases (e.g., `//` for JS/C/Java, `<!-- -->` for HTML/XML, `/* */` for CSS/SQL), but it requires a dedicated parser/comment formatter registry and still requires a skip rule for commentless formats like JSON. Option B+ immediately restores 100% fidelity to JSON, HTML, CSS, SQL, and JS with zero regression risk. Option A is scheduled for future exploration as a dedicated feature proposal.  
- **Why Not Option C?** Flipping `add_headers=False` merely hides the defect by altering user expectations, breaks Team Directive v4 provenance tracking, and does not solve the underlying defect.

### 1.2 Default Setting Ruling

- **Ruling:** `add_headers=True` **remains the ratified shipped default**.  
- With Option B+ in place, `add_headers=True` injects provenance headers where they are syntactically valid and completely harmless (`.py`, `.sh`, `.yaml`), and silently skips them where they would cause syntax errors (`.json`, `.html`, `.xml`).

### 1.3 Testing Mandate & Verification Contract

- **Mandatory Control for Build 109:** Implement `tests/integration/test_multiformat_roundtrip_default.py`.  
- **Test Specification:**  
  1. Construct a synthetic repository containing: `.py`, `.json`, `.yaml`, `.toml`, `.html`, `.xml`, `.css`, `.js`, `.sql`, `.md`, `.txt`, and binary `.png`/`.whl`.  
  2. Bundle the repository under the default configuration (`add_headers=True`).  
  3. Extract the bundle into an isolated scratch tree using default settings.  
  4. Assert that every structured format parses validly using its native engine (`json.loads()`, `yaml.safe_load()`, `tomllib.loads()`, `xml.etree.ElementTree.fromstring()`, `ast.parse()`).  
  5. Assert that `#`\-comment formats contain the verified provenance block, while structured/non-comment formats are byte-pure identical to source.

---

## 2\. FORMAL ARCHITECTURAL RULING: GOV-BFT-001

### Governed Artifact Self-Defense & Stale Deployment Governance

\+-----------------------------------------------------------------------------------+

| ANATOMY OF CONFIGURATION DRIFT (4th Recurrence — 2026-08-23 11:54:52)             |

|                                                                                   |

|  \[Developer Workstation\]                                                          |

|       │                                                                           |

|       ├─► (Active) BFT v2.1 Build 107/108 (src/core/config.py \-\> ReadOnlyConfig)  |

|       │      └── BLOCKED from writing config. Resolves path from App Root.        |

|       │                                                                           |

|       └─► (Stale) BFT Build 101/104 in docs/ or bundle\_file\_project/              |

|              └── Launched with Active Project Root as CWD.                        |

|              └── Resolves bundle\_config.json relative to CWD.                     |

|              └── Blindly executes legacy save-all UI state routine\!               |

\+-----------------------------------------------------------------------------------+

### 2.1 The Tri-Layer Defense Architecture (D \+ C \+ A)

To permanently eliminate foreign and stale writers across the machine, we adopt three interlocking layers of defense:

                  ┌────────────────────────────────────────┐

                  │ LAYER D: Operational Quarantine        │

                  │ Purge/Archive all pre-105 runnable     │

                  │ directories from the workstation.      │

                  └──────────────────┬─────────────────────┘

                                     │

                                     ▼

                  ┌────────────────────────────────────────┐

                  │ LAYER C: Filesystem Immunitization     │

                  │ Installer sets Read-Only OS attribute  │

                  │ (attrib \+R / chmod 444\) on config.     │

                  └──────────────────┬─────────────────────┘

                                     │

                                     ▼

                  ┌────────────────────────────────────────┐

                  │ LAYER A: Active Telemetry & Ledger     │

                  │ Startup SHA-256 verification against   │

                  │ manifest \+ forensic stderr alert.      │

                  └────────────────────────────────────────┘

#### Layer D: Operational Quarantine (Effective Immediately — Owner Action)

- **Mandatory Action for Ringo:** Archive or delete all legacy, un-gated copies of Bundle File Tool on development machines, specifically:  
  - `docs/bft_qc_target_base_20260724`  
  - `bundle_file_project/bundle_file_tool_v2  Build 101/`  
  - Any historical bundles extracted as runnable code trees.  
- Historical reference builds must be converted into standard non-executable `.zip` archives under `archives/`.

#### Layer C: Filesystem Immunitization (Automated via Installer)

- **Implementation:** The installation script `FAMILY_DELIVERY_HELPERS_v2_0.bat` (and `PREP_AND_STAGE_BFT.bat`) will enforce filesystem write protection:  
  - **Gate C (Pre-Install):** Strip Read-Only flag (`attrib -R bundle_config.json`) prior to placing verified payload.  
  - **Gate D (Post-Install):** Apply OS Read-Only flag (`attrib +R bundle_config.json` on Windows; `chmod 444` on POSIX).  
- **Result:** Any legacy, rogue, or foreign process attempting to open `bundle_config.json` in write mode (`'w'`) will instantly receive an OS-level `PermissionError` / `Access Denied` and fail without corrupting the governed document.

#### Layer A: Active Verification & Telemetry Ledger

- **Implementation:** `ConfigManager.load()` will verify the runtime SHA-256 of `bundle_config.json` against the cryptographic hash recorded in `.pyprojectmgr/project_manifest.json`.  
- If a hash mismatch is detected, the CLI and UI will log a high-visibility warning to `stderr` recording the timestamp, expected hash, detected hash, and process executable path.

### 2.2 Family Policy Standard: GOV-POL-001

- **Policy Statement:**  
  *No developer workstation or production host may maintain runnable, un-gated legacy versions of software family tools (`pyprojectmgr`, `BFT`, `PyThermX`, `EDSS/EDSM`) in unmanaged directories.*  
- All prior versions must be archived as inert `.zip` artifacts.

---

## 3\. FORMAL RATIFICATION: OPERATIONPROGRESS CONTRACT

### Resolving Build 106 §8, Build 107 §12, and Build 108 §11

The `OperationProgress` protocol designed by Paul and implemented by John is hereby **formally ratified and declared the Family Standard Progress Contract**.

@dataclass(frozen=True)

class OperationProgress:

    operation: str               \# "bundle", "unbundle", "validate"

    phase: str                   \# "discover", "read", "format", "parse", "write", "complete"

    mode: str                    \# "indeterminate", "determinate"

    current: int                 \# current units processed

    total: Optional\[int\]         \# total units (None when indeterminate)

    unit: str                    \# "files", "bytes", "entries"

    message: str                 \# human-readable context

    

    @property

    def percent(self) \-\> Optional\[float\]:

        if self.total is None or self.total \<= 0:

            return None

        return min(100.0, (self.current / self.total) \* 100.0)

### Architectural Contract Clauses:

1. **Schema & Field Set:** Ratified as specified above. All future attributes must be additive with default values.  
2. **Indeterminate Representation:** `percent` returning `Optional[float]` (`None` during indeterminate discovery, never `0.0`) is ratified.  
3. **Never-Raise Sink Guarantee:** Sinks wrapped via `emit()` must swallow consumer exceptions unconditionally. Progress reporting is an observational diagnostic and must never jeopardize operation execution.  
4. **Frozen Phase Vocabulary:** The canonical phase vocabulary is locked to: `['discover', 'read', 'format', 'parse', 'write', 'complete']`.  
5. **Architectural Layering Rule:** Zero GUI/Renderer imports in `src/core/`. Enforced via AST-parser tests across all core modules.

---

## 4\. TECHNICAL REVIEW: BUILDS 105, 106, 107, AND 108

\+-----------------------------------------------------------------------------------+

| BFT v2.1 BUILD PROGRESSION & MATURATION MATRIX                                    |

\+-----------+--------+----------+---------------+-----------------------------------+

| Build     | Tests  | Coverage | PyThermX Ver  | Architectural Milestone Delivered |

\+-----------+--------+----------+---------------+-----------------------------------+

| Build 105 | 592    | 89.75%   | N/A (None)    | Registry Fix, CWD Anchor, Purity  |

| Build 106 | 622    | 90.09%   | 0.1.0 (Stub)  | Service Facade, Progress Event    |

| Build 107 | 661    | 90.23%   | 0.2.0 (Kit)   | CLI Progress Adapter, Handoff     |

| Build 108 | 702    | 90.29%   | 0.3.1 (Kit)   | Tkinter Worker Thread, Pin Eval   |

\+-----------+--------+----------+---------------+-----------------------------------+

### 4.1 Key Architecture & Quality Highlights Ratified

- **Thread Isolation in Tkinter (Build 108):** Running folder scans on dedicated background threads (`bft-progress`) while pumping progress messages onto the Tk main loop completely solves the UI freeze defect.  
- **Safety Deny-List Completion (Build 107):** Ratification of `**/*.whl` added to the deny list alongside `**/*.zip` and `**/*.tar` ensures self-bundles remain compact and secure.  
- **Dynamic Pin Specifier Evaluation (Build 108):** Replacing floor-only test assertions with `packaging.specifiers.SpecifierSet` guarantees both lower- and upper-bound dependency enforcement.  
- **Payload & Gate Cleanliness:** All kits verified against canonical include SHA-256 (`380037a3…`).

---

## 5\. ROADMAP & SEQUENCING DIRECTIVE (BUILDS 109 – 111\)

\+-----------------------------------------------------------------------------------+

| MASTER SEQUENCING ROADMAP                                                         |

\+-----------------------------------------------------------------------------------+

|  BUILD 109: Defect Resolution & Governance Hardening                              |

|  ├── \[DEFECT-BFT-001\] Option B+ (\#-comment allow-list & structured text skip)     |

|  ├── \[GOV-BFT-001\] Tri-Layer Defense (attrib \+R in installer \+ telemetry)         |

|  ├── \[TEST-MATRIX\] Parameterized multi-format round-trip test under defaults      |

|  └── \[DOCS\] Supersession cross-references in build records                        |

\+-----------------------------------------------------------------------------------+

|  BUILD 110: Service Facade Consolidation & Cooperative Cancellation               |

|  ├── \[WP5\] Migrate CLI command handlers onto BundleToolService facade             |

|  ├── \[CORE-CANCEL\] Implement CancellationToken protocol in discover/write/read   |

|  └── \[UI-CANCEL\] Wire Cancel button in Tkinter progress modal dialog              |

\+-----------------------------------------------------------------------------------+

|  BUILD 111: Web Adapter & Test Harness Maturation                                 |

|  ├── \[WP7\] Web Service Adapter (Server-Sent Events / WebSocket progress stream)   |

|  ├── \[UI-QC\] Headless Tk test harness for remaining 4 UI frames                   |

|  └── \[UPSTREAM\] Upstream Tri-Layer defense to pyprojectmgr & EDSS                 |

\+-----------------------------------------------------------------------------------+

---

## 6\. TEAM ACTION ITEMS & RESPONSIBILITY MATRIX

| Role | Assignee | Action Required | Target Build / Window |
| :---- | :---- | :---- | :---- |
| **Product Owner** | **Ringo** | Execute Layer D: Archive/quarantine legacy BFT directories (`Build 101`, `QC Target`). Clean `Downloads/` before staging. | Immediate |
| **Lead Analyst** | **Paul** | Sequence Work Packages WP5 (Build 110), WP6/WP7, and log GOV-POL-001 into governance tracker. | Post-Build 108 |
| **Lead Developer** | **John** | Implement Option B+, installer `attrib +R`, multi-format test matrix, and prepare Build 109 kit. | Build 109 |
| **Lead Architect** | **George** | Oversee cancellation token spec, sign off on Build 109 QA gates, and align family templates. | Continuous |

---

**Approved & Ratified:**  
*George, Lead Architect & Collaborative Developer*  
*2026-08-23*  
