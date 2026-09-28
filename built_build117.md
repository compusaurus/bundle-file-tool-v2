# BFT v2.1 Build 117 — Build Record

**Candidate kit:** `INSTALL_BUNDLETOOL_v2_1_117_governed_ingress_and_workflow_RC1.zip`  
**Prepared by:** Paul, Lead Developer / Lead Analyst  
**Date:** 2026-08-26  
**Status:** Release candidate verified; Ringo ratified; George exact-diff approval and interactive Git release pending  
**Supersedes for installation:** Builds 106 through 116

## 1. Release outcome

Build 117 consolidates the post-116 workflow repairs and closes the transport-ingress defect reported during NodeThermX delivery verification. It is installable over `2.1.105` through `2.1.117` and has been exercised as a real `2.1.116` → `2.1.117` upgrade in a disposable tree.

The live development tree remains at governed identity `2.1.116`. The release identity exists only in the isolated staging and candidate package until George approves the exact diff and an authorized interactive account performs the protected Git operations.

## 2. Delivered behavior

1. One canonical selection plan now drives CLI, service, and GUI bundle creation, with strict plan-to-artifact reconciliation and atomic publication.
2. Bundle-open and bundle-write dialogs remember their last directories in per-user state, and bundle creation supplies a deterministic suggested filename.
3. A single click on a folder row toggles selection; clicking the native expander remains expansion-only.
4. Unbundle mode reports recorded or inferred sizes instead of `?`, and all affected panes have wired horizontal and vertical scrollbars that activate under overflow.
5. All file-based validation and extraction enter through one strict decoder: UTF-8 BOM is accepted, UTF-16/32 is detected and refused unless explicitly selected, decoding is fail-closed, and CLI `--encoding` is available on validate/unbundle.
6. Stdout purity, cross-surface parity, marker-bearing payloads, and real NodeThermX ingress remain covered.

## 3. Evidence

| Gate | Result |
|---|---|
| Staged full suite | **1,453 passed**, coverage **90.79%** |
| Byte-final identity/config subset | **20 passed** |
| Final clean-room installer suite | **1,453 passed**, one known warning, coverage **90.82%** |
| Installer staged hashes | **74/74 passed** |
| Installer content markers | **73/73 passed** |
| Independent installed-file audit | **74 entries, 0 mismatches** |
| Installed version | `bundle-tool 2.1.117` |
| Governed config | SHA-256 `5cf84eb590925f681a9d1026b8facf4c7b25e7e8c722384498fd8b3a77b6e69a`, read-only |
| Teardown | Incoming and rollback directories removed after success |

The final installer SHA-256 is `b087fecbe1cea589b4539c944712ae06bb12cdf3a3573000abc25ee20d3be432`. The delivery-manifest SHA-256 is `6ad001fd02825b089613a5001793034c32898c4848c9fd3f6b3c740fffc93017`; the marker-ledger SHA-256 is `0ba2653611be3ce93018e370bf450aec4016c3e2fe8c204ff4a1759afb89362f`.

## 4. Installer correction found during release verification

The first disposable run correctly placed the payload but exposed a batch capture defect in the CLI version probe. The probe was changed to execute `bundle-tool --version` directly and validate the package-owned version in a separate process exit gate. A second audit then found a stale display count (`67` instead of `74`). Both were corrected, and the **byte-final installer** was rerun from a fresh Build 116 tree through the complete suite.

The installer subroutine suffix beginning at `:hashVerify` remains byte-identical to Build 116 (SHA-256 `50583b4e049f2c2ba7713093cb73e4d569a68563a698fe2768214b61717ee94a`).

## 5. Governance disposition

Ringo's ratification is recorded. The exact release-identity proposal is in `docs/architecture/phase0/BUILD117_RELEASE_IDENTITY_EXACT_DIFF_2026-08-26.md`.

No automated commit or tag was attempted. `.pyprojectmgr/project_spec.json` expressly denies Git metadata writes by automated agents and reserves `.git/index` and `.git/refs/` for authorized interactive accounts.
