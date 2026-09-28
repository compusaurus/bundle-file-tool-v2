# Bundle File Tool Documentation Master Index

**Document class:** `RESTRICTED_INTERNAL`  
**Purpose:** Searchable table of contents, lifecycle register, and visibility classification  
**Last updated:** 2026-09-23  

> This index reveals internal structure and document names. Do not publish it. Use [PUBLIC_INDEX.md](PUBLIC_INDEX.md) for externally approved material.

## 1. Search and classification

Search this file by title, filename, lifecycle (`BASELINE`, `RATIFIED`, `ACTIVE_CANDIDATE`, `HISTORICAL`, `ARCHIVED`), visibility label, or tags such as `vcs`, `selection-workspace`, `configeditor`, `build-123`, `quality`, `operations`, or `research`.

Visibility rules are defined in [VISIBILITY_POLICY.md](VISIBILITY_POLICY.md). `PUBLIC_CANDIDATE` remains restricted until an exact approved version appears in [PUBLIC_INDEX.md](PUBLIC_INDEX.md).

## 2. Start here

| Need | Current starting point |
|---|---|
| Library organization and document-state rules | [Documentation Library README](README.md) |
| Ratified architecture | [Architecture and Governance](architecture/README.md) |
| Product and workspace design | [Product Specifications](product/README.md) |
| Verified implementation baseline | [Current Implementation Baseline](implementation/CURRENT_BASELINE.md) |
| Supported environments | [Build 123 Supported Environment Matrix](implementation/BFT_SUPPORTED_ENVIRONMENT_MATRIX_2026-08-29.md) |
| User and operating guidance | [Operations and User Guidance](operations/README.md) |
| Quality evidence | [Quality and Evidence](quality/README.md) |
| Complete file-level provenance | [Consolidation Inventory](history/DOCUMENT_CONSOLIDATION_INVENTORY_2026-08-31.csv) |
| Public release eligibility | [Visibility Policy](VISIBILITY_POLICY.md) and [Public Index](PUBLIC_INDEX.md) |

## 3. Current architecture and product documents

| Document | Lifecycle | Visibility | Search tags | Notes |
|---|---|---|---|---|
| [SPEC-VCS-001 v0.2.1](architecture/SPEC-VCS-001_v0.2.1_Repository_Support_Specification.md) | `RATIFIED` | `PUBLIC_CANDIDATE` | `vcs git repository contract phase-0` | Candidate for a sanitized external engineering specification; approval still required |
| [BFT/VCS Narrow Integration Profile](architecture/BFT_VCS_NARROW_INTEGRATION_PROTOTYPE_2026-09-23.md) | `ACTIVE_CANDIDATE` | `RESTRICTED_INTERNAL` | `vcs bft repository tracked extraction prototype` | Authorized design-and-prototype boundary; not production integration acceptance |
| [BFT v2.2 Selection Workspace ruling](architecture/George_ARCH_Feedback_and_Ruling_BFT_v2.2_Selection_Workspace_2026-08-25.md) | `RATIFIED` | `RESTRICTED_INTERNAL` | `selection-workspace precedence grouping safety` | Internal architectural ruling |
| [BFT v2.2 Architectural Ruling Addendum](architecture/George_BFT_v2_2_Architectural_Ruling_Addendum_2026-08-25.md) | `RATIFIED` | `RESTRICTED_INTERNAL` | `detector plan-generation force-include delivery` | Internal architectural ruling |
| [Architectural Decision Record and Ratification Rulings](<architecture/George's TEAM COMMUNICATION — Architectural Decision Record & Ratification Rulings.md>) | `RATIFIED` | `RESTRICTED_INTERNAL` | `adr governance config ownership shared-component` | Cross-project governance and team communication |
| [ConfigEditor central setup architecture](architecture/CONFIGEDITOR_CENTRAL_SETUP_ARCHITECTURE_2026-08-26.md) | `ACTIVE_CANDIDATE` | `RESTRICTED_INTERNAL` | `configeditor setup architecture` | Candidate, not ratified authority |
| [ConfigEditor gaps, risks, and recommendations](architecture/CONFIGEDITOR_GAPS_RISKS_RECOMMENDATIONS_2026-08-26.md) | `ACTIVE_CANDIDATE` | `RESTRICTED_INTERNAL` | `configeditor gaps risks recommendations` | Internal assessment |
| [ConfigEditor implementation plan](architecture/CONFIGEDITOR_IMPLEMENTATION_PLAN_2026-08-26.md) | `ACTIVE_CANDIDATE` | `RESTRICTED_INTERNAL` | `configeditor implementation plan` | Internal plan |
| [ConfigEditor setup contracts](architecture/CONFIGEDITOR_SETUP_CONTRACTS_2026-08-26.md) | `ACTIVE_CANDIDATE` | `RESTRICTED_INTERNAL` | `configeditor contracts setup` | Internal contract draft |
| [Phase 0 proposed ADR set](architecture/phase0/README.md) | `ACTIVE_CANDIDATE` | `RESTRICTED_INTERNAL` | `phase-0 adr proposal` | Proposal set; not implementation authority |
| [BFT Selection Workspace Design Specification](product/BFT_SELECTION_WORKSPACE_DESIGN_SPEC.docx) | `ACTIVE_CANDIDATE` | `RESTRICTED_COMMERCIAL` | `selection-workspace product ux docx` | Unreleased product design source |
| [Developer Selection Workspace render](renders/developer-selection-workspace.png) | `ACTIVE_CANDIDATE` | `RESTRICTED_COMMERCIAL` | `render developer selection-workspace ui` | Product-design image |
| [Writer Selection Workspace render](renders/writer-selection-workspace.png) | `ACTIVE_CANDIDATE` | `RESTRICTED_COMMERCIAL` | `render writer selection-workspace ui` | Product-design image |

## 4. Current implementation and operations

| Document | Lifecycle | Visibility | Search tags | Notes |
|---|---|---|---|---|
| [Current Implementation Baseline](implementation/CURRENT_BASELINE.md) | `BASELINE` | `RESTRICTED_INTERNAL` | `baseline build-123 version delivery` | Verified source-tree baseline |
| [Build 123 Supported Environment Matrix](implementation/BFT_SUPPORTED_ENVIRONMENT_MATRIX_2026-08-29.md) | `BASELINE` | `PUBLIC_CANDIDATE` | `support matrix windows python environment build-123` | Useful public support reference after accuracy and support review |
| [PyThermX 0.5.3 Build 16 Layout Repair](implementation/BFT_PYTHERMX_0_5_3_BUILD16_LAYOUT_REPAIR_2026-08-31.md) | `HISTORICAL` | `RESTRICTED_INTERNAL` | `pythermx layout repair build-16` | Point-in-time integration/repair evidence |
| [Build 130 splash overlay and display synchronization](implementation/BFT_BUILD130_SPLASH_OVERLAY_AND_DISPLAY_SYNC_2026-09-04.md) | `ACTIVE_CANDIDATE` | `RESTRICTED_INTERNAL` | `build-130 pysplashx overlay display monitor railgun` | Installed and accepted on the Windows reference PC; public media-rights gate remains open |
| [Build 129 native identity and PySplashX integration](implementation/BFT_BUILD129_NATIVE_IDENTITY_AND_PYSPLASHX_2026-09-04.md) | `ACTIVE_CANDIDATE` | `RESTRICTED_INTERNAL` | `build-129 icon pysplashx crex video` | Native branding integration; public media-rights gate remains open |
| [Bundle File Tool README](../README.md) | `BASELINE` | `PUBLIC_CANDIDATE` | `readme installation usage overview` | Live project-root guide; exact approved version must be registered before publication |
| [Bundle File Tool User Guide](../USER_GUIDE.md) | `BASELINE` | `PUBLIC_CANDIDATE` | `user-guide operations usage` | Live user guide; requires supportability and disclosure review |

## 5. Topic and archive register

Collection classifications apply to their contents unless a file-specific row above or an approved publication record is more restrictive.

| Collection | Lifecycle | Default visibility | Search tags | Archive |
|---|---|---|---|---|
| [Architecture and Governance](architecture/README.md) | mixed current | `RESTRICTED_INTERNAL` | `architecture governance rulings adr configeditor vcs` | [Archive](architecture/archive/README.md) |
| [Product Specifications](product/README.md) | current design | `RESTRICTED_COMMERCIAL` | `product workspace design specification` | [Archive](product/archive/README.md) |
| [Implementation and Delivery](implementation/README.md) | current baseline | `RESTRICTED_INTERNAL` | `implementation delivery builds integration` | [Archive](implementation/archive/README.md) |
| [Operations and User Guidance](operations/README.md) | current | `RESTRICTED_INTERNAL` | `operations user-guide support runtime` | [Archive](operations/archive/README.md) |
| [Analysis and Reviews](analysis/README.md) | historical index | `RESTRICTED_INTERNAL` | `analysis reviews findings team` | [Archive](analysis/archive/README.md) |
| [Quality and Evidence](quality/README.md) | historical evidence | `RESTRICTED_INTERNAL` | `quality qc wp0 tests workspaces database` | [Archive](quality/archive/README.md) |
| [Technical Research](research/README.md) | historical research | `RESTRICTED_COMMERCIAL` | `research alternatives discovery` | [Archive](research/archive/README.md) |
| [Design Renders](renders/README.md) | current design | `RESTRICTED_COMMERCIAL` | `renders ui ux workspace` | [Archive](renders/archive/README.md) |
| [Documentation History](history/README.md) | provenance | `RESTRICTED_INTERNAL` | `history provenance inventory source-locations sha256` | [Archive](history/archive/README.md) |

The [file-level consolidation inventory](history/DOCUMENT_CONSOLIDATION_INVENTORY_2026-08-31.csv) is the authoritative path-level register for preserved archive content and generated QC workspaces. Those items inherit the classification of their collection; archived status never reduces sensitivity.

## 6. Maintenance checklist

1. Place new material in the narrowest topic directory.
2. Record lifecycle, visibility, owner, date, and searchable tags.
3. Update the topic README and this master index.
4. Preserve superseded material in the topic archive and update provenance records.
5. Verify relative links and the rendered form of binary documents.
6. For public release, complete the publication gate and register only the exact approved version in `PUBLIC_INDEX.md`.
