# Paul’s Analysis — Proposed Plain-Marker Self-Hosting Fix

**Project:** Bundle File Tool v2.1  
**Review date:** 2026-08-04  
**Prepared by:** Paul, Lead Analyst  
**For:** Ringo (Owner), George (Lead Architect), and John (Lead Developer)  
**Files reviewed:**

- `Proposed_plain_marker.py`
- `Proposed_test_selfhosting_roundtrip.py`
- Build 102 source and test bundles
- Bundle File Tool v2.1 master specification
- BFT v2.1 Build 100 Tri-UI Feature and System Specification
- Team Directives v5

## 1. Executive conclusion

John has correctly identified a genuine and important defect in the legacy Plain Marker format: an in-band `# FILE:` marker embedded in a source file can be byte-identical to a real bundle boundary. The existing parser therefore cannot always distinguish transport structure from file content.

The proposed per-bundle nonce is a sound architectural direction. The focused regression tests are meaningful and prove that the Build 102 parser is defective in this area. The proposed code also resolves the seven supplied test scenarios.

**Recommended disposition: CONDITIONAL APPROVAL — REVISION REQUIRED BEFORE MERGE.**

The concept should be approved, but the exact implementation should not be merged as submitted. The proposal introduces or leaves unresolved several P0 issues:

1. A nonce-looking line belonging to a file can still be deleted.
2. A legacy bundle containing a nonce-looking content line can be misclassified and rejected.
3. A damaged nonce header can silently omit a file instead of failing loudly.
4. The changed separator syntax is not cleanly readable by the previous Plain Marker parser.
5. The application-level nested-bundle guard can still reject legitimate self-hosting source files containing multiple `# FILE:` examples.
6. Random nonce generation makes identical inputs produce different bundle text, conflicting with the target requirement for a deterministic bundle artifact unless the team explicitly changes that requirement.

The correct outcome is to retain the nonce concept, revise its placement and parser state model, update the bundle-integrity policy, expand the tests, and then run the complete Build 102 regression and governance gates.

## 2. What John’s proposal changes

Compared with the Build 102 `plain_marker.py`, the proposed file:

- Adds the `secrets` import.
- Adds three nonce constants:
  - `NONCE_BYTES`
  - `NONCE_SEPARATOR_PREFIX`
  - `NONCE_SEPARATOR_PATTERN`
- Adds three private methods:
  - `_mint_nonce()`
  - `_nonce_separator()`
  - `_nonce_boundaries()`
- Changes `format_manifest()` to generate a random per-bundle nonce and place it in each separator.
- Changes `parse_stream()` so only a `# FILE:` line licensed by the bundle’s nonce separator can open a block in nonce-stamped bundles.
- Preserves legacy parsing when no nonce separator is detected.
- Stops discarding ordinary `# =====` banner lines in nonce mode.

No existing public method was removed. The public `PlainMarkerProfile` interface remains stable.

## 3. QA and evidence

### 3.1 Syntax checks

Both proposed Python files compiled successfully.

### 3.2 Focused regression tests

The supplied `test_selfhosting_roundtrip.py` was run against both implementations.

| Implementation | Result |
|---|---:|
| Build 102 baseline `plain_marker.py` | **6 failed, 1 passed** |
| Proposed `plain_marker.py` | **7 passed** |

The baseline failures correctly demonstrate:

- Phantom entries created from embedded markers.
- Truncation of embedded bundle text.
- Loss of repository banner lines.
- Consumption of a content `# META:` line.
- Incorrect entry counts in multi-file self-hosting cases.
- Absence of the proposed nonce stamp.

The one baseline pass is the legacy unstamped-bundle test, as expected.

### 3.3 Code catalog comparison

The team’s Code Catalog and Code Catalog Comparison tools were run against the Build 102 and proposed `plain_marker.py` files.

Structural result:

- Existing class methods: 11
- Proposed class methods: 14
- Added private methods: 3
- Existing public methods removed: 0
- Existing public method signatures changed: 0

The raw command-level stability figures were approximately:

- Function stability: `0.7333`
- Command stability: `0.7014`

Those numeric values are distorted by the catalog tool treating the changed class body as a large moved/changed AST region. The meaningful manual interpretation is that the proposal is localized to nonce constants, nonce helpers, parser boundary filtering, and formatter separators.

### 3.4 Additional focused probes

Additional probes found the following behavior:

| Probe | Observed result |
|---|---|
| Format the same manifest twice | Bundle text differed because a new random nonce was generated |
| Legacy bundle contains a valid-looking BFT nonce separator as file content | Parser raised `ProfileParseError: No files found` |
| Add one extra `=` to nonce separators | Regex recognized nonce mode, but exact separator comparison found no entries |
| Damage the first block’s closing nonce separator in a two-file bundle | First file silently vanished; second file parsed successfully |
| Read a new nonce bundle with the Build 102 parser | File parsed, but the closing nonce separator was inserted into file content |
| Put a foreign nonce-looking separator inside file content | The content line was deleted |
| Bundle a source entry containing two column-zero `# FILE:` examples | Existing `assert_bundle_clean()` rejected it as a nested bundle |

These findings establish that the central fix works for the supplied happy path but is not yet safe enough for production or self-hosting release use.

## 4. Strengths of the proposal

### 4.1 Correct root-cause analysis

John’s comment is correct: if a file contains an exact example of the bundle transport grammar, the legacy parser cannot distinguish that example from a genuine boundary using marker text alone.

This is not merely a weak regular expression. It is an information-design problem. A boundary requires additional context that is guaranteed not to occur in the payload.

### 4.2 Appropriate architectural pattern

A per-bundle boundary token is the standard class of solution used by multipart and framed transport formats. Generating the token after the content is known and verifying that it is absent from the content is a strong approach.

### 4.3 Good preservation of new-reader/old-bundle compatibility

The proposal keeps a legacy fallback when a bundle has no nonce. Therefore, the proposed reader can still parse old Plain Marker bundles.

This is an important zero-regression property.

### 4.4 Valuable regression tests

The new tests cover four previously unprotected content classes:

- Embedded `# FILE:` markers.
- Embedded `# META:` markers.
- Source header/banner separators.
- Multiple files containing embedded marker syntax.

They also verify that unstamped legacy bundles remain readable.

The tests should be retained and expanded rather than replaced.

## 5. P0 merge blockers

## 5.1 Foreign nonce-looking content is deleted

In nonce mode, `parse_stream()` currently discards every line matching `NONCE_SEPARATOR_PATTERN`, regardless of whether the line carries the active bundle nonce.

That means a legitimate file line such as:

```text
# === BFT:0123456789abcdef ==========================================
```

is removed even when the active bundle nonce is different.

This violates byte-for-byte round-trip fidelity.

**Required correction:** Discard only separators carrying the active bundle token and recognized as actual transport separators. A nonce-like line with another token must remain ordinary file content.

## 5.2 Legacy bundles can be falsely classified as nonce bundles

`_nonce_boundaries()` selects the first line anywhere in the input that matches the nonce-separator pattern.

A legacy bundle may legitimately contain that text inside one of its files. In that case:

- The parser switches to nonce mode.
- The actual legacy `# FILE:` headers are not licensed by the selected nonce.
- The parser may return no entries and raise a parse error.

This breaks legacy compatibility for a newly introduced content pattern.

**Required correction:** New-format detection must require a complete, valid top-level header near the beginning of the bundle, not merely a nonce-looking line anywhere in the input.

## 5.3 Malformed nonce structure can silently lose files

The current implementation precomputes allowed `# FILE:` line numbers. An apparent transport header that is not included in that set is treated as content.

A probe damaged the first block’s closing separator while leaving the second block valid. The parser returned only the second file without reporting that the first header was malformed.

Silent omission is unacceptable for a tool whose primary requirement is round-trip fidelity and safe reconstruction.

**Required correction:** Once a valid new-format bundle token is established, malformed uses of that active token or incomplete transport headers must raise `ProfileParseError`. The parser must fail loudly rather than return a partial manifest.

## 5.4 Changed separator syntax breaks clean old-reader/new-bundle compatibility

The new writer changes the old generic separator:

```text
# ===================================================================
```

to:

```text
# === BFT:<nonce> ==========================================
```

The Build 102 parser still recognizes `# FILE:` and therefore finds the file, but it does not recognize the nonce separator as a border. The closing nonce separator becomes part of the extracted file content.

The proposed comment says it preserves v1.1.5 compatibility. The implementation provides **new-reader/old-bundle compatibility**, but not **old-reader/new-bundle compatibility**.

The team must decide whether compatibility is intended to be one-way or two-way. The current master specification and “Legacy-Compatible” display name reasonably imply that this distinction must be explicit.

**Recommended correction:** Preserve the legacy separator line and place the nonce in metadata rather than in the separator.

Recommended format:

```text
# ===================================================================
# FILE: src/example.py
# META: encoding=utf-8; eol=LF; mode=text; boundary=<token>
# ===================================================================
<content>
```

Benefits:

- The old parser continues to ignore the old separator.
- The old parser ignores the unknown `boundary` metadata field.
- New readers can require the matching `boundary` token.
- Embedded legacy examples cannot accidentally match the current token because the token is chosen after content inspection.
- The visible Plain Marker format remains substantially unchanged.

A separate `# BFT-BOUNDARY:` header line before `# FILE:` is also feasible, but adding the token to `# META:` is simpler and preserves the current block structure.

## 5.5 Existing nested-bundle detection conflicts with true self-hosting

The current `bundle_integrity.py` classifies an entry as a nested bundle when its content contains two or more column-zero `# FILE:` lines.

That heuristic was designed to prevent accidental inclusion of historical full-source bundles. It also rejects legitimate source files, test fixtures, documentation, and parsers that intentionally contain multiple marker examples.

The supplied test uses one embedded `# FILE:` marker, so it does not exercise the existing threshold of two. A real self-hosting test suite can contain several examples and will still be blocked before `PlainMarkerProfile.format_manifest()` is called.

**Required correction:** Revise `bundle_integrity.py` together with this profile change.

Recommended policy:

1. Keep strong path-based rejection for known bundle/archive artifacts.
2. Remove marker-count-only classification.
3. Classify content as a nested bundle only when the content itself begins with and validates as a complete transport artifact, rather than merely containing marker lines.
4. Add an explicit override/allow mechanism for intentional bundle fixtures if needed.
5. Test the complete application path through discovery, manifest creation, integrity validation, formatting, parsing, and extraction.

Without this coordinated change, the profile can pass its direct unit tests while the product still cannot bundle its own complete test suite.

## 5.6 Random output conflicts with deterministic artifact requirements

`secrets.token_hex()` generates a new nonce on every call. Formatting the same manifest twice therefore produces different bundle text.

The Build 100 Tri-UI specification describes the product as creating a deterministic text artifact. Determinism is also useful for:

- Hash comparison.
- Release evidence.
- Reproducible builds.
- Diff review.
- CLI/GUI/Web parity testing.
- Avoiding unnecessary bundle changes when source content is unchanged.

**Recommended correction:** Derive the boundary token deterministically from a canonical, length-prefixed representation of manifest paths, metadata, and content.

Suggested approach:

1. Build a SHA-256 digest over canonical length-prefixed fields.
2. Use at least 128 bits of the digest for the boundary token.
3. If the token occurs in any payload, hash again with a deterministic counter.
4. Permit dependency injection of a token factory for tests.

If the team deliberately chooses random MIME-style boundaries, the specification must be amended to distinguish semantic determinism from byte-level determinism, and UI parity tests must not compare independently generated bundle strings byte-for-byte.

## 6. P1 issues and improvements

### 6.1 Regex and exact-match grammar disagree

`NONCE_SEPARATOR_PATTERN` accepts a variable number of trailing `=` characters. `_is_sep()` then requires exact equality with the canonical separator generated by `_nonce_separator()`.

A line can therefore pass format detection but fail boundary recognition.

**Recommendation:** Use one canonical grammar. Either:

- Require the exact canonical separator in the regex, or
- Compare the captured active token while allowing the padding accepted by the regex.

Do not recognize a format that the parser then cannot parse.

### 6.2 Parser should be a strict state machine in new mode

The new format should not rely primarily on a precomputed set of line numbers. A clearer parser state model is:

1. Detect and validate the first complete new-format header.
2. Lock the bundle token.
3. Parse each block as:
   - opening separator
   - `# FILE:`
   - required `# META:` with matching boundary token
   - closing separator
   - payload
4. Preserve all nonmatching marker-like lines as payload.
5. Raise on incomplete active-token transport sequences.
6. Fall back to the legacy heuristic only when no valid new-format first header exists.

This will be easier to reason about and test than licensing lines in a preprocessing pass.

### 6.3 Token size

Eight random bytes provide a 64-bit token. Because the token is checked against the payload, accidental in-bundle collision is already addressed. However, 128 bits is a better long-term default for cross-bundle uniqueness, copied fragments, and future tooling.

### 6.4 Avoid constructing one large content copy

`_mint_nonce()` concatenates every string payload into one large `blob`, which temporarily duplicates bundle content in memory.

Use per-entry membership checks instead:

```python
all(candidate not in entry.content for entry in manifest.entries if isinstance(entry.content, str))
```

For a deterministic digest design, stream length-prefixed fields into the hash instead of concatenating them.

### 6.5 Version and lifecycle metadata

The proposed source file remains `VERSION: 2.1.10`, although functionality changed. The test file uses `VERSION: 2.1.102`.

Before merge:

- Align both files with the canonical package/build version source.
- Avoid treating file headers as runtime version truth.
- Move lifecycle from `Proposed` to `Testing` only after the full gate passes.
- Retain approval/ratification claims only if the associated decision record exists.

### 6.6 Minor test cleanup

`pytest` is imported in the new test file but not used directly. This is harmless but can be removed.

## 7. Required test expansion

John’s seven tests should remain. Add the following before approval.

### New-format content preservation

1. A foreign nonce-looking separator inside file content is preserved.
2. Multiple different foreign nonce-looking separators are preserved.
3. Generic source banners remain exact.
4. Content `# FILE:` and `# META:` lines remain exact.
5. Binary content round-trips.
6. Empty text files round-trip.
7. CRLF metadata and content policy remain correct.

### Structural corruption

8. First opening header malformed: fail loudly.
9. Closing separator malformed: fail loudly.
10. One block uses a different active boundary token: fail loudly.
11. Missing `# META:` in new format: follow the explicitly ratified policy.
12. Duplicate or conflicting token declarations: fail loudly.
13. Truncated final block: fail loudly.
14. Valid earlier blocks are not returned as a partial success after later structural corruption.

### Compatibility

15. New reader parses canonical legacy bundles.
16. Legacy bundle containing nonce-looking content remains legacy and round-trips.
17. Decide and test old-reader/new-bundle behavior.
18. Test legacy bundles with and without `# META:`.
19. Test existing duplicate-path semantics.

### Determinism

20. Formatting the same manifest twice produces identical text, if deterministic output remains required.
21. Changing any path, metadata value, or content changes the derived token.
22. Deterministic collision-counter path is tested with an injected token/digest stub.

### Full self-hosting workflow

23. Bundle the actual `src` and `tests` trees through `BundleCreator`.
24. Run `assert_bundle_clean()`.
25. Format the manifest.
26. Parse it back.
27. Verify path set, entry count, content, encoding, and EOL policy.
28. Extract to a temporary directory and compare files according to the project’s canonical header-injection policy.
29. Confirm a real historical bundle/archive is still blocked.
30. Confirm Python tests/docs containing multiple marker examples are not blocked.

## 8. Recommended implementation sequence

### Step 1 — Ratify the transport grammar

George should ratify:

- Nonce location: recommended `boundary=<token>` in `# META:`.
- Deterministic versus random token.
- One-way versus two-way legacy compatibility.
- Strict failure behavior for malformed new-format bundles.

### Step 2 — Revise `plain_marker.py`

John should:

- Preserve legacy separator syntax.
- Introduce a canonical boundary metadata key.
- Use a strict new-format state machine.
- Preserve foreign token-like content.
- Fail loudly on active-token structural corruption.
- Retain legacy fallback.
- Avoid whole-bundle content concatenation.

### Step 3 — Revise `bundle_integrity.py`

Replace the two-marker heuristic with validated standalone-bundle detection while retaining strong archive/path controls.

### Step 4 — Expand tests

Add the P0/P1 and complete workflow cases listed above.

### Step 5 — Run governance gates

- Full pytest under the project’s supported Python 3.12 environment.
- Code Catalog and Code Catalog Comparison.
- Changelog CSV.
- Canonical sample bundle refresh.
- Round-trip comparison.
- Release contract tests.
- `PREP_AND_STAGE_BFT.bat /dryrun`.

## 9. Team conclusions

### To Ringo

The underlying feature should be approved. It solves a real defect that prevents dependable self-hosting and exact source transport. Approval should be for the **nonce-based boundary strategy**, not for the submitted separator implementation as-is.

### To George

The key architecture decision is where the token belongs. I recommend preserving old separators and adding a boundary field to `# META:`. This best satisfies round-trip fidelity, legacy readability, deterministic parsing, and minimal format disruption.

### To John

The new tests are useful and should remain. Please revise the implementation around the six P0 items, especially foreign-token content preservation, strict corruption failure, bundle-integrity integration, and determinism.

## 10. Final recommendation

**Approve the feature concept. Do not merge the two proposed files yet.**

Merge authorization should require:

1. Revised token placement or an explicit compatibility waiver.
2. No deletion of foreign nonce-like content.
3. No legacy false-positive nonce detection.
4. Fail-loud behavior for malformed new-format structure.
5. Coordinated `bundle_integrity.py` correction.
6. Deterministic output or a formally revised determinism requirement.
7. Full self-hosting integration test.
8. Full pytest and governance evidence.

Once those gates are met, this will be a strong and necessary improvement to the Plain Marker profile and to the Bundle File Tool’s core claim of safe, bidirectional, self-hosting round-trip fidelity.
