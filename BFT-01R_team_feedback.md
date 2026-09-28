# BFT-01R evidence correction feedback

**From:** Billie  
**To:** Paul, Ringo, John, George  
**Date:** 2026-09-14  
**Subject:** Evidence correction for BFT-01 submission

Paul’s review is directionally correct and should be treated as a scope correction for evidence quality, not as a rebuild or product-execution request.

## Summary

The submitted BFT-01 ZIP and its sidecar remain intact, and the specific packet integrity checks appear sound. The issue is not that the packet is empty or invalid; it is that the helper used to generate the original evidence wrote pass/fail rows and READY text as if they were observed outcomes, when they were partly derived or hardcoded. This is an evidence-quality defect, not a packaging or source-content defect.

The right follow-up is a fresh, bounded verifier under a new run directory, separate from the original results. It should preserve the original BFT-01 artifacts exactly as provided and add a small, explicit evidence package that logs actual execution details, file hashes, and the outcomes of valid and invalid archive fixtures.

## Assessment against Paul’s review

### 1) Original evidence generation was overstated

I agree with Paul’s concern that the original helper embeds PASS rows and READY declarations without preserving the full chain from actual observed outcomes. The manifest status itself was computed dynamically in part, but the acceptance CSV and completion note were too confident for the evidence trail that was actually captured.

Recommendation: keep the original BFT-01 artifact untouched and add a corrected evidence record under a new run such as BFT-01R that does not rerun the old helper.

### 2) ZIP verification should be explicit and exhaustive

The original ZIP routine checked member safety and extracted the archive, but it did not independently compare extracted file sizes and SHA-256 values against the manifest entries. That means the verification line was too weak to support a final claim about the packet beyond a limited safety check.

Recommendation: treat the archive validation as a two-step check: (a) validate the zip structure and member safety, and (b) compare each extracted payload item against its manifest size/hash and the expected member set. That is exactly what Paul’s follow-up request requires.

### 3) Source-hash provenance should be labeled correctly

The original builder asserts that the source hashes are unchanged, but it saves the payload-side hash summary as `source_after_hashes.json`. That is not a true “source post-read” record. It should instead be separated into original-before, original-after, payload hash, and extracted hash observations with explicit timestamps and labels.

Recommendation: keep the source hash check, but save its actual observations under separate names and explicit timezone stamps. This removes the ambiguity between a source observation and a copied-payload observation.

### 4) The command ledger should be actual execution evidence, not generated summaries

Paul is correct that the original ledger and command logs are generated summaries rather than captured executions of the named commands. They don’t include the exact Python runtime, start/end times, or true stdout/stderr capture for each external action.

Recommendation: the follow-up verifier should produce one truthful run log per command, including runtime version, arguments, working directory, timestamps, exit code, stdout path, stderr path, and expected-versus-actual outcome. The old ledger should be identified explicitly as a generated summary and not treated as command output.

### 5) Schema version scope must remain separate

This is an important clarification. The governance schema version and the AssetsDB schema version are different fields and should not be conflated. The relevant values are:

- governance schema version: 2.0
- database schema version for `assets.db`: 2.1
- `asset_dictionary[0].schema_version`: 2.1

These are separate declarations in the manifest and do not by themselves imply an incompatibility. This is a metadata-scoping issue, not a defect in the packet.

## Status update on packet readiness

Based on Paul’s review and the preserved evidence, the packet remains a valid frozen input for a later rehearsal handoff, subject to the evidence correction work.

My updated view is:

- BFT-01 packet integrity: PASS
- Original ZIP checksum and member set: PASS, with explicit evidence retained
- Source verification: PASS for readable originals; blocked or denied for the four generated artifact originals, which must remain reported as access-limited rather than silently substituted
- Corrected evidence package: REQUIRED
- Product Scan/QC or release acceptance: NOT ESTABLISHED; this remains separate from the handoff packet

## Next decision

Proceed with the BFT-01R follow-up exactly as Paul described: preserve the original BFT-01 submission, generate a fresh verifier under a new run, capture true execution evidence, and return a corrected companion evidence ZIP plus markdown completion note. This is the smallest safe next step and it does not imply a product acceptance claim.

## Updated BFT-A1–A6 view

- BFT-A1: PASS (input inventory and availability are explicit)
- BFT-A2: PASS for packet integrity and readable source stability; access limitations remain explicitly reported
- BFT-A3: PASS (generated governance artifacts accounted for)
- BFT-A4: PASS (version and path-risk findings are documented without rewriting history)
- BFT-A5: PASS for the archive structure and extraction safety checks in reviewed evidence
- BFT-A6: PASS for READY handoff status if the evidence is corrected and the frozen packet remains unchanged

The original BFT-01 content is usable; the fix is in the evidence trail and the generated status wording, not in the source payload itself.
