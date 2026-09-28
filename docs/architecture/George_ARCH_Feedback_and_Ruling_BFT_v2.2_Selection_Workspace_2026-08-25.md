# ARCHITECTURAL RULING & TEAM MEMORANDUM

**Document Ref:** `ARCH-RULING-2026-08-25-01`  
**From:** George, Lead Architect & Collaborative Developer  
**To:** Ringo (Product Owner), Paul (Lead Analyst), John (Lead Developer)  
**Date:** August 25, 2026  
**Subject:** Architectural Analysis, Formal Ratifications, and Technical Risk Assessment for BFT v2.2 Selection Workspace  
**Responds to:** `BFT_SELECTION_WORKSPACE_DESIGN_SPEC.docx` (Paul, Lead Analyst)  
**Status:** Architectural Rulings Enacted; Precedence Ladder & Group Invariants Ratified; WP1 & WP2 Implementation Cleared.

---

## 1\. Executive Summary & Architectural Disposition

I have conducted a thorough architectural analysis of Paul’s comprehensive design specification (*BFT Selection Workspace: Transparent, high-control bundle composition for developers, writers, and mixed-content teams*).

Paul’s specification exhibits exemplary systems-engineering insight. It correctly diagnoses that the screenshot showing 4,084 files and leaked `.venv312` site-packages is **not an isolated glob string omission**, but symptomatic of a fundamental structural coupling in BFT Build 112:

1. **Coupled Path Discovery and Content Ingestion:** Manifest creation and file reading are triggered eagerly on every checkbox toggle (`bundle_frame.py:522-570`), causing catastrophic $O(N)$ I/O and hash recalculations for unchanged files.  
2. **Adapter Policy Divergence:** The desktop UI bypasses shared configuration logic by constructing `BundleCreator()` directly (`bundle_frame.py:72`), creating governance divergence between GUI and CLI.  
3. **Literal Directory Matching vs. Behavioral Classification:** The existing `prunable_dir_names()` contract rejects wildcard directory segments, preventing early directory pruning of versioned virtual environments (such as `.venv312` or `env-app`).

### Summary of Architectural Rulings & Dispositions:

1. **Core Concept & 3-Tier Separation:** **APPROVED & RATIFIED**. Separating **Path Classification** (metadata scan), **Intent Expression** (ordered rules, typed detectors, groups, session overrides), and **Content Ingestion** (incremental cache \+ lazy reads) is architecturally sound and preserves BFT's core invariants of determinism, auditability, and safety.  
2. **Precedence Ladder Ratification (Decision for George):** **RATIFIED**. The 7-layer precedence hierarchy (Priority 0 Hard Safety → Priority 1 Session Overrides → Priority 2 Project Rules → Priority 3 User Presets → Priority 4 Shipped Detectors → Priority 5 Governed Baseline → Priority 6 Base Action) is formally adopted.  
3. **Session Force-Include vs. Detector Boundary (Decision for George):** **RATIFIED WITH EXPLICIT ENFORCEMENT**. A Priority 1 Session Force-Include **may override** ordinary Priority 4 Environment Detectors and Priority 5 Default Exclusions. However, Priority 0 **Hard Safety boundaries** (path traversal outside base, circular symlinks, unreadable paths, and bundle output self-ingestion) remain **strictly non-overridable under all circumstances**.  
4. **Group Metadata & Transport Grammar Invariance (Decision for George):** **RATIFIED**. Group metadata will strictly control **in-memory evaluation, user mental modeling, and manifest output sequencing** in v2.2. No new wire syntax, headers, or envelope delimiters will be added to the underlying transport profiles (`plain_marker`, `markdown_fence`). This guarantees 100% backward compatibility with existing bundle/unbundle parsers.  
5. **Implementation Clearance (WP1 & WP2):** John is authorized to begin immediate implementation of **WP1 (Selection Core)** and **WP2 (Detectors & Directory Pruning)** against the `core/selection.py` and `core/detectors.py` seams.

---

## 2\. In-Depth Concept Analysis & System Architecture

\+-------------------------------------------------------------------------------------------------------+

|                        BFT v2.2 SELECTION WORKSPACE ARCHITECTURAL PIPELINE                           |

|                                                                                                       |

|  \[ Source Root \]                                                                                      |

|        │                                                                                              |

|        ▼                                                                                              |

|  ┌─────────────────────────┐     Signature Proved      ┌───────────────────────────────────────────┐  |

|  │  Metadata-First Scan    │ ────────────────────────► │ Early Directory Pruning (O(1) Skip)       │  |

|  │  (os.scandir / stat)    │   (pyvenv.cfg, etc.)      │ (.venv312, node\_modules, .git, caches)    │  |

|  └──────────┬──────────────┘                           └───────────────────────────────────────────┘  |

|             │ Unpruned Metadata Candidates                                                            |

|             ▼                                                                                         |

|  ┌─────────────────────────────────────────────────────────────────────────────────────────────────┐  |

|  │  core/selection.py: SelectionPlan Engine (Immutable Source Snapshot & Rule Stack)               │  |

|  │                                                                                                 │  |

|  │   Layer 0: Hard Safety (Base Traversal, Self-Ingestion, Bad Symlinks) \[NON-OVERRIDABLE\]         │  |

|  │   Layer 1: Session Overrides (GUI/CLI Checked/Unchecked Flags)                                  │  |

|  │   Layer 2: Project Rule File (.bft-selection.json / \--rules) \[OPT-IN\]                           │  |

|  │   Layer 3: User Personal Presets (%LOCALAPPDATA%/.../selection\_presets/)                         │  |

|  │   Layer 4: Shipped Presets & Typed Detectors (App Dev, Book+Campaign)                          │  |

|  │   Layer 5: Governed Baseline Invariants (bundle\_config.json)                                    │  |

|  │   Layer 6: Base Action (Default Include / Default Exclude)                                      │  |

|  │                                                                                                 │  |

|  │   ──► Computes SelectionDecision per path (State, Winning Rule, Chain, Group, Output Order)  │  |

|  └──────────┬──────────────────────────────────────────────────────────────────────────────────────┘  |

|             │                                                                                         |

|             ├───────────────────────────────────────────┐                                             |

|             ▼                                           ▼                                             |

|  ┌───────────────────────────┐             ┌───────────────────────────┐                              |

|  │  Desktop UI Adapter       │             │  CLI Adapter              │                              |

|  │  (ui/bundle\_frame.py)     │             │  (cli.py)                 │                              |

|  │  \- Tri-state folder tree  │             │  \- plan command           │                              |

|  │  \- Decision list & filter │             │  \- \--explain \<path\>       │                              |

|  │  \- Inspector & rule editor│             │  \- \--report \<path\> (JSON) │                              |

|  │  \- 250ms debounce timer   │             │  \- Preserves stdout purity│                              |

|  └──────────┬────────────────┘             └────────────┬──────────────┘                              |

|             │                                           │                                             |

|             └─────────────────────┬─────────────────────┘                                             |

|                                   ▼                                                                   |

|  ┌─────────────────────────────────────────────────────────────────────────────────────────────────┐  |

|  │  core/service.py: BundleToolService (Single Shared Execution Facade)                            │  |

|  │  \- plan\_bundle()    : Pure metadata planning (Zero file reads)                                  │  |

|  │  \- preview\_bundle() : Incremental cache hit \+ read only newly included/changed (250ms debounced)│  |

|  │  \- create\_bundle()  : Re-stat validation \-\> Read uncached \-\> Integrity Gate \-\> Byte-Pure Output │  |

|  └─────────────────────────────────────────────────────────────────────────────────────────────────┘  |

\+-------------------------------------------------------------------------------------------------------+

### 2.1 The Three Entangled Problems in Build 112

1. **The Re-read Bottleneck:** In Build 112, unchecking a single file in a 4,000-file selection forces `BundleCreator.create_manifest()` to re-open, read, encode, and checksum all 3,999 remaining files. This creates seconds of UI unresponsiveness.  
2. **Policy Drift Across Adapters:** The GUI instantiates `BundleCreator` directly, while CLI uses `cli.py` flag parsing. Neither produces an inspectable decision graph.  
3. **Naive Globs vs. Signature Pruning:** Matching `**/.venv312/**` after walking directory trees wastes thousands of NTFS `stat` operations. True directory pruning must happen *before* directory descent during `os.walk`/`os.scandir`.

### 2.2 The SelectionPlan Paradigm

The introduction of `SelectionPlan` as an immutable evaluation result resolves these architectural flaws:

- **Zero I/O Planning:** Metadata scanning collects only `path`, `size`, `mtime_ns`, and detector evidence.  
- **Explainability as a First-Class Citizen:** Each path is assigned a `SelectionDecision` capturing its final state (`Included`, `Excluded`, `Blocked`, `Skipped`, `Unknown`), winning rule ID, layer priority, full evaluation chain, and override history.  
- **Single Facade Entry Point:** Both the GUI (`bundle_frame.py`) and CLI (`cli.py`) interact exclusively with `core/service.py:BundleToolService`.

---

## 3\. Formal Architectural Rulings

### Ruling 3.1: Precedence Ladder & Conflict Resolution Mechanics

The 7-tier precedence ladder defined in Section 6 of the specification is **RATIFIED** with the following structural rules:

1. **Cross-Layer Evaluation:** Higher-priority layers strictly supersede lower-priority layers regardless of file order or specificity.  
2. **Intra-Layer Evaluation:** Within a single rule layer (e.g., within User Presets or Project Rules), rules are evaluated in configured sequential order, and the **last matching rule wins**.  
3. **Separation of Inclusion and Grouping:** Group evaluation occurs **strictly after** the final inclusion decision is established. Group assignment never alters inclusion state.

### Ruling 3.2: Scope and Boundary of Session Overrides (Priority 1\)

- **Allowable Overrides:** A user may explicitly override a Priority 4 Environment Detector (e.g., forcing inclusion of `.venv312/Lib/site-packages/pytest/__init__.py`) or a Priority 5 Default Exclusion via UI checkbox or CLI `--force-include`.  
- **Absolute Safety Invariants (Priority 0):** The following conditions represent non-overridable Hard Safety blocks:  
  - Relative or absolute path traversal attempting to escape the configured project source base.  
  - Target paths pointing into the designated active bundle destination file (self-ingestion protection).  
  - Unresolvable, broken, or recursive circular symlinks.  
  - File paths containing illegal characters or unreadable filesystem permissions.  
- **Persistence Boundary:** Session overrides exist solely in transient memory during an active session and must never silently write back to governed baseline configuration (`bundle_config.json`).

### Ruling 3.3: User-Defined Groups & Transport Grammar Invariance

- **Manifest Sequencing:** Group assignments define the primary partitioning and emitted order of files within the bundle manifest: `[Group 1 files in normalized path order] -> [Group 2 files] -> ... -> [Ungrouped files]`.  
- **Zero Syntax Extensions in v2.2:** To preserve strict backward compatibility with existing downstream bundle unpackers and unbundlers (across `pyprojectmgr`, `EDSS/EDSM`, and external CLI pipelines), **no new group delimiter syntax or header fields will be written into the raw bundle stream**. Serialized transport grammar enhancements are deferred to v2.3 under a separate governance RFC.

---

## 4\. Foreseen Technical Risks, Edge Cases & Mitigation Strategies

As Lead Architect, I have identified six technical risks in the specification that require proactive defensive engineering before code lands in `main`:

\+-------------------------------------------------------------------------------------------------------+

|                              ARCHITECTURAL RISK & MITIGATION MATRIX                                   |

\+----+-----------------------------+------------------------------------+-------------------------------+

| ID | Technical Risk / Edge Case  | Potential Failure Mechanism        | Mandated Architectural Fix    |

\+----+-----------------------------+------------------------------------+-------------------------------+

| R1 | The "Ghost Children" Pruning| Pruning .venv312 skips walk, but   | Implement two-tier scan: early|

|    | & Manual Override Paradox   | user requests \--force-include on a | prune skips deep walk; on-    |

|    |                             | specific nested site-package file. | demand targeted subtree walk  |

|    |                             |                                    | if explicit child override set|

\+----+-----------------------------+------------------------------------+-------------------------------+

| R2 | Detector Signature Gaps &   | Virtualenvs without pyvenv.cfg     | Broaden detector signature    |

|    | Alternative Environments    | (e.g. legacy virtualenv, conda,    | matrix: pyvenv.cfg, conda-meta|

|    |                             | poetry symlinks, pipenv).          | bin/activate, Scripts/python. |

\+----+-----------------------------+------------------------------------+-------------------------------+

| R3 | Tkinter Worker Thread Race  | Fast checkbox clicks dispatch out- | Monotonic Generation Counters |

|    | Conditions & Stale Previews | of-order preview worker threads.   | (preview\_generation); cancel  |

|    |                             |                                    | obsolete worker generations.  |

\+----+-----------------------------+------------------------------------+-------------------------------+

| R4 | Treeview Memory Bloat on    | Instantiating 5,000+ Tk widget     | Windowed/virtualized rendering|

|    | Large Filesystem Trees      | nodes causes UI latency/freezes.   | backed by pure Python model;  |

|    |                             |                                    | render visible viewport only. |

\+----+-----------------------------+------------------------------------+-------------------------------+

| R5 | Untrusted Project Rule Files| Malicious .bft-selection.json in   | Enforce explicit opt-in only; |

|    | (.bft-selection.json)       | repo exfiltrates sensitive files.  | CLI requires \--rules flag; GUI|

|    |                             |                                    | shows active security banner. |

\+----+-----------------------------+------------------------------------+-------------------------------+

| R6 | Cross-Platform Path & Case  | Windows backslashes vs POSIX       | Canonical internal format:    |

|    | Normalization Discrepancies | forward slashes break glob chains. | strictly POSIX forward-slash, |

|    |                             |                                    | case-preserved, normalized.   |

\+----+-----------------------------+------------------------------------+-------------------------------+

### Risk R1: The "Ghost Children" Pruning & Manual Override Paradox

- **The Issue:** If the scanner detects `.venv312` and prunes it at the root directory level, `os.walk` never descends into `Lib/site-packages`. However, if the user specifies `--force-include .venv312/Lib/site-packages/pytest/__init__.py` or expands the `.venv312` folder in the UI tree, the system must handle children that were never initially enumerated.  
- **Architectural Solution:**  
  1. Pruned directories are recorded in `SelectionPlan.pruned_roots` as single meta-entries with status `Excluded (Directory Detector)`.  
  2. If an explicit child path override is registered, or if a user expands a pruned directory in the GUI, BFT triggers an **on-demand targeted subtree scan** for that specific directory, integrating the discovered nodes into the metadata index.

### Risk R2: Detector Signature Matrix & Polyglot Environments

- **The Issue:** Relying solely on `pyvenv.cfg` will miss:  
  - Conda environments (distinguished by `conda-meta/history` or `conda-meta/`).  
  - Standard Unix virtual environments created with certain tools where `bin/activate` exists but `pyvenv.cfg` is missing.  
  - Node.js environments (`node_modules/` with `.package-lock.json` or `package.json`).  
- **Architectural Solution:** In `core/detectors.py`, define composite structural signatures:  
    
  PYTHON\_ENV\_SIGNATURES \= \[  
    
      ("pyvenv.cfg",),                                      \# Standard venv / virtualenv  
    
      ("conda-meta",),                                      \# Conda environment root  
    
      ("Scripts", "python.exe"),                            \# Windows interpreter layout  
    
      ("bin", "activate"),                                  \# POSIX virtualenv layout  
    
  \]

### Risk R3: Tkinter Concurrency & Monotonic Generation Debouncing

- **The Issue:** Rapidly toggling multiple checkboxes within the 250ms debounce window can spawn multiple worker threads. If thread execution times vary, an earlier preview could finish *after* a later preview, corrupting the UI display.  
- **Architectural Solution:**  
  1. The UI maintains an atomic integer: `_current_generation: int = 0`.  
  2. On every user interaction, increment `_current_generation += 1`.  
  3. Pass `generation_id` to the background preview task.  
  4. Before applying preview updates in `root.after()`, assert:  
       
     if task\_generation \!= self.\_current\_generation:  
       
         return  \# Discard obsolete generation result

### Risk R4: Memory Virtualization for Large Datasets

- **The Issue:** In large codebases (e.g., 20,000+ files), creating individual `ttk.Treeview` items for every file consumes extensive GDI/Tkinter memory.  
- **Architectural Solution:** `bundle_frame.py` must hold the `SelectionPlan` in a lightweight Python dataclass list and populate only the top-level tree nodes (folders/groups), rendering leaf file nodes on-demand as folders are expanded.

---

## 5\. Work Package Sequencing & Engineering Roadmap

I endorse Paul’s proposed 6-stage work package breakdown and mandate the following staging progression:

                  ┌─────────────────────────────────────────────────┐

                  │ WP1: Selection Core Engine                      │

                  │ (core/selection.py, SelectionPlan, Rules, Tests)│

                  └────────────────────────┬────────────────────────┘

                                           │

                                           ▼

                  ┌─────────────────────────────────────────────────┐

                  │ WP2: Detectors & Directory Pruning              │

                  │ (core/detectors.py, Signature Matchers)         │

                  └────────────────────────┬────────────────────────┘

                                           │

                                           ▼

                  ┌─────────────────────────────────────────────────┐

                  │ WP3: Service Facade & CLI Adapter               │

                  │ (core/service.py, BundleToolService, cli.py)    │

                  └────────────────────────┬────────────────────────┘

                                           │

                                           ▼

                  ┌─────────────────────────────────────────────────┐

                  │ WP4: Selection Workspace Desktop UI             │

                  │ (ui/bundle\_frame.py, Tri-State Tree, Inspector) │

                  └────────────────────────┬────────────────────────┘

                                           │

                                           ▼

                  ┌─────────────────────────────────────────────────┐

                  │ WP5: Incremental Preview & Content Cache        │

                  │ (core/selection\_cache.py, Debounce, Generations)│

                  └────────────────────────┬────────────────────────┘

                                           │

                                           ▼

                  ┌─────────────────────────────────────────────────┐

                  │ WP6: Presets, Groups & Manifest Sequencing      │

                  │ (Local AppData, Project Export, Acceptance Test)│

                  └─────────────────────────────────────────────────┘

### Milestone Exit Criteria:

- **WP1 & WP2 Exit Gate:** Deterministic precedence tests pass across 100% of rule layers; `.venv312` is pruned before directory descent with zero content reads.  
- **WP3 Exit Gate:** `bundle-tool plan` displays identical decision trees to the service output; CLI stdout purity is 100% preserved; JSON reports validate against schema.  
- **WP4 & WP5 Exit Gate:** 4,000-path UI loads within \<150ms; single file toggle triggers 0 content reads for unchanged files; preview debounce executes under 250ms.  
- **WP6 Exit Gate:** Full end-to-end round-trip equivalence proven across developer and writer/marketer test fixtures.

---

## 6\. Action Items & Next Steps

1. **For John (Lead Developer):**  
   - Begin development of **WP1 (`core/selection.py`)** and **WP2 (`core/detectors.py`)**.  
   - Ensure `BundleToolService` in `core/service.py` exposes the exact method signatures specified in §13.1.  
   - Implement the monotonic generation counter pattern in the preview worker bridge.  
2. **For Paul (Lead Analyst):**  
   - Formalize the JSON schema definition for `.bft-selection.json` and user presets.  
   - Construct the reference test fixtures for both persona test suites:  
     - Application Dev Fixture: Multi-environment root (`.venv`, `.venv312`, `node_modules`, nested source).  
     - Writer/Marketer Fixture: Structured publication tree (`front-matter`, `chapters`, `research`, large video masters).  
3. **For Ringo (Product Owner):**  
   - Review and sign off on the UX interaction model (Tri-State Folder Tree, Rule Inspector, Selection Report).  
   - Confirm target release timeline for BFT v2.2 integration into the governed delivery kit.

---

*Signed,*  
**George**  
Lead Architect & Collaborative Developer  
`ARCH-RULING-2026-08-25-01`  
