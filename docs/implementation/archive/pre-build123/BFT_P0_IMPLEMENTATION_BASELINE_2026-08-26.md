# BFT P0 Implementation Baseline — 2026-08-26

**Recorded by:** Paul, Lead Developer  
**Purpose:** Preserve the exact pre-change state of files in the P0 implementation scope without staging, committing, or altering unrelated working-tree changes.

## Repository state

- Git HEAD: `b88d67c36c4f2ff97837a0fbee24e907e691fba5`
- Branch observed during review: `master`
- Product version surfaces: `2.1.116`
- Working tree: pre-existing, extensively dirty; Build 103–116 selection-workspace files are largely untracked relative to HEAD.
- Policy: P0 work will edit only named implementation/test/documentation files and will not stage, commit, revert, delete, or normalize unrelated user changes.

This is a checksum ledger, not a claim that the dirty tree is an immutable release. A clean release branch/tag remains a required exit gate.

## Pre-change SHA-256 ledger

| SHA-256 | File |
|---|---|
| `F4490B2CC4F9DFE598C18F968949234A7CC9FA29BED24C6DFD610B908B64469C` | `src/cli.py` |
| `E38A6408300A7C147B2E5BE31FF4033B1B6C89932044BCD212F314416FAE2B05` | `src/cli_plan.py` |
| `A2CE3548837C493CE22A312BFCE5D846E743D79D84F07904C2BD3394EAB262EF` | `src/core/service.py` |
| `9BC80DAD29BB6392B0B1D8914AC5608025601E821A27B80D05141ACB0DE8B27A` | `src/core/selection.py` |
| `2A9A95336D8BA8FC9B9F8DF5E855A96B22D8126E578E381394EA8CE56299869B` | `src/core/metadata_scan.py` |
| `5239DD5D991980A04441BBB6354EEAA7285AEF3627DAB42F0C0D1F765A51F43F` | `src/core/exceptions.py` |
| `41AD7B88321F99E4526C8C0DBE38A9206AA34533DBF38CFF08B7FE6FFDC3CDE6` | `src/core/writer.py` |
| `5C173C6F20EDD6796567DBE78ECB165671EFCE0E25383892395ED668ED4281CB` | `src/ui/bundle_frame.py` |
| `197CC2A15407EC990813794E2B4BF352C4BC2FB4D5ECD622D4CBE8A0F77F3AB2` | `src/ui/selection_workspace.py` |
| `7D3C3C1544276D1AA172FBD15A92F1DE348EA5A5BA00A1B5EC5098F73EF7D387` | `tests/integration/test_cli_plan.py` |
| `6286C0325431A8EE209545AFA4D090C773671F1ACEA3D16B4AE12377B8FCC341` | `tests/unit/test_service_planning.py` |
| `6CA7B7355324F95FEA64C1C769745D0CDC9FA09C7ADDF6C7C7A1C01920FC64C8` | `tests/integration/test_service_facade.py` |

## Verified starting test baseline

The repository virtual environment produced `1402 passed` with `91.21%` statement coverage before P0 implementation began.
