# SPEC-VCS-001: Pluggable VCS & Repository Support Tool

**Author:** George, Lead Architect  
**Audience:** Ringo (Product Owner), Paul (Lead Analyst), John (Lead Developer)  
**Date:** 2026-08-30  
**Status:** DRAFT / BRAINSTORMING SPECIFICATION  
**Target Applications:** `pyprojectmgr`, `Bundle File Tool` (`BFT`), `PyThermX`, `NodeThermX`

---

## 1\. Executive Summary & Objective

As our software suite expands across modular Python project governance (`pyprojectmgr`), file distribution/archival (`BFT`), and runtime visualizers (`PyThermX`/`NodeThermX`), we require uniform repository awareness (Git and future VCS backends) without tightly coupling core application engines to specific VCS binaries or heavy third-party libraries.

This specification defines the architecture, wire contracts, and integration lifecycle for **`vcs_tool`**—a standalone, loadable tool providing version control inspection, preflight gate validation, provenance capture, and export capabilities.

### Key Goals

1. **Decoupled Architecture:** Core applications (`pyprojectmgr`, `BFT`) consume repository services strictly through a standardized JSON/API contract.  
2. **Graceful Degradation:** Applications function seamlessly in non-repository environments (e.g., bare file extracts, offline air-gapped runtimes).  
3. **Pluggable Backends:** Initial implementation defaults to system `git` via standard library `subprocess` (zero extra dependencies), with future support for in-process `pygit2`, Mercurial (`hg`), or remote API adapters (GitHub/GitLab).  
4. **Machine-Readable Governance:** All operations return deterministic JSON schemas and standardized exit codes suitable for automated build gates.

---

## 2\. Architectural Design: The Loadable Tool Pattern

\+-------------------------------------------------------------------------+

|                           Host Applications                             |

|       pyprojectmgr (Pillar/Gates)       |      Bundle File Tool (BFT)   |

\+-------------------------------------------------------------------------+

                                    |

            \+-----------------------+-----------------------+

            | (In-process Python)                           | (CLI Subprocess)

            v                                               v

\+-------------------------------------------------------------------------+

|                  vcs\_tool Programmatic & CLI Boundary                   |

|                        (Contract: JSON Schema)                          |

\+-------------------------------------------------------------------------+

                                    |

                                    v

\+-------------------------------------------------------------------------+

|                           Provider Registry                             |

|   \- GitCliProvider (Default standard library subprocess)                |

|   \- Pygit2Provider (Optional in-process C-bindings)                     |

|   \- HgCliProvider  (Optional Mercurial backend)                         |

|   \- MockVcsProvider (Deterministic QA/QC & unit testing)                |

\+-------------------------------------------------------------------------+

### Module Layout

tools/vcs\_tool/

├── \_\_init\_\_.py               \# Package root & programmatic entry point

├── api.py                    \# VcsTool class definition (Python in-process API)

├── cli.py                    \# Command-line entry point (sys.exit \+ stdout JSON)

├── contracts.py              \# Schema validators & exit code constants

├── errors.py                 \# Structured VcsError hierarchy

├── providers/

│   ├── \_\_init\_\_.py

│   ├── base.py               \# Abstract Base Class (IVcsProvider)

│   ├── git\_cli.py            \# Subprocess Git adapter (Standard Library)

│   ├── pygit2\_provider.py    \# libgit2 adapter (Optional extension)

│   └── mock\_provider.py      \# Test harness fixture provider

└── schemas/

    ├── vcs\_status\_v1.json    \# JSON Schema for status/inspection output

    └── vcs\_diff\_v1.json      \# JSON Schema for diff/delta output

---

## 3\. Core Capabilities & CLI/API Interface

The tool exposes four primary functional actions across both its CLI interface and Python API:

### 3.1 `inspect`

Extracts repository identity, branch metadata, commit hash, and dirty/clean status.

* **CLI Syntax:** `python -m tools.vcs_tool inspect [--path <dir>]`  
* **Programmatic API:** `VcsTool(path).inspect() -> VcsStatusPayload`  
* **JSON Output Schema (`vcs_status_v1.json`):**

{

  "schema\_version": "1.0",

  "vcs\_type": "git",

  "is\_repository": true,

  "root\_dir": "C:/Projects/pyprojectmgr",

  "branch": "main",

  "commit\_sha": "4a86e8fad16516a766cc3a21aa88310762391c45",

  "short\_sha": "4a86e8f",

  "nearest\_tag": "v1.7.0-RC1",

  "is\_dirty": false,

  "modified\_count": 0,

  "untracked\_count": 0,

  "remote\_url": "https://github.com/org/pyprojectmgr.git",

  "ahead": 0,

  "behind": 0

}

### 3.2 `validate`

Acts as an automated preflight gatekeeper. Evaluates the local repository against user-defined governance policies.

* **CLI Syntax:** `python -m tools.vcs_tool validate [--require-clean] [--require-tag] [--branch <name>]`  
* **Programmatic API:** `VcsTool(path).validate(require_clean=True, require_branch="main")`  
* **Behavior:** Returns `0` on success. On violation, outputs structured error JSON to `stderr` and exits with specific non-zero exit codes.

### 3.3 `diff-manifest`

Generates a structured list of file changes between the working directory and a reference commit/tag, or between two arbitrary references.

* **CLI Syntax:** `python -m tools.vcs_tool diff-manifest --from <ref1> [--to <ref2>]`  
* **Output Payload:**

{

  "schema\_version": "1.0",

  "from\_ref": "v1.6.0",

  "to\_ref": "HEAD",

  "total\_changed": 3,

  "files": \[

    { "path": "src/core/manifest.py", "change\_type": "modified", "lines\_added": 12, "lines\_deleted": 2 },

    { "path": "docs/spec.md", "change\_type": "added", "lines\_added": 85, "lines\_deleted": 0 },

    { "path": "legacy/old\_tool.py", "change\_type": "deleted", "lines\_added": 0, "lines\_deleted": 40 }

  \]

}

### 3.4 `snapshot`

Produces a clean export/archive of tracked files at a specific revision, respecting repository ignore rules without copying `.git` metadata.

* **CLI Syntax:** `python -m tools.vcs_tool snapshot --out <archive_path> [--ref <commit/tag>]`  
* **Output:** Creates a deterministic `.zip` or `.tar.gz` bundle.

---

## 4\. Integration into Host Applications

### 4.1 Integration with `pyprojectmgr`

1. **Manifest Provenance Stamping:**  
   * During build execution (`pyprojectmgr build`), the orchestrator queries `vcs_tool inspect`.  
   * Stamped manifest fields:  
       
     build\_provenance:  
       
       vcs\_backend: "git"  
       
       commit\_sha: "4a86e8fad16516a766cc3a21aa88310762391c45"  
       
       branch: "main"  
       
       clean\_build: true  
       
       nearest\_tag: "v1.7.0"

     
2. **Preflight Build Gates:**  
   * The `pyprojectmgr` preflight gate engine executes `vcs_tool validate --require-clean`.  
   * Fails fast if dirty uncommitted changes exist, preventing unrepeatable release builds.  
3. **Repository Pillar Module:**  
   * Introduce a `repository` pillar in the project manifest enabling teams to configure sync policies, default branch rules, and upstream sanity checks.

### 4.2 Integration with `Bundle File Tool` (`BFT`)

1. **Repository-Aware Source Ingestion:**  
   * `BFT` invokes `vcs_tool` to list tracked files, preventing accidental inclusion of `.git/`, `.gitignore`, build artifacts, and ignored scratchpads.  
2. **Incremental / Delta Bundling:**  
   * Using `vcs_tool diff-manifest --from <last_release_tag>`, `BFT` can assemble delta patch bundles containing only changed or added assets.  
3. **Header Attestation:**  
   * Embeds repository commit SHA and tag provenance directly into the encrypted/unencrypted BFT bundle header.

---

## 5\. Exit Codes & Failure Taxonomy

To ensure unambiguous error handling across batch scripts and parent processes, `vcs_tool` defines standard exit codes:

| Code | Constant | Meaning |
| :---- | :---- | :---- |
| **0** | `VCS_SUCCESS` | Operation completed successfully. |
| **10** | `VCS_NOT_A_REPO` | Directory is not inside a recognized repository. |
| **11** | `VCS_BINARY_MISSING` | Underlying VCS binary (`git`) not found on system PATH. |
| **20** | `VCS_GATE_DIRTY_TREE` | Validation failed: working directory contains uncommitted modifications. |
| **21** | `VCS_GATE_BRANCH_MISMATCH` | Validation failed: active branch does not match required policy. |
| **22** | `VCS_GATE_UNTAGGED_COMMIT` | Validation failed: current commit lacks required release tag. |
| **30** | `VCS_REF_NOT_FOUND` | Specified commit, branch, or tag does not exist. |
| **50** | `VCS_INTERNAL_ERROR` | Unhandled internal exception. |

---

## 6\. Security & Operational Boundaries

1. **Read-Only by Default:** The tool's primary role in builds and bundling is non-destructive inspection. Mutating operations (`tag`, `commit`, `push`) require explicit CLI flags and are separated from inspection paths.  
2. **Credential Isolation:** The tool never reads, prompts for, or caches raw passwords or SSH private keys. It delegates network transport strictly to existing user-configured SSH agents or Git Credential Managers.  
3. **Sanitized Subprocess Invocations:** All subprocess calls execute with strict argument lists (`shell=False`) and sanitized environment variables, preventing shell injection vulnerabilities.

---

## 7\. Next Steps & Implementation Milestones

* **Phase 1: Tool Harness & Base Contract**  
  * Define `IVcsProvider` abstract base class and JSON schema specs.  
  * Implement `GitCliProvider` using standard library `subprocess`.  
  * Deliver standalone CLI with unit tests and mock provider.  
* **Phase 2: `pyprojectmgr` Gate & Provenance Integration**  
  * Add VCS preflight gate check to `pyprojectmgr` validation suite.  
  * Wire build provenance metadata into manifest generation.  
* **Phase 3: `Bundle File Tool` (`BFT`) Integration**  
  * Integrate tracked-file filtering and bundle header provenance stamping.  
  * Test delta bundle creation between release tags.

