# Paul’s Analysis — BFT v2.1 Build 100 Team Reviews

## Executive conclusion

I agree with the team’s central conclusion:

**Approve `BFT-2.1-B100-TRI-UI-HEADLESS-CORE` as the Build 100 target, begin the non-contractual portions of Phase 0 immediately, and do not open Phase 1 until a normative Interface Control Document has been approved.**

John correctly identified that the feature specification is strong at the architectural and product-scope levels but incomplete where three independent interfaces must bind to a common service. The request DTOs, structured errors, file-result schema, CLI exit codes, and Web security controls are not implementation details; they are the actual parity contract.

George appropriately ratified John’s core findings, selected Flask, chose a separate dry-run planning endpoint, approved the loopback security direction, and restricted Web access to sensitive configuration branches.

The original implementation sequence remains valid. There is no reason to replace Section 12 with a new plan. The correct action is to add an ICD and strengthen the phase gates.

---

## 1. Decisions that are now resolved

### D1 — Web framework

**Resolved: Flask.**

This is the correct Build 100 decision. The application is a local Windows developer utility with synchronous filesystem operations. FastAPI would add packaging and validation dependencies without providing a material Build 100 benefit.

The framework decision should now be treated as frozen so that `requirements.txt`, `pyproject.toml`, the Web test client, the launcher, and delivery package can be finalized.

### D6 — Dry-run behavior

**Resolved: dry-run extraction uses the separate `plan_extract` service operation and `/api/unbundle/plan` endpoint.**

This cleanly separates:

- analysis and conflict resolution;
- user review and confirmation;
- actual filesystem mutation.

The extraction endpoint should not independently recalculate an unrelated plan. It should consume or verify the approved plan, as discussed under Web security below.

### D3 — Web security architecture

**Architectural direction resolved; Ringo should formally ratify it.**

The minimum Build 100 controls are:

- bind only to `127.0.0.1`;
- issue a cryptographically random token at server launch;
- require that token on every API request;
- validate `Host` and `Origin` for state-changing calls;
- enforce request-size limits before JSON or file-content parsing;
- prohibit Web clients from changing their own security authority;
- require a confirmed extraction plan before writing files.

The original specification’s Web design exposed filesystem-writing endpoints without defining these controls, despite making safety-by-default a central product principle.

### D7 — Configuration write authority

**Architectural direction resolved; exact field matrix remains to be documented.**

The Web UI must not be able to modify:

- `web.host`;
- `web.enable_write_operations`;
- token or session-security settings;
- `safety.allow_globs`;
- `safety.deny_globs`;
- filesystem roots or other fields that could enlarge its authority.

A configuration write-authority matrix should identify each setting as writable by CLI, Tkinter, Web, installer, or none at runtime.

---

## 2. Recommended Ringo decisions

### D4 — Default Web write authority

**Recommendation: approve `enable_write_operations: false` as the persistent default.**

Web write access should require explicit enablement for the current server session. It should not be enabled merely by changing a value from the Web Settings page.

The preferred Build 100 mechanism is:

```text
python src\cli.py web --enable-write
```

or an equivalent trusted local launcher control.

The server can then mint a session token containing a read/write capability. The setting should revert to read-only when the server exits. This preserves complete Web functionality while ensuring that starting the Web UI does not silently expose filesystem mutation.

### D5 — JSONL profile

**Recommendation: approve implementation and retention of JSONL.**

JSONL is already represented in configuration, documentation, profile expectations, and canonical-sample planning. Removing it would create a visible regression and another configuration migration problem.

The ICD must nevertheless define:

- `mode` values for text and binary records;
- base64 representation;
- encoding rules;
- exact EOL preservation behavior;
- checksum algorithm and checksum input bytes;
- malformed-line handling;
- duplicate-path behavior;
- required versus optional fields;
- whether unknown fields are preserved or rejected.

A malformed record should fail validation with a stable error code rather than being silently skipped.

### D8 — Governance entries

**Recommendation: approve the governance objective, but not an unverified count or an outdated storage mechanism.**

John’s need for pre-implementation governance records is correct. However, his statement that the directive requires an `assets.db` relationships table and `pyprojmgr qc` appears inconsistent with the current BFT architecture addendum, which explicitly replaced external-database relationship tracking with a concise UI↔API mapping table in the specification. The current team directive also requires Code Catalog Tool and Code Catalog Comparison Tool evidence, but does not establish `assets.db` as the BFT relationship authority.

Therefore:

1. Do not ratify “approximately 58 entities” as a fixed count.
2. Generate the authoritative entity list from the completed ICD.
3. Put source assets and public code elements into the applicable code catalog.
4. Put DOM-to-endpoint-to-service relationships into a normative relationship table.
5. Validate both through automated orphan and drift tests.
6. Use the Code Catalog Comparison report as delivery evidence.

The count is provisional until the DTOs, DOM IDs, errors, and endpoints are frozen.

---

## 3. Refinement to the Phase 0/ICD sequence

John and George say Phase 0 can begin while the ICD is drafted. That is correct, but Phase 0 should be split logically.

### Phase 0A — Begin immediately

These tasks do not depend on the final interface contract:

- create the Build 100 branch and record its baseline commit;
- add `VERSION.txt`;
- implement `core/version.py`;
- normalize source headers;
- inventory existing code-catalog state;
- identify every test dependent on the `writer.py` compatibility shims;
- capture the complete baseline pytest result;
- verify current CLI and Tkinter launch behavior;
- define rollback and branch merge criteria.

The `writer.py` shims should not simply be removed. The team first needs a dependency report distinguishing invalid tests from legitimate compatibility expectations.

### ICD — Draft and ratify in parallel

John should draft the contract; George should approve the architecture; Paul should QA the completeness and testability; Ringo should ratify product and security defaults.

### Phase 0B — Governance freeze

After the ICD is approved:

- finalize the proposed entity inventory;
- finalize all stable DOM IDs;
- finalize the UI↔endpoint↔service relationship table;
- add the accepted contracts to the code/governance catalogs;
- baseline the Code Catalog Comparison report;
- open Phase 1.

This avoids cataloging speculative entities and then immediately changing them.

---

## 4. Required ICD contents

The ICD should be normative rather than advisory. At minimum, it should include the following.

### 4.1 Request contracts

Define field-level schemas for:

- `DiscoverRequest`;
- `BundlePreviewRequest`;
- `CreateBundleRequest`;
- `ParseBundleRequest`;
- `ValidateBundleRequest`;
- `PlanExtractRequest`;
- `ExtractBundleRequest`;
- `ConfigPatchRequest`;
- `ExportLogsRequest`.

Each field needs its type, default, allowed values, normalization rule, source authority, and validation error.

I recommend standard-library dataclasses plus explicit validation for Build 100. Adding Pydantic solely for these DTOs would work, but it would weaken the rationale for selecting Flask as the lighter dependency path.

### 4.2 Common result contracts

The generic service result should add:

- `schema_version`;
- `request_id`;
- `success`;
- `operation`;
- `profile`;
- `summary`;
- `warnings`;
- `errors`;
- `files`;
- `output_text`;
- `output_path`;
- `log_file`.

The `files` entries must use a named schema rather than `list[dict]`. Fields should include:

- `path`;
- `relative_path`;
- `size_bytes`;
- `mode`;
- `encoding`;
- `eol`;
- `checksum`;
- `selected`;
- `action`;
- `reason`;
- `destination_path`.

### 4.3 Error contract

Errors should be structured objects:

```json
{
  "code": "E_PATH_ESCAPE",
  "message": "The requested path resolves outside the output root.",
  "path": "../../bad.txt",
  "hint": "Use a relative path within the selected output directory."
}
```

The ICD should establish stable error codes and a CLI exit-code mapping. A practical top-level exit model would be:

| Exit | Meaning |
|---:|---|
| 0 | Success |
| 2 | Invalid command or request |
| 3 | Safety or validation block |
| 4 | Profile or parse failure |
| 5 | Configuration or filesystem failure |
| 6 | Unexpected internal failure |
| 130 | User cancellation |

Individual error codes remain more precise than exit statuses.

### 4.4 Plan-confirm-extract contract

For the Web UI, `plan_extract` should return:

- a `plan_id`;
- a digest of the normalized extraction request;
- planned file actions;
- conflicts and blocked paths;
- expiration time.

`extract_bundle` should require the valid `plan_id` and verify that the request, output root, selected files, overwrite policy, and security session still match. This prevents a reviewed plan from being replaced by a different write request.

### 4.5 Complete Web contract

The ICD must contain:

- all endpoints;
- all HTTP methods;
- request and response schemas;
- authentication-token transport;
- allowed origins and hosts;
- request and response size behavior;
- timeout rules;
- preview truncation behavior;
- stable DOM IDs;
- the global `showTab(tabName, buttonEl)` contract;
- UI element ↔ endpoint ↔ service-operation mapping.

### 4.6 Progress and cancellation

An indeterminate spinner alone does not require granular progress events, but long-running service operations still need:

- optional progress callback support for Tkinter;
- cooperative cancellation;
- defined timeout behavior for Web calls;
- cancellation results using stable codes rather than generic exceptions.

### 4.7 Version contract

`VERSION.txt` should be the authoritative installed version.

`core/version.py` should read that file and provide a packaged fallback only when the file is unavailable. Tests should compare the service version to `VERSION.txt`, not to a permanently hardcoded `2.1.100`.

This accommodates the intended post-install increment to `2.1.101`.

### 4.8 Clipboard boundary

Clipboard access belongs in the UI adapters.

The service should accept bundle text or a file path. Tkinter or the browser reads clipboard content and passes text to the service. This preserves the required dependency direction.

### 4.9 Concurrency policy

Build 100 does not require sophisticated multi-process locking, but it needs explicit behavior:

- configuration saves use atomic temporary-file replacement;
- concurrent writes are last-validated-write-wins;
- logs are session-specific rather than shared mutable files;
- extraction rejects destination conflicts discovered after planning;
- Tkinter and Web cannot silently overwrite the same output file without applying the selected overwrite policy.

---

## 5. Acceptance-test recommendation

John’s proposed increase from 15 tests to approximately 30–35 is reasonable, but coverage should be the controlling criterion rather than the number.

The expanded matrix should cover:

- every service method;
- every request DTO’s required-field and invalid-value behavior;
- every major structured-error family;
- all three profile round trips;
- malformed JSONL;
- encoding and EOL preservation;
- binary base64 round trip;
- file and request size limits;
- nested-bundle blocking;
- path traversal;
- overwrite modes;
- Web token rejection;
- invalid `Origin` and `Host`;
- read-only Web configuration enforcement;
- plan-confirm-extract integrity;
- preview truncation;
- CLI exit codes;
- log export;
- config save;
- GUI/Web concurrency policy;
- import-boundary enforcement;
- delivery-package contents;
- version increment behavior.

The import-boundary test should fail when `cli.py`, `ui/*`, or `web/*` imports parser, writer, profile, validator, or domain-model internals instead of the public service/DTO layer.

---

## 6. Issues correctly identified but not explicitly resolved by George

George’s response resolves the most important architectural decisions, but the following still belong in the ICD or Phase 0 evidence:

- canonical version resolution;
- complete and permanent DOM ID list;
- `files` result-entry schema;
- CLI exit-code table;
- progress and cancellation;
- preview-response limits;
- clipboard ownership;
- positive source-header format;
- `writer.py` shim dependency inventory;
- branch and rollback procedure;
- concurrent GUI/Web behavior;
- session-log isolation.

These should not be lost merely because they were classified as “non-blocking.” Most are non-blocking only in the sense that they can be resolved inside the ICD before Phase 1.

---

## 7. Final team recommendation

The project should proceed under the following approved posture:

1. **Approve the Build 100 Tri-UI/headless-core target.**
2. **Retain the existing seven-phase implementation sequence.**
3. **Begin Phase 0A immediately.**
4. **Authorize John to draft the ICD.**
5. **Use Flask.**
6. **Use a separate extraction-plan endpoint.**
7. **Make the local Web server token-protected, origin-validated, and loopback-only.**
8. **Default Web filesystem writes to disabled and enable them only for the current trusted launch session.**
9. **Implement JSONL after its exact semantics are frozen.**
10. **Replace the provisional “58 entities/assets.db” formulation with an ICD-derived code catalog and normative UI↔API relationship table.**
11. **Complete Phase 0B governance baselining after ICD approval.**
12. **Do not open Phase 1 until George signs the ICD and Paul confirms that each contract is objectively testable.**

John’s review materially improves the Build 100 specification rather than overturning it. George’s rulings close most architectural questions. The remaining work is now narrow and controllable: freeze the interface contracts, ratify the product-security defaults, and establish governance evidence before implementation begins.

---

The ratified ICD and revised specification should be circulated as PDF in accordance with the current team delivery directive.
