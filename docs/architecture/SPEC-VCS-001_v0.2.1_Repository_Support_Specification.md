# SPEC-VCS-001 (v0.2.1): Pluggable VCS & Repository Support Tool

**Document ID:** SPEC-VCS-001  
**Version:** 0.2.1  
**Status:** RATIFIED ARCHITECTURE SPECIFICATION / PHASE 0 CONTRACT FREEZE  
**Author:** George, Lead Architect (incorporating analyst review by Paul, Lead Analyst)  
**Audience:** Ringo (Product Owner), Paul (Lead Analyst), John (Lead Developer)  
**Date:** 2026-08-31  
**Target Applications:** `pyprojectmgr`, `Bundle File Tool` (`BFT`), `PyThermX`, `NodeThermX`, `EDSS`/`EDSM`/`EDV`

---

## 1\. Executive Summary, Scope & Non-Goals

### 1.1 Objective & Purpose

This specification establishes the normative contract, wire schemas, security boundaries, and host integration profiles for **`vcs_tool`**—a standalone, zero-external-dependency Python package providing version control inspection, file listing, and preflight policy validation across the product family.

### 1.2 In-Scope Capabilities (v0.2.1 Frozen)

1. **Repository State Inspection (`inspect`):** Deterministic extraction of repository presence, branch/HEAD state, commit SHA, clean/dirty state, exact/nearest tags, and local upstream divergence without network invocation.  
2. **Two-Dimensional File Listing (`list-files`):** NUL-safe enumeration of repository files modeling both index and worktree states independently (`index_status`, `worktree_status`, `conflict_status`, `original_path`).  
3. **Policy-Driven Validation Gate (`validate`):** Preflight gatekeeper evaluating repository compliance against caller-defined rule policies with per-rule dispositions (`allow`, `warn`, `fail`) and multi-violation aggregation.  
4. **Observational Diff Metrics (`diff-summary`):** Read-only line and file change counts between references or working tree.  
5. **Hardened Subprocess Engine (`GitCliProvider`):** Standard-library-only implementation supporting Python 3.11–3.13 and Git \>= 2.25.0.

### 1.3 Explicit Non-Goals (Deferred)

* **No Direct File Archiving / Snapshots:** File archiving remains the sole responsibility of `Bundle File Tool` (`BFT`). `vcs_tool` provides inventories, not archive creation.  
* **No Delta Patching / Applying:** Patch creation, apply engines, conflict resolution, and rollback are deferred to a dedicated BFT Delta Specification.  
* **No Sixth Integrity Pillar:** `pyprojectmgr` retains its ratified five-pillar Pentagon integrity model. Repository rules live under governance policy.  
* **No Implicit Network Access:** The tool operates strictly on local repository state. Remote fetch/pull/push operations and network adapters are out of scope.  
* **No BFT Artifact Provenance Headers:** BFT bundle-level serialization of provenance is deferred to a versioned BFT transport proposal.

---

## 2\. Architecture, Canonical Packaging & Execution Boundary

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

### 2.1 Canonical Package Layout

The package layout is locked exclusively to the `src/` layout:

src/vcs\_tool/

├── \_\_init\_\_.py               \# Public API exports (VcsTool, domain models, policy classes)

├── \_\_main\_\_.py               \# CLI entry point for \`python \-m vcs\_tool\`

├── api.py                    \# VcsTool host boundary class

├── cli.py                    \# CLI argument parsing, exit codes & stream handler

├── models.py                 \# Immutable dataclass domain models

├── serializers.py            \# Canonical JSON schema-compliant serializers

├── policy.py                 \# Rule-based validation policy engine

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

    ├── vcs\_diff\_summary\_v1.json \# JSON schema for diff-summary

    └── vcs\_error\_v1.json     \# JSON schema for structured failures

### 2.2 Execution & Packaging Specifications

* **Package Identity:** `vcs_tool` (Distribution name: `vcs-tool`).  
* **Supported Python Runtimes:** Python 3.11, 3.12, 3.13.  
* **Supported VCS Binaries:** Git \>= 2.25.0.  
* **Runtime Dependencies:** Standard Library only (`subprocess`, `json`, `dataclasses`, `pathlib`, `re`, `typing`, `enum`).  
* **Console Script:** `vcs-tool` mapped to `vcs_tool.cli:main`.  
* **Module Invocation:** `python -m vcs_tool <command> [options]`.

---

## 3\. Standard Result Envelope & Domain Models

All JSON responses share a standard metadata envelope:

{

  "schema\_id": "https://specs.equitable.dev/schemas/vcs/vcs\_status\_v1.json",

  "schema\_version": "1.0.0",

  "tool\_version": "0.2.1",

  "operation": "inspect",

  "provider\_id": "git\_cli",

  "provider\_version": "git version 2.43.0",

  "capabilities": {

    "inspect": true,

    "list\_files": true,

    "validate": true,

    "diff\_summary": true,

    "staging": true,

    "untracked\_detection": true,

    "ignored\_detection": true,

    "local\_tracking\_diff": true

  },

  "warnings": \[\]

}

---

## 4\. Normative Operation Contracts & JSON Schemas

### 4.1 `inspect` (Repository State Observation)

Inspects the target path and returns repository metadata. **Absence of a repository is a valid state (Exit Code 0\)**, reporting `is_repository: false` and `head: null`.

#### Python API

tool \= VcsTool(root\_path=".")

status: VcsStatusResult \= tool.inspect()

#### CLI Invocation

vcs-tool inspect \[--path \<dir\>\] \[--format json|text\]

#### Normative Schema: `vcs_status_v1.json`

{

  "$schema": "https://json-schema.org/draft/2020-12/schema",

  "$id": "https://specs.equitable.dev/schemas/vcs/vcs\_status\_v1.json",

  "title": "VcsStatusResult",

  "type": "object",

  "additionalProperties": false,

  "required": \[

    "schema\_id", "schema\_version", "tool\_version", "operation",

    "provider\_id", "provider\_version", "capabilities", "is\_repository",

    "root\_dir", "head", "tags", "worktree", "upstream", "warnings"

  \],

  "properties": {

    "schema\_id": { "type": "string" },

    "schema\_version": { "type": "string", "pattern": "^1\\\\.0\\\\.0$" },

    "tool\_version": { "type": "string" },

    "operation": { "type": "string", "const": "inspect" },

    "provider\_id": { "type": "string" },

    "provider\_version": { "type": "string" },

    "capabilities": { "type": "object", "additionalProperties": { "type": "boolean" } },

    "is\_repository": { "type": "boolean" },

    "root\_dir": { "type": "string" },

    "head": {

      "type": \["object", "null"\],

      "additionalProperties": false,

      "required": \["commit\_sha", "short\_sha", "branch", "is\_detached", "is\_unborn", "is\_shallow"\],

      "properties": {

        "commit\_sha": { "type": \["string", "null"\], "pattern": "^\[0-9a-f\]{40}$" },

        "short\_sha": { "type": \["string", "null"\], "pattern": "^\[0-9a-f\]{7,12}$" },

        "branch": { "type": \["string", "null"\] },

        "is\_detached": { "type": "boolean" },

        "is\_unborn": { "type": "boolean" },

        "is\_shallow": { "type": "boolean" }

      }

    },

    "tags": {

      "type": \["object", "null"\],

      "additionalProperties": false,

      "required": \["exact\_tags", "nearest\_tag", "distance"\],

      "properties": {

        "exact\_tags": { "type": "array", "items": { "type": "string" } },

        "nearest\_tag": { "type": \["string", "null"\] },

        "distance": { "type": \["integer", "null"\], "minimum": 0 }

      }

    },

    "worktree": {

      "type": \["object", "null"\],

      "additionalProperties": false,

      "required": \["is\_clean", "staged\_count", "unstaged\_count", "untracked\_count", "conflicted\_count"\],

      "properties": {

        "is\_clean": { "type": "boolean" },

        "staged\_count": { "type": "integer", "minimum": 0 },

        "unstaged\_count": { "type": "integer", "minimum": 0 },

        "untracked\_count": { "type": "integer", "minimum": 0 },

        "conflicted\_count": { "type": "integer", "minimum": 0 }

      }

    },

    "upstream": {

      "type": \["object", "null"\],

      "additionalProperties": false,

      "required": \["tracking\_ref", "ahead\_count", "behind\_count", "remote\_url"\],

      "properties": {

        "tracking\_ref": { "type": \["string", "null"\] },

        "ahead\_count": { "type": \["integer", "null"\], "minimum": 0 },

        "behind\_count": { "type": \["integer", "null"\], "minimum": 0 },

        "remote\_url": { "type": \["string", "null"\] }

      }

    },

    "warnings": {

      "type": "array",

      "items": {

        "type": "object",

        "additionalProperties": false,

        "required": \["code", "message"\],

        "properties": {

          "code": { "type": "string" },

          "message": { "type": "string" }

        }

      }

    }

  }

}

---

### 4.2 `list-files` (Two-Dimensional Inventory Listing)

Enumerates files modeling both index and worktree states independently. Essential for `Bundle File Tool` (`BFT`).

#### Python API

result: VcsFileListResult \= tool.list\_files(

    include\_tracked=True,

    include\_untracked=False,

    include\_ignored=False

)

#### CLI Invocation

vcs-tool list-files \[--path \<dir\>\] \[--tracked\] \[--untracked\] \[--ignored\] \[--format json|nul|text\]

#### Normative Schema: `vcs_files_v1.json`

{

  "$schema": "https://json-schema.org/draft/2020-12/schema",

  "$id": "https://specs.equitable.dev/schemas/vcs/vcs\_files\_v1.json",

  "title": "VcsFileListResult",

  "type": "object",

  "additionalProperties": false,

  "required": \[

    "schema\_id", "schema\_version", "tool\_version", "operation",

    "provider\_id", "total\_count", "files", "warnings"

  \],

  "properties": {

    "schema\_id": { "type": "string" },

    "schema\_version": { "type": "string", "pattern": "^1\\\\.0\\\\.0$" },

    "tool\_version": { "type": "string" },

    "operation": { "type": "string", "const": "list\_files" },

    "provider\_id": { "type": "string" },

    "total\_count": { "type": "integer", "minimum": 0 },

    "files": {

      "type": "array",

      "items": {

        "type": "object",

        "additionalProperties": false,

        "required": \[

          "path", "original\_path", "index\_status", "worktree\_status",

          "conflict\_status", "is\_tracked", "is\_untracked", "is\_ignored"

        \],

        "properties": {

          "path": { "type": "string" },

          "original\_path": { "type": \["string", "null"\] },

          "index\_status": {

            "type": "string",

            "enum": \["unmodified", "added", "modified", "deleted", "renamed", "copied", "untracked", "ignored", "none"\]

          },

          "worktree\_status": {

            "type": "string",

            "enum": \["unmodified", "modified", "deleted", "untracked", "ignored", "none"\]

          },

          "conflict\_status": {

            "type": "string",

            "enum": \["none", "both\_modified", "added\_by\_us", "added\_by\_them", "deleted\_by\_us", "deleted\_by\_them"\]

          },

          "is\_tracked": { "type": "boolean" },

          "is\_untracked": { "type": "boolean" },

          "is\_ignored": { "type": "boolean" }

        }

      }

    },

    "warnings": { "type": "array", "items": { "$ref": "vcs\_status\_v1.json\#/properties/warnings/items" } }

  }

}

---

### 4.3 `validate` (Preflight Policy Gate)

Evaluates local repository state against explicit caller policies. Returns exit code `0` on compliance; returns exit code `1` and multi-violation JSON on violation.

#### Policy Model & Disposition Rules

Each rule in `VcsPolicy` carries an explicit severity disposition: `allow`, `warn`, or `fail`.

@dataclass(frozen=True)

class VcsRuleConfig:

    disposition: Literal\["allow", "warn", "fail"\] \= "fail"

    enabled: bool \= True

@dataclass(frozen=True)

class VcsPolicy:

    require\_repository: VcsRuleConfig \= field(default\_factory=VcsRuleConfig)

    require\_clean\_worktree: VcsRuleConfig \= field(default\_factory=lambda: VcsRuleConfig(disposition="allow"))

    allowed\_branches: tuple\[str, ...\] \= ("main", "master")

    branch\_policy: VcsRuleConfig \= field(default\_factory=lambda: VcsRuleConfig(disposition="allow"))

    disallow\_detached\_head: VcsRuleConfig \= field(default\_factory=lambda: VcsRuleConfig(disposition="allow"))

    require\_exact\_tag: VcsRuleConfig \= field(default\_factory=lambda: VcsRuleConfig(disposition="allow"))

    require\_tracking\_ref\_equal: VcsRuleConfig \= field(default\_factory=lambda: VcsRuleConfig(disposition="allow"))

#### Rule Dependency Validation

* If `is_repository=false` and `require_repository.disposition == "allow"`, all downstream repository rules (`require_clean_worktree`, `branch_policy`, etc.) automatically evaluate to `NOT_APPLICABLE` (no false violations).

#### Normative Schema: `vcs_validate_v1.json`

{

  "$schema": "https://json-schema.org/draft/2020-12/schema",

  "$id": "https://specs.equitable.dev/schemas/vcs/vcs\_validate\_v1.json",

  "title": "VcsValidationResult",

  "type": "object",

  "additionalProperties": false,

  "required": \[

    "schema\_id", "schema\_version", "tool\_version", "operation",

    "provider\_id", "passed", "violation\_count", "warning\_count",

    "findings", "warnings"

  \],

  "properties": {

    "schema\_id": { "type": "string" },

    "schema\_version": { "type": "string", "pattern": "^1\\\\.0\\\\.0$" },

    "tool\_version": { "type": "string" },

    "operation": { "type": "string", "const": "validate" },

    "provider\_id": { "type": "string" },

    "passed": { "type": "boolean" },

    "violation\_count": { "type": "integer", "minimum": 0 },

    "warning\_count": { "type": "integer", "minimum": 0 },

    "findings": {

      "type": "array",

      "items": {

        "type": "object",

        "additionalProperties": false,

        "required": \["rule\_id", "severity", "passed", "message", "details"\],

        "properties": {

          "rule\_id": {

            "type": "string",

            "enum": \[

              "VCS\_RULE\_REPOSITORY\_REQUIRED",

              "VCS\_RULE\_CLEAN\_WORKTREE",

              "VCS\_RULE\_ALLOWED\_BRANCH",

              "VCS\_RULE\_NO\_DETACHED\_HEAD",

              "VCS\_RULE\_EXACT\_TAG\_REQUIRED",

              "VCS\_RULE\_TRACKING\_REF\_EQUAL"

            \]

          },

          "severity": { "type": "string", "enum": \["fail", "warn", "info"\] },

          "passed": { "type": "boolean" },

          "message": { "type": "string" },

          "details": { "type": "object", "additionalProperties": true }

        }

      }

    },

    "warnings": { "type": "array", "items": { "$ref": "vcs\_status\_v1.json\#/properties/warnings/items" } }

  }

}

---

### 4.4 `diff-summary` (Observational Metrics)

Calculates line and file change counts between revisions or between HEAD and the working tree.

#### Normative Schema: `vcs_diff_summary_v1.json`

{

  "$schema": "https://json-schema.org/draft/2020-12/schema",

  "$id": "https://specs.equitable.dev/schemas/vcs/vcs\_diff\_summary\_v1.json",

  "title": "VcsDiffSummaryResult",

  "type": "object",

  "additionalProperties": false,

  "required": \[

    "schema\_id", "schema\_version", "tool\_version", "operation",

    "provider\_id", "base\_ref", "target\_ref", "files\_changed",

    "insertions", "deletions", "file\_summaries", "warnings"

  \],

  "properties": {

    "schema\_id": { "type": "string" },

    "schema\_version": { "type": "string", "pattern": "^1\\\\.0\\\\.0$" },

    "tool\_version": { "type": "string" },

    "operation": { "type": "string", "const": "diff\_summary" },

    "provider\_id": { "type": "string" },

    "base\_ref": { "type": "string" },

    "target\_ref": { "type": "string" },

    "files\_changed": { "type": "integer", "minimum": 0 },

    "insertions": { "type": "integer", "minimum": 0 },

    "deletions": { "type": "integer", "minimum": 0 },

    "file\_summaries": {

      "type": "array",

      "items": {

        "type": "object",

        "additionalProperties": false,

        "required": \["path", "change\_type", "insertions", "deletions", "is\_binary"\],

        "properties": {

          "path": { "type": "string" },

          "change\_type": { "type": "string", "enum": \["modified", "added", "deleted", "renamed", "copied", "type\_changed"\] },

          "insertions": { "type": "integer", "minimum": 0 },

          "deletions": { "type": "integer", "minimum": 0 },

          "is\_binary": { "type": "boolean" }

        }

      }

    },

    "warnings": { "type": "array", "items": { "$ref": "vcs\_status\_v1.json\#/properties/warnings/items" } }

  }

}

---

### 4.5 `vcs_error_v1.json` (Structured Error Envelope)

{

  "$schema": "https://json-schema.org/draft/2020-12/schema",

  "$id": "https://specs.equitable.dev/schemas/vcs/vcs\_error\_v1.json",

  "title": "VcsErrorResult",

  "type": "object",

  "additionalProperties": false,

  "required": \["schema\_id", "schema\_version", "tool\_version", "error\_code", "error\_class", "message", "details"\],

  "properties": {

    "schema\_id": { "type": "string" },

    "schema\_version": { "type": "string", "pattern": "^1\\\\.0\\\\.0$" },

    "tool\_version": { "type": "string" },

    "error\_code": { "type": "string" },

    "error\_class": { "type": "string", "enum": \["usage", "environment", "repository", "timeout", "internal"\] },

    "message": { "type": "string" },

    "details": { "type": "object", "additionalProperties": true }

  }

}

---

## 5\. Failure Taxonomy & Stream Purity Contract

### 5.1 Standard Exit Code Table

| Exit Code | Constant | Meaning | Stream Behavior |
| :---- | :---- | :---- | :---- |
| **0** | `VCS_SUCCESS` | Command completed successfully (including non-repo `inspect`). | Schema-compliant JSON on `stdout`. |
| **1** | `VCS_POLICY_VIOLATION` | Policy validation failed (`validate`). | Multi-violation JSON on `stderr`. |
| **2** | `VCS_USAGE_ERROR` | Invalid CLI syntax, arguments, or mutually exclusive flags. | Error JSON on `stderr`. |
| **10** | `VCS_NOT_A_REPO` | Explicit repository required by command, but target is not a repo. | Error JSON on `stderr`. |
| **11** | `VCS_BINARY_MISSING` | Required VCS binary (`git`) not found on system PATH. | Error JSON on `stderr`. |
| **30** | `VCS_REF_NOT_FOUND` | Commit, branch, or tag reference does not exist. | Error JSON on `stderr`. |
| **40** | `VCS_TIMEOUT` | Process execution timeout exceeded. | Error JSON on `stderr`. |
| **50** | `VCS_INTERNAL_ERROR` | Unhandled internal exception. | Error JSON on `stderr`. |

### 5.2 Stream Purity Mandate

* In `--format json` mode:  
  * **`stdout`** MUST receive exactly one schema-compliant JSON document on exit 0\.  
  * **`stderr`** MUST receive exactly one schema-compliant error JSON document on non-zero exit.  
  * Diagnostic logs, progress indicators, or Python tracebacks MUST NEVER be emitted on either stream in JSON mode.

---

## 6\. Security, Isolation & Privacy Projections

### 6.1 Subprocess Hardening Specifications

1. **Argument Vectors Only:** Subprocess calls strictly pass argument lists (`shell=False`).  
2. **Path Separator Isolation:** Calls handling paths explicitly append `--` before path arguments to prevent option injection.  
3. **Helper & Interactive Prompt Suppression:** Subprocesses inject:  
   * `GIT_TERMINAL_PROMPT=0`  
   * `GIT_OPTIONAL_LOCKS=0`  
   * `GIT_PAGER=cat`  
   * `GIT_ASKPASS=`  
   * `GIT_CONFIG_NOSYSTEM=1`  
4. **Environment Allowlist:** Inherits strictly: `PATH`, `SYSTEMROOT`, `TEMP`, `TMP`, `HOME`, `USERPROFILE`.  
5. **Execution Bounds:** Default timeout: 10.0 seconds; output buffer limit: 10 MB. Exceeding limits raises `VcsTimeoutError` (Exit 40\) or `VcsOutputLimitError` (Exit 50).

### 6.2 Privacy Projection Profiles

\+--------------------------------------------------------------------------+

|                       Projection Profile Matrix                          |

|                                                                          |

| Profile: LOCAL\_DIAGNOSTIC (Internal CLI / Debugging)                    |

|   \- Full local paths (root\_dir)                                          |

|   \- Sanitized remote URLs (embedded credentials stripped)               |

|                                                                          |

| Profile: PORTABLE\_PROVENANCE (Build Manifests / Release Evidence)        |

|   \- commit\_sha, short\_sha, branch, exact\_tag, is\_clean, timestamp        |

|   \- NO root\_dir, NO workstation paths, NO usernames, NO remote URLs     |

|                                                                          |

| Profile: MACHINE\_LOG (Structured Audit Traces)                           |

|   \- Normalized repository-relative paths only                            |

|   \- Redacted remote hostnames (e.g., github.com/org/repo)                |

\+--------------------------------------------------------------------------+

### 6.3 Matrimonial System Isolation (`EDSS`/`EDSM`/`EDV`)

* **Case Vault Root Rejection:** `vcs_tool` explicitly refuses to inspect or list directories matching known client case storage patterns (e.g., paths containing `/vault/`, `*.case`, `*.edsm`).  
* **Root Allowlisting:** Host callers must pass an explicitly validated project root. `vcs_tool` will never infer repository roots upward across client privacy boundaries.

---

## 7\. Host Product Integration Profiles

### 7.1 `pyprojectmgrV2` Integration

* **Manifest Policy Binding:**  
    
  governance:  
    
    repository\_policy:  
    
      enforce\_in\_preflight: true  
    
      require\_repository:  
    
        disposition: "allow"  
    
      require\_clean\_worktree:  
    
        disposition: "fail"  
    
      allowed\_branches: \["main", "release/\*"\]  
    
      branch\_policy:  
    
        disposition: "fail"  
    
* **Integrity Model Invariance:** The Pentagon integrity engine continues to compute cryptographic signatures strictly across the 5 ratified pillars. Repository governance is evaluated by preflight Quality Tracking & Control (QTC) gates as policy evidence.  
* **Manifest Provenance Stamping:** Injects `PORTABLE_PROVENANCE` profile data into build output manifests.

### 7.2 `Bundle File Tool` (`BFT`) Integration

* **Three-Tier Selection Engine:**  
  * Mode `filesystem` (Default): Standard BFT file selection, completely ignoring VCS status.  
  * Mode `tracked`: Intersects BFT selection with `vcs_tool.list_files(include_tracked=True)`.  
  * Mode `repository-aware`: Runs full filesystem traversal and annotates each candidate with VCS metadata (`index_status`, `worktree_status`).  
* **Safety Precedence:** BFT hard deny patterns and path exclusions take strict precedence over Git tracking state.  
* **Artifact Transport Scope:** In-memory manifest metadata only. Serialization of provenance into bundle files is deferred to a future BFT transport RFC.

---

## 8\. Frozen Conformance Test Matrix (Phase 0 Exit Gate)

| Test ID | Scenario | Expected API Result | Expected CLI Result |
| :---- | :---- | :---- | :---- |
| **TC-01** | Non-Repository Directory | `is_repository=False`, `head=None` | Exit 0, valid `vcs_status_v1.json` |
| **TC-02** | Clean Repository on Branch | `is_clean=True`, `branch="main"` | Exit 0, valid `vcs_status_v1.json` |
| **TC-03** | Dirty Worktree (Staged \+ Unstaged) | `staged_count=1`, `unstaged_count=2` | Exit 0 on `inspect`; Exit 1 on `validate` |
| **TC-04** | Detached HEAD State | `is_detached=True`, `commit_sha` valid | Exit 0, accurate JSON representation |
| **TC-05** | Unborn Branch (Empty Repo) | `is_unborn=True`, `commit_sha=None` | Exit 0, `head.commit_sha: null` |
| **TC-06** | Shallow Clone | `is_shallow=True` | Exit 0, `head.is_shallow: true` |
| **TC-07** | Multiple Exact Tags on HEAD | `exact_tags=["v1.7.0", "release-1.7.0"]` | Exit 0, lexicographically sorted array |
| **TC-08** | Nearest Tag with Distance | `nearest_tag="v1.6.0"`, `distance=4` | Exit 0, accurate tag distance |
| **TC-09** | Missing Git Executable | Throws `VcsBinaryMissingError` | Exit 11, valid `vcs_error_v1.json` |
| **TC-10** | Missing / Invalid Path | Throws `VcsUsageError` | Exit 2, valid `vcs_error_v1.json` |
| **TC-11** | Execution Timeout (\>10s) | Throws `VcsTimeoutError` | Exit 40, valid `vcs_error_v1.json` |
| **TC-12** | Remote URL with User/Password | `remote_url` stripped of credentials | Exit 0, sanitized URL on stdout |
| **TC-13** | NUL-Delimited File Listing | `list_files(format="nul")` | Exit 0, `\0`\-separated POSIX paths |
| **TC-14** | Unicode & Special Filenames | Paths correctly decoded | Exit 0, UTF-8 JSON / NUL streams |
| **TC-15** | Diff Summary Metrics | Accurate insertions/deletions counts | Exit 0, valid `vcs_diff_summary_v1.json` |
| **TC-16** | Validate Multi-Violation Failure | `passed=False`, `violations=[...]` | Exit 1, valid `vcs_validate_v1.json` |
| **TC-17** | Validate Non-Repo with `allow` | `passed=True`, `findings=[NOT_APPLICABLE]` | Exit 0, valid `vcs_validate_v1.json` |
| **TC-18** | Privacy Rejection (EDSM Vault) | Throws `VcsPrivacyViolationError` | Exit 2, valid `vcs_error_v1.json` |
| **TC-19** | JSON Stdout/Stderr Purity | Zero non-JSON characters | 100% parseable by `jq` / `json.loads` |
| **TC-20** | Python API/CLI Byte Parity | Serializer matches CLI stdout | Byte-identical JSON output |

---

## 9\. Implementation Roadmap & Milestones

* **Phase 0 — Contract & Schema Freeze (COMPLETE):**  
  * `SPEC-VCS-001` v0.2.1 ratified.  
  * All 5 schemas frozen under `specs.equitable.dev/schemas/vcs/`.  
* **Phase 1 — Git Provider Spike (Target: John):**  
  * Implement `src/vcs_tool/` and `GitCliProvider`.  
  * Pass all 20 conformance test cases in `tests/test_vcs_tool/`.  
* **Phase 2 — `pyprojectmgr` QTC Integration (Target: George, John):**  
  * Integrate `governance.repository_policy` in preflight gates.  
  * Inject `PORTABLE_PROVENANCE` into build manifests.  
* **Phase 3 — `Bundle File Tool` Selection Integration (Target: Paul, John):**  
  * Implement `repository-aware` and `tracked` selection modes in BFT.  
  * Verify plan-to-artifact reconciliation and safety rule precedence.

