# SPEC-VCS-001 v0.2.2 Git Provider Security and Privacy Profile

**Document reference:** `SPEC-VCS-001-GITSEC` — Version 0.2.2 Draft  
**Architecture:** `DRAFT_SPEC-VCS-001_v0.2.2_Repository_Support_Specification.md`  
**Data contract:** `DRAFT_SPEC-VCS-001_v0.2.2_Data_and_Policy_Contracts.md`  
**Date:** August 31, 2026  
**Status:** **Candidate Provider Profile — Adversarial Evidence Not Yet Accepted**  
**Normative terms:** `MUST`, `MUST NOT`, `SHOULD`, and `MAY` express proposed requirements pending ratification

---

## 1. Purpose and operating rule

This profile defines how `GitCliProvider` may invoke a local Git executable without turning repository inspection into an option-injection, helper-execution, privacy, resource-exhaustion, prompt, or accidental-network boundary.

The provider is read-only by contract. “Read-only” means it invokes no Git operation intended to modify repository, worktree, index, refs, configuration, credentials, remotes, submodules, or hooks. Filesystem races and Git implementation behavior remain residual risks and must be tested honestly.

Conformance requires both the architecture and this profile. A generic use of `shell=False` is necessary but not sufficient.

---

## 2. Threat and non-claim model

### 2.1 Threats in scope

- path or ref values beginning with `-`;
- revision/path ambiguity;
- hostile local or global Git configuration;
- external diff, text-conversion, pager, askpass, SSH askpass, credential, filesystem-monitor, or other helper execution;
- inherited environment manipulation;
- interactive prompts;
- accidental network-capable commands;
- executable substitution or unexpected Git version;
- malformed or oversized provider output;
- hung or recursively spawned processes;
- cancellation and process cleanup;
- invalid UTF-8 and unusual filenames;
- symlink, junction, reparse-point, case, and canonicalization boundary escape;
- remote credentials or repository identifiers in output/logs; and
- sensitive filename disclosure from client-data roots.

### 2.2 Claims explicitly not made

- immunity from a hostile local administrator controlling the executable, process, kernel, or filesystem;
- authenticity of repository contents or commit signatures;
- freshness relative to any remote;
- prevention of concurrent repository mutation by another process;
- complete support for every Git object format, extension, filter, filesystem, submodule, or platform configuration; or
- permission to inspect a root merely because Git recognizes it as a repository.

---

## 3. Executable resolution and qualification

### 3.1 Resolution

The API accepts either:

1. an explicitly configured absolute Git executable path; or
2. a discovery request that resolves `git` once through the provider's allowlisted `PATH`.

The provider MUST convert the result to a canonical absolute path before the first repository command and MUST reuse that exact path for the operation. It MUST NOT invoke a shell, batch wrapper, alias, function, or command string.

On Windows, executable discovery MUST reject an unexpected script/batch indirection for the qualified binary profile unless that wrapper is explicitly approved and tested. On POSIX, the resolved file MUST be a regular executable.

### 3.2 Qualification

Before repository commands, the provider executes the equivalent of:

```text
<git-executable> --version
```

The provider parses a bounded, single-line version response. A missing executable returns exit 11. A version below the accepted baseline or malformed executable identity returns exit 12. The sanitized version is included as `provider_version`.

Provider qualification evidence is recorded per operating-system/runtime profile. Passing on one platform does not qualify another.

---

## 4. Process construction

### 4.1 Required subprocess properties

- argument vector only;
- `shell=False`;
- stdin connected to the null device;
- stdout and stderr captured separately as bytes;
- no inherited console input;
- no terminal allocation;
- explicit working directory or `git -C <root>`; and
- a newly supervised process group/session suitable for cancellation and timeout cleanup.

On POSIX, the reference implementation SHOULD use `start_new_session=True`. On Windows, it SHOULD use a new process group and the strongest standard-library-compatible child cleanup available. Any inability to guarantee descendant cleanup is documented as residual risk and exercised.

### 4.2 Environment construction

The child environment is built from an empty dictionary. Only the following host variables MAY be copied when required by the platform profile:

```text
PATH
SYSTEMROOT
WINDIR
TEMP
TMP
TMPDIR
HOME
USERPROFILE
LANG
LC_ALL
```

Copied values do not authorize Git behavior. The provider injects or overrides:

```text
GIT_TERMINAL_PROMPT=0
GIT_OPTIONAL_LOCKS=0
GIT_PAGER=cat
PAGER=cat
GIT_ASKPASS=
SSH_ASKPASS=
GIT_EXTERNAL_DIFF=
GIT_CONFIG_NOSYSTEM=1
```

The provider also sets `GIT_CONFIG_GLOBAL` to the platform null device (`NUL` on Windows; `/dev/null` on POSIX), after confirming the selected Git accepts the platform representation.

All other `GIT_*`, `SSH_*`, credential, proxy, editor, pager, Python, and language-runtime injection variables are excluded unless this profile explicitly adds them. In particular, inherited `GIT_CONFIG_COUNT`, `GIT_CONFIG_KEY_*`, `GIT_CONFIG_VALUE_*`, `GIT_EXEC_PATH`, `GIT_SSH`, `GIT_SSH_COMMAND`, `GIT_EDITOR`, and `GIT_SEQUENCE_EDITOR` are prohibited.

### 4.3 Per-command configuration floor

Every repository command uses fixed Git configuration overrides equivalent to:

```text
-c core.fsmonitor=false
-c core.untrackedCache=false
-c diff.external=
-c pager.status=false
-c pager.diff=false
-c color.ui=false
-c core.quotepath=false
```

Diff commands additionally use `--no-ext-diff` and `--no-textconv`.

Local repository configuration remains readable only where required for core repository semantics, ignore rules, tracking refs, remotes, and submodule metadata. A local value MUST NOT enable a helper path for a selected command. The command matrix and adversarial tests are the authority for this assertion.

### 4.4 Locale and bytes

The provider prefers a stable UTF-8 locale when the platform supports one. It parses machine-oriented `-z` output as bytes and decodes path fields as strict UTF-8. It does not parse human-localized status text.

Git diagnostic stderr is never copied verbatim to a machine response. A known error is translated to a stable error code; unknown bounded stderr is retained only in a separately configured debug sink after redaction.

---

## 5. Root containment and repository discovery

### 5.1 Canonical root algorithm

Before Git execution:

1. Resolve the requested path strictly to a canonical existing directory.
2. Resolve every allowed and denied root strictly and normalize case according to the platform filesystem profile.
3. Reject the request if it is outside all allowed roots or inside/equal to a denied root.
4. Invoke repository discovery from the approved requested path.
5. Canonically resolve any discovered repository root.
6. Reject the result if the repository root is outside all allowed roots, inside/equal to a denied root, or crosses a symlink/junction/reparse-point boundary prohibited by host policy.
7. Retain both `requested_dir` and `root_dir` only in the local diagnostic result.

Containment is path-component-aware. String prefix comparison is prohibited.

### 5.2 CLI boundary

When the CLI receives no external allowlist, its allowed boundary is exactly the canonical `--path` directory. A repository root above that directory is not accepted. The caller must explicitly target the intended repository root.

### 5.3 Matrimonial/client-data boundary

EDSS/EDSM/EDV hosts MUST configure canonical denied roots for client vaults, case stores, evidence, exports, and working data. Name patterns such as `vault`, `*.case`, or `*.edsm` MAY trigger defense-in-depth rejection but are not authoritative because they are vulnerable to renaming, separator, case, symlink, and false-positive problems.

`list-files` access is considered sensitive metadata access even when file content is not read.

---

## 6. User-controlled refs and paths

### 6.1 Ref handling

User refs are never forwarded directly to a diff command. The accepted v1 ref language is deliberately smaller than Git's revision language:

```text
HEAD
full SHA-1 or SHA-256 object ID
refs/heads/<valid-ref-tail>
refs/tags/<valid-ref-tail>
unqualified branch-or-tag name that validates as a ref tail and resolves uniquely
```

Parent/ancestor operators, reflog selectors, revision ranges, peel expressions, colon expressions, path suffixes, and other arbitrary revision syntax are not caller inputs in v1.

The provider:

1. rejects NUL, control characters, leading/trailing whitespace, and values beginning with `-`;
2. applies a frozen maximum length;
3. validates full and constructed ref names with `check-ref-format` rules;
4. expands an unqualified name to `refs/heads/<name>` and `refs/tags/<name>`, rejects branch/tag ambiguity, and resolves only the unique full ref;
5. resolves the accepted full ref or full object ID with `rev-parse --verify <validated-value>^{commit}`;
6. validates the returned ID against the repository object format; and
7. passes only the validated full object ID to subsequent diff commands.

Ambiguous short object IDs are rejected. Revision expressions MAY be supported only if explicitly listed; v1 SHOULD restrict caller refs to names and full object IDs rather than arbitrary revision-language expressions.

### 6.2 Path handling

Provider-generated Git paths are repository-relative and never accepted as options. Commands accepting pathspecs use an explicit `--` separator and the global literal-pathspec mode where applicable.

The v1 public operations do not accept arbitrary pathspec arguments. Future path filters require a separate contract and negative-test set.

---

## 7. Approved command families

The implementation MAY combine compatible queries when the result and safety behavior remain identical. It MUST NOT introduce a Git subcommand outside this allowlist without contract review.

`<PFX>` below means the qualified executable, global `--literal-pathspecs`, fixed `-c` overrides, and canonical `-C <root>` arguments.

### 7.1 Repository discovery and identity

| Purpose | Approved command shape | Notes |
|---|---|---|
| Worktree check | `<PFX> rev-parse --is-inside-work-tree` | Machine boolean |
| Bare state | `<PFX> rev-parse --is-bare-repository` | Machine boolean |
| Worktree root | `<PFX> rev-parse --show-toplevel` | Invoked only for a worktree; discovered root revalidated |
| Absolute Git directory | `<PFX> rev-parse --absolute-git-dir` | Supports bare identity and worktree metadata; local diagnostic only |
| Shallow state | `<PFX> rev-parse --is-shallow-repository` | Unsupported command maps to capability/version result |
| HEAD object | `<PFX> rev-parse --verify HEAD^{commit}` | Fixed revision token only |
| Attached branch | `<PFX> symbolic-ref --quiet --short HEAD` | Exit semantics distinguish detached/unborn |
| Linked worktree metadata | `<PFX> rev-parse --git-dir --git-common-dir` | Returned paths stay local diagnostic only |

Object-format detection first uses `<PFX> rev-parse --show-object-format`. If the qualified baseline lacks that option, the provider uses the read-only query `<PFX> config --get extensions.objectFormat`; a missing value means `sha1`, `sha256` is accepted only when the capability profile supports it, and any other value is a typed unsupported repository state. Inferring format only from an untrusted caller value or object-ID length is prohibited.

### 7.2 Worktree and file inventory

| Purpose | Approved command shape | Notes |
|---|---|---|
| Two-dimensional changes | `<PFX> status --porcelain=v2 -z --find-renames=50% --untracked-files=all --ignored=no` | Parses ordinary, rename, unmerged, and submodule records; copy identity is not an index state |
| All tracked paths | `<PFX> ls-files -z --cached` | Reconciled with status output |
| Untracked paths | `<PFX> ls-files -z --others --exclude-standard` | Used only when selected |
| Ignored paths | `<PFX> ls-files -z --others --ignored --exclude-standard` | Used only when selected; file expansion required |

The provider reconciles records by normalized path and rejects malformed, duplicate-conflicting, or out-of-root records. It MUST NOT silently coerce an unknown porcelain status into `modified` or `none`.

### 7.3 Tags and upstream

| Purpose | Approved command shape | Notes |
|---|---|---|
| Exact tags | `<PFX> tag --points-at <validated-head-oid>` | Sort performed by tool |
| Nearest tag | `<PFX> describe --tags --long <validated-head-oid>` | No describable tag maps to null; Git selection semantics are documented observational behavior |
| Tracking ref | `<PFX> rev-parse --symbolic-full-name @{upstream}` | Fixed token; full local tracking ref; local only |
| Divergence | `<PFX> rev-list --left-right --count <head-oid>...<upstream-oid>` | Both endpoints validated full IDs |

Remote URL lookup is optional local-diagnostic behavior. The derived remote name must validate as a safe configuration key component. No remote subcommand may contact a network; URL values are read from local configuration and sanitized before output.

The read-only URL query is `<PFX> config --get remote.<validated-name>.url`. A missing key yields null; multiple or malformed values yield a warning and null unless the profile defines a deterministic selection rule.

### 7.4 Diff summary

| Endpoint pair | Numeric command | Name/status command |
|---|---|---|
| Ref → Ref | `<PFX> diff --no-ext-diff --no-textconv --find-renames=50% --find-copies=50% --numstat -z <base-oid> <target-oid> --` | Same endpoints/options with `--name-status -z` replacing `--numstat -z` |
| Ref → Index | `<PFX> diff --cached --no-ext-diff --no-textconv --find-renames=50% --find-copies=50% --numstat -z <base-oid> --` | Same endpoints/options with `--name-status -z` replacing `--numstat -z` |
| Ref → Worktree | `<PFX> diff --no-ext-diff --no-textconv --find-renames=50% --find-copies=50% --numstat -z <base-oid> --` | Same endpoints/options with `--name-status -z` replacing `--numstat -z` |
| Index → Worktree | `<PFX> diff --no-ext-diff --no-textconv --find-renames=50% --find-copies=50% --numstat -z --` | Same endpoints/options with `--name-status -z` replacing `--numstat -z` |

The name/status query MUST use the same endpoints and rename/copy thresholds as the numeric query. The provider reconciles both bounded NUL streams and returns `VCS_PROVIDER_MALFORMED_OUTPUT` on inconsistency. Binary `-` counts become JSON null; they are never coerced to zero.

### 7.5 Prohibited command families

The provider MUST NOT invoke:

```text
clone fetch pull push ls-remote
checkout switch reset restore clean
add commit merge rebase cherry-pick revert
tag (creation/deletion modes) branch (mutation modes)
stash worktree (mutation modes) submodule update
credential credential-cache credential-store
config (write modes) gc maintenance repack prune
archive bundle apply am
```

This list is defense in depth. The executable allowlist is the positive authority.

---

## 8. Time, output, cancellation, and process cleanup

### 8.1 Limits

Default limits:

| Limit | Default | Rule |
|---|---:|---|
| Per-process wall time | 10.0 seconds | Monotonic clock |
| Whole-operation wall time | 30.0 seconds | Includes all provider subprocesses |
| Per-stream bytes | 10 MiB | stdout and stderr independently |
| Whole-operation captured bytes | 20 MiB | Aggregate ceiling |
| Ref length | 1,024 bytes UTF-8 | Before Git execution |
| Warning/detail text | 4 KiB per field | Sanitized/truncated only in debug sink; machine errors use stable summaries |

Hosts MAY lower limits. Raising a sealed product limit requires an explicit deployment profile and evidence.

### 8.2 Bounded capture

The provider drains stdout and stderr concurrently in bounded chunks. It MUST stop retaining bytes and terminate the process group as soon as a limit is exceeded. Calling `communicate()` and checking length only after an unbounded child has exited does not satisfy the output limit.

### 8.3 Timeout

On timeout:

1. mark the result `VCS_TIMEOUT`;
2. terminate the supervised process group;
3. wait for a bounded grace interval;
4. force termination if still running;
5. drain/discard remaining bounded output; and
6. emit exactly one structured error.

### 8.4 Cancellation

The Python API accepts an optional cancellation token/event. The CLI translates Ctrl+C into the same cancellation path. Cancellation returns exit 42 and `VCS_CANCELLED`; it is not an internal error and does not emit a traceback.

If cancellation races with normal completion, the first terminal state recorded by the supervisor wins. Cleanup is idempotent.

### 8.5 Resource errors

Output overflow returns exit 41 and `VCS_OUTPUT_LIMIT`. It MUST NOT return exit 50. Memory allocation failure or an implementation exception remains exit 50 only after safe redaction.

---

## 9. Privacy projections and logging

### 9.1 Local diagnostic

May contain:

- canonical requested and repository paths;
- local branch/tag/worktree state; and
- a sanitized remote URL only when explicitly requested.

It MUST NOT contain embedded credentials, query strings, fragments, environment values, raw command lines, or unredacted Git stderr.

### 9.2 Portable provenance

Contains only the allowlisted fields in `vcs_portable_provenance_v1`. It contains no path, user, host, remote, organization, repository path, process ID, or timestamp.

Portable output is constructed directly from allowlisted fields. It is not implemented by serializing a local object and deleting known-sensitive keys, because future local fields could otherwise leak by omission error.

### 9.3 Machine logs

Default machine logs contain:

```text
stable event/error ID
operation
provider ID
result/exit class
duration bucket or bounded duration when policy permits
counts
correlation ID supplied by host
```

They exclude absolute paths, repository-relative filenames, refs, tags, remotes, organizations, repository names, usernames, hostnames, raw arguments, environment, and Git stderr by default.

A product-specific diagnostic profile MAY add repository-relative paths only after privacy review. Remote hosts and repository paths are not default machine-log fields.

### 9.4 Remote sanitization

When local diagnostic output requests a remote URL, the sanitizer MUST handle at least:

- `https://user:password@host/path?query#fragment`;
- `ssh://user@host/path`;
- SCP-like `user@host:path`;
- `file://` URLs;
- local absolute/relative paths; and
- malformed strings.

Credentials, usernames, query, fragment, and local paths are removed. A malformed value produces a warning and null, not a best-effort string containing unknown sensitive data.

---

## 10. Failure and redaction behavior

### 10.1 Error mapping

| Condition | Exit | Error code |
|---|---:|---|
| Unsafe/invalid ref before execution | 2 | `VCS_REF_UNSAFE` |
| Syntactically safe ref that does not resolve | 30 | `VCS_REF_NOT_FOUND` |
| Root outside boundary | 21 | `VCS_PRIVACY_BOUNDARY_VIOLATION` |
| Unsupported object/repository state | 31 | `VCS_REPOSITORY_STATE_UNSUPPORTED` |
| Malformed provider bytes | 20 | `VCS_PROVIDER_MALFORMED_OUTPUT` |
| Unsupported path encoding | 20 | `VCS_PATH_ENCODING_UNSUPPORTED` |
| Timeout | 40 | `VCS_TIMEOUT` |
| Output limit | 41 | `VCS_OUTPUT_LIMIT` |
| Cancellation | 42 | `VCS_CANCELLED` |

### 10.2 Redaction invariant

The machine error serializer receives structured fields, not raw exception `repr`, raw command strings, or raw provider stderr. Any debug sink is separate from stdout/stderr, opt-in, bounded, access-controlled by the host, and subject to the same secret/client-data exclusions.

---

## 11. Adversarial evidence requirements

Before `GitCliProvider` is `EVIDENCE_ACCEPTED`, tests must demonstrate:

- a leading-dash ref cannot become an option;
- revision expressions outside the accepted grammar are rejected;
- file paths containing spaces, tabs, newlines, leading dashes, Unicode, glob characters, and pathspec magic remain literal;
- global configuration is not loaded;
- local external diff, textconv, pager, fsmonitor, alias, credential, and helper attempts do not execute;
- askpass and terminal prompts cannot occur;
- no approved command opens a network connection in the fixture profile;
- a substituted or unsupported executable is rejected;
- timeout, output overflow, and cancellation terminate the supervised process tree;
- stdout/stderr remain schema-pure;
- malformed/partial NUL records produce typed failures;
- binary, rename, copy, conflict, submodule, and object-format states map correctly;
- canonical allow/deny containment survives case variation, symlinks, junctions/reparse points, and nested repositories;
- client/vault roots are rejected before file listing;
- local remote sanitization removes credentials and ambiguous values; and
- portable and machine-log serializers contain none of the prohibited fields.

The test harness SHOULD use a fake Git executable for helper/environment/process attacks and real fixture repositories for Git state semantics.

---

## 12. Ratification conditions

This profile becomes normative only when:

- George approves the trust and command boundary;
- John demonstrates the command matrix and supervised-process behavior on every claimed platform profile;
- Paul accepts the adversarial, privacy, and redaction evidence and residual risk;
- Ringo approves root/privacy/logging defaults for each host product; and
- the gate register records exact artifacts, implementation revision, test results, and hashes as `CONTRACT_FROZEN` or `EVIDENCE_ACCEPTED`, as applicable.

Until then, this document remains a candidate provider profile.

---

— **Version 0.2.2 Git Security and Privacy Draft for Team Review**
