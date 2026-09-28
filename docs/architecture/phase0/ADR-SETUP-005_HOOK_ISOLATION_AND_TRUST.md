# ADR-SETUP-005: Application Hook Isolation and Trust

**Status:** Proposed  
**Date:** 2026-08-26  
**Decision owner:** George, Lead Architect  
**Implementation owner:** Paul, Lead Developer / Lead Analyst  
**Product acceptance:** Ringo  
**Consulted:** John, Lead Developer  
**Depends on:** ADR-SETUP-001, ADR-SETUP-002, ADR-SETUP-003

## Context

Schemas cannot express every application rule. BFT needs domain validation for settings such as match patterns and cross-field behavior; ThermX has construction and sanitizer rules; SplashX has profile, media, geometry, and precedence rules. The proposed contribution contract therefore permits application validators, migrators, postflight checks, and optional reload adapters.

Loading executable references from a descriptor is a security and reliability boundary. An arbitrary module path, command, script, or URL could execute untrusted code in a privileged governance process. A validator with side effects could also modify the project during preview, defeating staged approval.

## Decision

Application integration hooks are **governed, allowlisted, capability-limited interfaces**. Descriptor text alone cannot authorize execution.

### Trust establishment

1. The authenticated application manifest binds the contribution descriptor and approved hook package/artifacts by identity and digest.
2. The suite registry records which hook capabilities are approved for that application and contract version.
3. Hook references use a constrained import-reference format resolved only from the authenticated installed application package.
4. Shell commands, executable strings, scripts selected by relative traversal, and remote URLs are forbidden.
5. A hook digest/package change places the contribution in `upgrade_pending` until reapproved.

### Capability classes

| Hook | Permitted purpose | Side-effect policy |
|---|---|---|
| Validator | Return structured diagnostics for baseline/proposed documents | Pure; no writes, subprocesses, UI, network, or application launch |
| Migrator | Transform an input document to a declared target schema and return explicit changes | Pure transformation; persistence prohibited |
| Postflight | Verify committed installed state and return diagnostics | Read-only; repair prohibited |
| Reload adapter | Request safe application activation after commit | Explicitly authorized capability; bounded timeout; result distinct from commit |
| Location provider | Resolve an approved non-project document such as user state | Narrow API; resolved path revalidated by `pyprojectmgr`; no arbitrary browsing |

### Execution boundary

The initial implementation may use an in-process adapter only for built-in, cryptographically/governance-bound hooks that pass purity tests. Before third-party or separately installed application hooks are enabled, the team must ratify a constrained worker-process boundary with:

- minimal environment and working directory;
- bounded input/output serialization;
- timeout and resource limits;
- no inherited privileged handles;
- network disabled unless a separately approved capability requires it;
- controlled import path;
- captured/redacted diagnostics;
- process termination on contract violation.

The architecture must not promise that Python code can be perfectly sandboxed in-process.

## Hook protocol

### Input

Hooks receive immutable, already-parsed values and a bounded context containing only:

- application/project identity and versions;
- baseline and proposed documents permitted to the hook;
- schema/contract version;
- validation phase;
- redacted effective-source metadata;
- approved path handles when required.

They do not receive raw credentials, registry mutation objects, the transaction journal writer, or unrestricted `pyprojectmgr` internals.

### Output

Hooks return a serializable result containing:

- stable diagnostic codes;
- severity;
- document ID and JSON Pointer;
- human-readable message and remediation;
- for migrations, transformed document and explicit change list;
- for reload, activation status.

Exceptions, invalid output, timeouts, or protocol violations become blocker diagnostics. They never mean validation success.

## BFT initial policy

- BFT's validator must be a pure adapter over ratified BFT validation semantics.
- It must not call `ConfigManager.save()` or any user-state write method.
- Pattern validation must use the same matching semantics as runtime selection.
- BFT migration preview returns proposed JSON and an explicit diff; `pyprojectmgr` owns persistence.
- BFT postflight verifies the committed config and manifest digest without repairing either.
- BFT does not require a runtime reload adapter in the first release; changes may be declared restart/next-operation scoped.

## Alternatives considered

### Permit arbitrary commands declared in the descriptor

Rejected. It turns configuration metadata into a privileged command-execution surface and is not portable or auditable enough.

### Run every hook in the ConfigEditor process

Rejected. It couples UI stability and privileges to application code and permits preview side effects outside the transaction authority.

### Use only JSON Schema; prohibit hooks

Rejected. It cannot faithfully express all domain, migration, path, and postflight rules.

### Trust any import installed in the environment

Rejected. Environment presence is not governance authorization and is vulnerable to import-path substitution.

## Consequences

### Positive

- Application-specific correctness remains possible without giving descriptors arbitrary execution power.
- Preview stays non-mutating.
- Hook upgrades are visible governance events.
- A future worker boundary can strengthen isolation without changing ConfigEditor semantics.

### Costs and constraints

- Hooks require stable protocols and structured diagnostics.
- Purity tests and side-effect detection are required.
- Worker-process isolation adds packaging and debugging complexity.
- Some application checks may need redesign to separate validation from I/O or launch behavior.

## Required follow-up decisions

1. Define the exact import-reference and package/digest binding format.
2. Decide whether all hooks use a worker from release 1 or only non-built-in hooks.
3. Ratify resource/time limits and supported platforms.
4. Ratify whether any postflight capability may read outside the project root.
5. Define a diagnostic namespace allocation process to prevent code collisions.

## Compliance evidence required

- Arbitrary command/URL/path hook declarations are rejected.
- Import-path substitution and digest mismatch are rejected.
- Validator and migrator side-effect fixtures fail closed.
- Timeout, crash, malformed output, and excessive-output fixtures fail closed.
- Secrets and sensitive paths are redacted from hook diagnostics.
- Preview leaves all governed and user-state files byte-identical.
- BFT validation diagnostics map to the same field pointers and semantics as runtime validation.

## Approval record

- [ ] Approved as written
- [ ] Approved with conditions recorded below
- [ ] Returned for revision
- [ ] Rejected

**Conditions / rationale:**

> 

**George:** ____________________  **Date:** __________  
**Ringo acceptance:** ____________________  **Date:** __________
