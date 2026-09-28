# Bundle File Tool Documentation Library

**Status:** Current documentation index and organization policy  
**Last updated:** 2026-08-31  
**Verified product baseline:** Bundle File Tool 2.1.123

This is the consolidated documentation library for Bundle File Tool. Current, non-superseded specifications and baseline records are grouped by topic. Build history, team reviews, superseded specifications, generated QC workspaces, and evidence snapshots remain preserved in topic archives.

## Project-wide navigation and visibility

- [Searchable master index](INDEX.md) — internal table of contents, lifecycle register, visibility classifications, and search tags.
- [Visibility and publication policy](VISIBILITY_POLICY.md) — restricted-by-default rules and publication gate.
- [Public documentation index](PUBLIC_INDEX.md) — externally approved versions only; currently empty.

## Current document map

- [Architecture and governance](architecture/README.md) — ratified specifications and rulings, plus clearly labeled active proposals.
- [Product specifications](product/README.md) — current user-facing and workspace design sources.
- [Implementation and delivery](implementation/README.md) — the verified Build 123 baseline and current integration records.
- [Analysis and reviews](analysis/README.md) — index to point-in-time technical and team analyses.
- [Quality and evidence](quality/README.md) — WP0 records, QC outputs, scripts, and preserved generated workspaces.
- [Technical research](research/README.md) — earlier alternatives and investigation material.
- [Operations and user guidance](operations/README.md) — links to the live product and user guides.
- [Design renders](renders/README.md) — current selection-workspace images.
- [Documentation history](history/README.md) — consolidation provenance and the file-level inventory.

## Current baseline

The live source tree's package-owned version signals agree on `2.1.123`. Build 123 supersedes Builds 119–122 for delivery and baseline review. See [Current Implementation Baseline](implementation/CURRENT_BASELINE.md).

SPEC-VCS-001 v0.2.1 is labeled `RATIFIED ARCHITECTURE SPECIFICATION / PHASE 0 CONTRACT FREEZE`. Earlier repository-support drafts and their reviews are archived.

## Document-state rules

- **Current baseline or ruling:** the latest non-superseded source within its stated scope.
- **Current proposal:** a still-relevant planning or ADR candidate that remains visibly labeled as proposed and is not implementation authority.
- **Archive:** superseded, build-specific, point-in-time, generated, duplicated, or historical evidence.

An embedded status label is evidence from that document, not a substitute for approval by the named authority. Topic indexes preserve unresolved approval language instead of silently treating a proposal as ratified.

## Organization policy

1. The root contains project-wide navigation and publication-governance documents only.
2. Topic roots contain current documents and a topic index.
3. Every topic has an `archive/`; archived material is retained, not deleted.
4. Generated QC workspaces are preserved intact under the quality archive.
5. The latest explicitly ratified numbered specification supersedes earlier drafts in the same family.
6. Build reports, delivery handoffs, and team communications are point-in-time history unless a topic index identifies an enduring current ruling.
7. Original Word, PDF, image, text, source, JSON, database, and package formats are preserved.
8. The [consolidation inventory](history/DOCUMENT_CONSOLIDATION_INVENTORY_2026-08-31.csv) records every preexisting file from both documentation locations, its final destination, length, timestamp, disposition, and SHA-256.
9. Visibility is restricted by default; only exact versions registered in [PUBLIC_INDEX.md](PUBLIC_INDEX.md) may be externally distributed.
