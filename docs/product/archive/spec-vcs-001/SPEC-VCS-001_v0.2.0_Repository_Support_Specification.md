# SPEC-VCS-001 (v0.2.0): Pluggable VCS & Repository Support Tool

**Document ID:** SPEC-VCS-001  
**Version:** 0.2.0  
**Status:** SPECIFICATION FREEZE CANDIDATE / DRAFT RATIFICATION  
**Author:** George, Lead Architect (incorporating review by Paul, Lead Analyst)  
**Audience:** Ringo (Product Owner), Paul (Lead Analyst), John (Lead Developer)  
**Date:** 2026-08-31  
**Target Applications:** `pyprojectmgr`, `Bundle File Tool` (`BFT`), `PyThermX`, `NodeThermX`, `EDSS`/`EDSM`/`EDV`

---

## 1\. Executive Summary, Scope & Non-Goals

### 1.1 Objective

This specification defines the contract, architecture, and integration boundaries for **`vcs_tool`**—a standalone, dependency-free Python tool providing version control inspection, file listing, and preflight policy validation across the product family.

### 1.2 In-Scope Capabilities (v0.2.0)

1. **Repository Inspection (`inspect`):** Deterministic extraction of repository presence, branch/HEAD state, commit SHA, clean/dirty status, nearest/exact tags, and local upstream divergence without network calls.  
2. **File Listing (`list-files`):** NUL-safe enumeration of tracked, untracked, modified, staged, and ignored files with normalized relative paths.  
3. **Policy Validation (`validate`):** Fail-fast preflight gatekeeper evaluating repository state against caller-defined policies (`allow`, `warn`, `fail`).  
4. **Diff Summary (`diff-summary`):** Read-only observational line and file change counts between references or working tree.  
5. **Zero-Dependency Subprocess Provider:** A hardened, standard-library-only `GitCliProvider` supporting Python 3.11–3.13.

### 1.3 Explicit Non-Goals (Deferred)

* **No Direct File Archiving / Snapshots:** Archive and bundle generation remains the exclusive domain of `Bundle File Tool` (`BFT`). `vcs_tool` provides inventories, not archive creation.  
* **No Delta Patching / Applying:** Delta creation, application, and rollback engines are deferred to a dedicated BFT Delta Specification.  
* **No Sixth Integrity Pillar:** `pyprojectmgr` retains its ratified five-pillar Pentagon integrity model. Repository rules are integrated under governance policies.  
* **No Implicit Network Access:** The tool operates strictly on local repository state. Remote fetch/pull/push operations and network adapters are out of scope.

---

## 2\. Architecture, Packaging & Domain Boundary

\+-------------------------------------------------------------------------+

|                           Host Applications                             |

|    pyprojectmgr (QTC Gates/Meta)        |    Bundle File Tool (BFT)     |

\+-------------------------------------------------------------------------+

                     |                                   |

    (In-Process Typed API: VcsTool)             (CLI Subprocess: vcs-tool)

                     |                                   |

                     \+-----------------+-----------------+

                                       |

                                       v

\+-------------------------------------------------------------------------+

|                  vcs\_tool Package & Boundary Engine                     |

|          \- Typed Domain Models (Immutable Dataclasses)                  |

|          \- Canonical JSON Serializers & Error Formatters                |

|          \- Environment & Subprocess Security Isolation Guard            |

\+-------------------------------------------------------------------------+

                                       |

                                       v

\+-------------------------------------------------------------------------+

|                           Provider Registry                             |

|   \- GitCliProvider (Standard library subprocess; Default)               |

|   \- MockVcsProvider (Deterministic QA fixture provider)                 |

|   \- \[Future\] Pygit2Provider / HgCliProvider                             |

\+-------------------------------------------------------------------------+

### 2.1 Packaging & Entry Points

* **Package Structure:** Standalone Python package named `vcs_tool`.  
* **Execution Paths:**  
  1. Programmatic in-process: `from vcs_tool import VcsTool, VcsPolicy`  
  2. CLI Module invocation: `python -m tools.vcs_tool <command>` or `python -m vcs_tool <command>` (supported by `__main__.py`)  
  3. Standalone Console Script: `vcs-tool <command>`  
* **Runtime Dependencies:** Python standard library only (`subprocess`, `json`, `dataclasses`, `pathlib`, `re`).

tools/vcs\_tool/ (or src/vcs\_tool/)

├── \_\_init\_\_.py               \# Public API exports (VcsTool, domain models)

├── \_\_main\_\_.py               \# CLI entry point for \-m execution

├── api.py                    \# VcsTool host boundary class

├── cli.py                    \# CLI argument parsing, exit codes & stream handler

├── models.py                 \# Immutable dataclass domain models

├── serializers.py            \# Canonical JSON schema-compliant serializers

├── errors.py                 \# Structured VcsError hierarchy

├── security.py               \# Argument validation, path normalizer & env sanitization

├── providers/

│   ├── \_\_init\_\_.py

│   ├── base.py               \# IVcsProvider Abstract Base Class

│   ├── git\_cli.py            \# Hardened Git subprocess implementation

│   └── mock\_provider.py      \# Deterministic testing mock

└── schemas/

    ├── vcs\_status\_v1.json    \# JSON schema for inspect

    ├── vcs\_files\_v1.json     \# JSON schema for list-files

    ├── vcs\_validate\_v1.json  \# JSON schema for validate

    └── vcs\_error\_v1.json     \# JSON schema for structured failures

---

## 3\. Operation Specifications & Schemas

### 3.1 `inspect` (Repository State Observation)

Inspects the target path and returns repository metadata. **Absence of a repository is a valid state (Exit Code 0\)**, reporting `is_repository: false`.

#### Python API

tool \= VcsTool(path=".")

status: VcsStatusResult \= tool.inspect()

#### CLI Invocation

vcs-tool inspect \[--path \<path\>\] \[--format json|text\]

#### JSON Output Schema (`vcs_status_v1.json`)

{

  "schema\_version": "1.0.0",

  "tool\_version": "0.2.0",

  "provider": "git\_cli",

  "is\_repository": true,

  "root\_dir": "C:/Projects/pyprojectmgr",

  "head": {

    "commit\_sha": "4a86e8fad16516a766cc3a21aa88310762391c45",

    "short\_sha": "4a86e8f",

    "branch": "main",

    "is\_detached": false,

    "is\_unborn": false

  },

  "tags": {

    "exact\_tag": "v1.7.0",

    "nearest\_tag": "v1.7.0",

    "distance": 0

  },

  "worktree": {

    "is\_clean": false,

    "staged\_count": 1,

    "unstaged\_count": 2,

    "untracked\_count": 0,

    "conflicted\_count": 0

  },

  "upstream": {

    "tracking\_ref": "origin/main",

    "ahead\_count": 1,

    "behind\_count": 0

  },

  "warnings": \[\]

}

*Non-repository payload (Exit 0):*

{

  "schema\_version": "1.0.0",

  "tool\_version": "0.2.0",

  "provider": "none",

  "is\_repository": false,

  "root\_dir": "C:/Projects/extracted\_bundle",

  "head": null,

  "tags": null,

  "worktree": null,

  "upstream": null,

  "warnings": \["Target directory is not inside a recognized repository."\]

}

---

### 3.2 `list-files` (Inventory Listing)

Enumerates files within the repository with explicit categorization. Essential for `Bundle File Tool` (`BFT`) ingestion.

#### Python API

files: VcsFileListResult \= tool.list\_files(

    include\_tracked=True,

    include\_untracked=False,

    include\_ignored=False

)

#### CLI Invocation

vcs-tool list-files \[--path \<path\>\] \[--tracked\] \[--untracked\] \[--ignored\] \[--staged\] \[--format json|nul|text\]

#### JSON Output Schema (`vcs_files_v1.json`)

{

  "schema\_version": "1.0.0",

  "tool\_version": "0.2.0",

  "total\_count": 3,

  "files": \[

    {

      "path": "src/core/manifest.py",

      "status": "modified",

      "is\_tracked": true,

      "is\_staged": false

    },

    {

      "path": "src/core/new\_feature.py",

      "status": "added",

      "is\_tracked": true,

      "is\_staged": true

    },

    {

      "path": "scratchpad.tmp",

      "status": "ignored",

      "is\_tracked": false,

      "is\_staged": false

    }

  \]

}

*Note:* In `--format nul` mode, outputs NUL-delimited (`\0`) normalized paths for safe piping to tools and shell utilities.

---

### 3.3 `validate` (Preflight Policy Gate)

Evaluates local repository state against explicit caller policies. Returns exit `0` on compliance; returns specific exit classes and structured error payloads on violation.

#### Validation Parameters / Policy Model

* `require_repository: bool` (default: `true`)  
* `require_clean: bool` (default: `false` for dev, `true` for release)  
* `allowed_branches: list[str]` (optional, e.g. `["main", "master", "release/*"]`)  
* `disallow_detached: bool` (default: `false`)  
* `require_tag: bool` (default: `false`)  
* `require_synced: bool` (optional: `ahead==0 and behind==0`)

#### CLI Invocation

vcs-tool validate \--require-clean \--branch main \--format json

#### Multi-Violation JSON Error Output (on failure, written to stderr):

{

  "schema\_version": "1.0.0",

  "tool\_version": "0.2.0",

  "valid": false,

  "violation\_count": 2,

  "violations": \[

    {

      "code": "VCS\_GATE\_DIRTY\_TREE",

      "message": "Working directory contains 2 uncommitted modifications.",

      "details": { "staged": 0, "unstaged": 2, "untracked": 0 }

    },

    {

      "code": "VCS\_GATE\_BRANCH\_MISMATCH",

      "message": "Active branch 'feature/vcs-tool' is not in allowed list: \['main'\].",

      "details": { "active\_branch": "feature/vcs-tool", "allowed\_branches": \["main"\] }

    }

  \]

}

---

### 3.4 `diff-summary` (Observational Metrics)

Provides high-level line and file modification summaries between references (read-only metric reporting).

#### CLI Invocation

vcs-tool diff-summary \--from \<ref1\> \[--to \<ref2\>\] \[--format json|text\]

---

## 4\. Failure Taxonomy & Stream Contracts

### 4.1 Standardized Exit Code Table

| Exit Code | Constant | Meaning | Stream Behavior |
| :---- | :---- | :---- | :---- |
| **0** | `VCS_SUCCESS` | Command succeeded. (For `inspect`, includes non-repo). | JSON payload on `stdout`. |
| **1** | `VCS_POLICY_VIOLATION` | Policy validation failed (`validate` command). | Violation JSON on `stderr`. |
| **2** | `VCS_USAGE_ERROR` | Invalid CLI flags or arguments. | Error text on `stderr`. |
| **10** | `VCS_NOT_A_REPO` | Explicit repo required, but target is not a repo. | Error JSON on `stderr`. |
| **11** | `VCS_BINARY_MISSING` | Required VCS binary (`git`) not found on system PATH. | Error JSON on `stderr`. |
| **30** | `VCS_REF_NOT_FOUND` | Specified git revision, tag, or branch does not exist. | Error JSON on `stderr`. |
| **40** | `VCS_TIMEOUT` | Git process exceeded execution timeout. | Error JSON on `stderr`. |
| **50** | `VCS_INTERNAL_ERROR` | Unhandled exception or unexpected failure. | Error JSON on `stderr`. |

### 4.2 Stream Separation Contract

* When `--format json` is requested:  
  * **`stdout`** is strictly reserved for valid schema-compliant success JSON.  
  * **`stderr`** is strictly reserved for structured failure JSON or critical runtime traces.  
  * Diagnostic messages, warnings, or human progress bars must **never** be written to `stdout`.

---

## 5\. Security, Isolation & Privacy Controls

2. **Subprocess Execution Hardening:**  
   * Invocations strictly use argument lists (`shell=False`).  
   * Explicit argument terminator (`--`) is used when passing file paths or refs to prevent option injection.  
3. **Interactive Prompt Suppression:**  
   * Subprocess executions inject `GIT_TERMINAL_PROMPT=0` and `GIT_OPTIONAL_LOCKS=0` to prevent hanging in headless pipelines or GUI apps.  
4. **Remote URL Credential Redaction:**  
   * Any remote URL containing embedded credentials (e.g., `https://user:secret@github.com/...`) is sanitized to `https://github.com/...` before serialization, logging, or manifest storage.  
5. **Environment Sanitization:**  
   * Subprocesses inherit only an explicit allowlist of environment variables (`PATH`, `SYSTEMROOT`, `TEMP`, `TMP`, `HOME`, `USERPROFILE`, `GIT_EXEC_PATH`, `SSH_AUTH_SOCK`).  
6. **Matrimonial / EDSM Privacy Boundary:**  
   * Portable build metadata, logs, and bundle headers must **never** record local absolute workstation paths, OS usernames, or user directories. Repository paths are always normalized to repository-relative POSIX paths.

---

## 6\. Host Application Integrations

### 6.1 `pyprojectmgr` Integration

* **Governance Binding:** Configured under `governance.repository_policy` in the project manifest:  
    
  governance:  
    
    repository\_policy:  
    
      enforce\_in\_preflight: true  
    
      require\_repository: false  
    
      require\_clean: true  
    
      allowed\_branches: \["main", "release/\*"\]  
    
* **QTC Preflight Gate:** The preflight validation engine invokes `vcs_tool.validate()` against the active policy.  
* **Manifest Provenance Stamping:** During packaging, `pyprojectmgr` injects sanitized provenance into build metadata:  
    
  provenance:  
    
    vcs\_provider: "git"  
    
    commit\_sha: "4a86e8fad16516a766cc3a21aa88310762391c45"  
    
    short\_sha: "4a86e8f"  
    
    branch: "main"  
    
    tag: "v1.7.0"  
    
    is\_clean: true  
    
* **Integrity Model Invariance:** The 5-pillar Pentagon integrity engine remains untouched.

### 6.2 `Bundle File Tool` (`BFT`) Integration

* **Layered Selection Engine:**  
  * Mode `filesystem` (Default): Standard BFT selection, ignoring repository status.  
  * Mode `tracked`: Queries `vcs_tool.list_files(include_tracked=True)`.  
  * Mode `repository-aware`: Uses full filesystem traversal but annotates and reconciles each item with tracked/untracked/ignored status.  
* **Preservation of Safety Rules:** BFT’s hard exclude patterns, secret scanners, and allow/deny overrides take strict precedence over Git tracking state.  
* **Bundle Header Provenance:** When enabled by caller, metadata is recorded in `BundleManifest.metadata` under a versioned namespace (`x_vcs_provenance`).

### 6.3 `EDSS` / `EDSM` / `EDV` Integration

* **Privacy Isolation:** Repository tooling remains completely isolated from case files and client vaults.  
* **Local State Inspection:** Provides build and packaging provenance for client distributions without exposing developer workstation details.

---

## 7\. Acceptance Gates & Test Matrix

To achieve conformance, `vcs_tool` must pass a comprehensive test suite across Python 3.11–3.13:

| Fixture / Test Case | Expected API Behavior | Expected CLI Behavior |
| :---- | :---- | :---- |
| **Non-Repository Tree** | `is_repository=False`, Exit 0 | Valid JSON payload on stdout, Exit 0 |
| **Clean Repository on Branch** | Accurate branch/SHA/clean state | Exit 0, matching JSON schema |
| **Dirty Tree (Staged & Unstaged)** | Accurate counts, `is_clean=False` | Exit 0 on inspect; Exit 1 on `validate --require-clean` |
| **Detached HEAD** | `is_detached=True`, SHA resolved | Accurate JSON representation |
| **Unborn Branch (New Repo)** | `is_unborn=True`, SHA=None | Handled gracefully without crash |
| **Missing Git Executable** | Throws `VcsBinaryMissingError` | Exit 11 with structured error JSON |
| **Unicode & Special Character Paths** | Paths accurately preserved | Valid NUL/JSON serialization |
| **Remote URL with Credentials** | Credentials stripped from model | Redacted URL on stdout/JSON |
| **Execution Timeout (\>10s)** | Throws `VcsTimeoutError` | Exit 40 with error JSON on stderr |

---

## 8\. Implementation Roadmap

* **Phase 0 — Contract & Schema Freeze (Current):**  
  * Freeze JSON schemas (`vcs_status_v1.json`, `vcs_files_v1.json`, etc.).  
  * Ratify `SPEC-VCS-001` v0.2.0.  
* **Phase 1 — Git Provider Spike:**  
  * Implement standalone `vcs_tool` package, `GitCliProvider`, and CLI test harness.  
  * Validate 100% test pass on Git edge cases and non-repository handling.  
* **Phase 2 — `pyprojectmgr` Governance Integration:**  
  * Implement `governance.repository_policy` in project manifest schema.  
  * Wire QTC preflight gate and build provenance metadata.  
* **Phase 3 — `BFT` Selection Integration:**  
  * Implement `repository-aware` selection source in BFT.  
  * Verify safety override precedence and bundle reconciliation.  
* **Phase 4 — Deferred Advanced Capabilities:**  
  * Formulate separate BFT Delta Specification.  
  * Evaluate `pygit2` and remote provider adapters.

