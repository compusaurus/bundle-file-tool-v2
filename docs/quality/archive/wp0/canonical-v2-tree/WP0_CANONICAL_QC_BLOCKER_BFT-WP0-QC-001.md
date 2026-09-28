# BFT WP0 — Canonical QC Blocker Record

**Tracking ID:** BFT-WP0-QC-001  
**Opened:** 2026-07-23  
**Formalized:** 2026-07-24  
**Owner:** Paul, Lead Analyst, for evidence and routing  
**Affected gate:** Gate 1 — Accept normalized candidate baseline  
**Status:** OPEN — clean canonical run or bounded waiver required

## 1. Expected result

Canonical pyprojectmgr strict QC must run against the exact BFT WP0 candidate and return the authoritative lifecycle-compliance, signature-drift, contract-adherence, and orphan-detection results.

The current CLI source identifies itself as version `3.8.0`. The installed distribution version used on July 23 was not captured and must be recorded on the next run.

## 2. Observed failure

Two attempts were made on 2026-07-23:

1. The live-candidate attempt entered governance auto-remediation, rewrote `src/database/schema_ids.py`, and then failed while writing Windows console output. The exact pre-attempt source was immediately restored and verified at SHA256 `b2db1b55cc0e12d9822805c75c0616b0f9df1712bebc0b881a4ed1a0ed82fe57`.
2. The attempt was repeated against a disposable mirror with UTF-8 forced. Artifact generation completed, but schema remediation did not stabilize and the command aborted before returning any of the four canonical rule results.

The live candidate was not subjected to another mutating QC attempt.

## 3. Evidence limitation

The earlier execution channel did not persist the full stdout/stderr transcript, exact executable path, installed-distribution version, or complete command line as a governed artifact. The repository's existing `.pyprojectmgr/logs/pyprojmgr.log` ends in April 2026 and does not contain the July 23 attempts.

This limitation is not concealed or reconstructed. The narrative observations, restoration hash, and disposable mirror remain available, but they do not satisfy John's request for the original full output.

On 2026-07-24, Paul attempted to launch the Python 3.11 runtime solely to reproduce the failure on a fresh disposable mirror. The current controlled execution environment denied launching the external interpreter, so no new canonical output was generated and the live candidate remained untouched.

## 4. Safe reproduction route

An authorized interactive developer should:

1. Create a fresh disposable copy of the exact BFT candidate, excluding `.git` and the project virtual environment.
2. Record the Python version, pyprojectmgr CLI/distribution version, exact command, working directory, environment overrides, exit code, full stdout, and full stderr.
3. Run the canonical command with the disposable copy supplied as the explicit project root.
4. Compare all generated changes after each remediation pass and determine why the schema export is non-idempotent.
5. Run against the live candidate only after the remediation path is proven stable and non-destructive on the mirror.

The CLI's documented external-project form is:

```text
pyprojmgr --project-root <disposable-BFT-root> qc --strict
```

The exact installed entry point must be confirmed before treating this as the captured production command.

## 5. Compensating evidence currently available

- 480 tests pass with zero failures.
- Coverage is 88.49% against an 85% requirement.
- All governed JSON parses.
- Active header-policy resolution passes.
- Source and callable preservation are reconciled.
- Required lifecycle paths are governed and not ignored.
- Package version, deny-list, ACL policy, manifest-ID hash, stager, and CLI version contracts have executable regression tests.
- Supplemental checks are explicitly mapped to canonical QC vocabulary but are not represented as canonical QC results.

## 6. Closure conditions

Close this blocker only through one of:

1. a clean canonical strict-QC run on the exact candidate, with complete governed run evidence; or
2. a waiver approved by Ringo or an explicitly delegated owner that states the precise waived QC scope, this tracking ID, compensating evidence, and a build-specific expiry.

No waiver is granted by this record.
