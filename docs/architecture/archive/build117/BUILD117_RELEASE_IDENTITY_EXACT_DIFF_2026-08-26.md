# Build 117 Release-Identity Exact-Diff Approval Record

**Package ID:** BFT-2.1.117-IDENTITY-2026-08-26  
**Status:** Staged and verified; Ringo ratified; George exact-diff approval pending  
**Prepared by:** Paul, Lead Developer / Lead Analyst  
**Date:** 2026-08-26  
**Live-tree identity:** `2.1.116` (unchanged)  
**Proposed identity:** `2.1.117`

## 1. Approval record

Ringo approved and ratified Build 117 Governance on 2026-08-26. That approval authorizes release-candidate preparation, isolated mutation, verification, and submission of this exact diff.

George's approval is still required before the staged identity is applied to the live governed tree. The repository's separation-of-duties policy also requires an authorized interactive account—not an automated agent—to write the Git index, commit, ref, or tag.

## 2. Scope boundary

This is the Build 117 **release-identity** proposal. It is not the broader Phase 0 structural governance reconciliation described in `BFT_GOVERNANCE_RECONCILIATION_PROPOSAL_2026-08-26.md`.

- No governance schema, authority, trust, team, entry-point, scan-scope, or infrastructure field changes.
- `bundle_config.json` changes only its package-owned release version. All operational settings remain byte-for-byte equivalent.
- The manifest's governed-config digest changes only because that release-version field changes.
- Manifest schema remains `3.0.4`.
- The live governed files have not been modified.

## 3. Exact approved field proposal

| File / JSON pointer or symbol | Before | Proposed |
|---|---|---|
| `VERSION.txt` | `2.1.116` | `2.1.117` |
| `pyproject.toml` `/project/version` | `2.1.116` | `2.1.117` |
| `bundle_config.json` `/version` | `2.1.116` | `2.1.117` |
| `.pyprojectmgr/project_spec.json` `/version` | `2.1.116` | `2.1.117` |
| `.pyprojectmgr/project_manifest.json` `/last_updated` | `2026-08-18T02:26:39Z` | `2026-08-26T20:03:23Z` |
| `.pyprojectmgr/project_manifest.json` `/project_meta/version` | `2.1.116` | `2.1.117` |
| `.pyprojectmgr/project_manifest.json` `/governance/governed_config_sha256` | `7ac770bcc0b906a6e60920202a6aec7ddd88a140ac146e9243df70823a9ea0c4` | `5cf84eb590925f681a9d1026b8facf4c7b25e7e8c722384498fd8b3a77b6e69a` |
| `.pyprojectmgr/project_manifest.json` `/meta/version` | `2.1.116` | `2.1.117` |
| `src/core/version.py` `FALLBACK_VERSION` | `2.1.116` | `2.1.117` |
| `src/core/module_ids.py` `MANIFEST_HASH` | `ba59c4b0a1473f6ff8073db3a0b74b701f0b9e65ce87ac4a0499729ac2df0126` | `4e63bb7ea15414a322a42ae02a20e4779b09ab938342c4da5792f369bde1fe0b` |
| `src/database/schema_ids.py` `MANIFEST_HASH` | `ba59c4b0a1473f6ff8073db3a0b74b701f0b9e65ce87ac4a0499729ac2df0126` | `4e63bb7ea15414a322a42ae02a20e4779b09ab938342c4da5792f369bde1fe0b` |
| `src/database/schema_ids.py` `PROJECT_VERSION` | `2.1.116` | `2.1.117` |
| `tests/unit/test_release_contract.py` `EXPECTED_VERSION` | `2.1.116` | `2.1.117` |

Line-ending and EOF shapes were reconciled to the live files before these hashes were sealed. The table above is the complete semantic diff.

## 4. Exact file hashes

| File | Live baseline SHA-256 | Proposed SHA-256 |
|---|---|---|
| `VERSION.txt` | `c13ffdf4e129260aade40b2a86476e1d6c315e16ecc5036ab0c5b348195319f2` | `32f9935a6160dedec930d95dae21a56cbd4c2514db721eef89b5eaa036fc60b8` |
| `pyproject.toml` | `4aaa3b4c298c2902c57f92a742bc5827bbee948b5791abfbb612e7e76efe6e57` | `13f2416a76983fe6a7178ea66d3db3dab2e3baa670a08a25d4d3c6d16abe57d1` |
| `bundle_config.json` | `7ac770bcc0b906a6e60920202a6aec7ddd88a140ac146e9243df70823a9ea0c4` | `5cf84eb590925f681a9d1026b8facf4c7b25e7e8c722384498fd8b3a77b6e69a` |
| `.pyprojectmgr/project_spec.json` | `a7db28e5140634f9b7abcf361c4a807fce24a594322f92e5610f9c1689ea3a2b` | `5158fea614c01a84cb208777b3336bf8ac8597cf7c08419d030932f7477c3e83` |
| `.pyprojectmgr/project_manifest.json` | `ba59c4b0a1473f6ff8073db3a0b74b701f0b9e65ce87ac4a0499729ac2df0126` | `4e63bb7ea15414a322a42ae02a20e4779b09ab938342c4da5792f369bde1fe0b` |
| `src/core/version.py` | `c5a92fce648c0162251cb4f1a5fd10c8358e429fa43dfda184db02fd58961509` | `e07659cefdbdd14ca314289c711ac30a05f49e39e65da73903afd4bc53c2bd60` |
| `src/core/module_ids.py` | `9fa263d51584f4bc51cbea682e10bc6da7de1fc496a8d445ec7e781da99e08a7` | `aaf4094860aca21f4155f3c42409d57a74c3edd3bebac29c18f1e88534c01268` |
| `src/database/schema_ids.py` | `c633073c58d91599aea2f0429fdffa1e3e215d9a1a5923768b767cd2d290dafc` | `c9e86af338e1e66c2a370c61d861f7940678be5f7e3f8f3357265a09ff1a06d8` |
| `tests/unit/test_release_contract.py` | `8b26527a449ef8e7e1e030c6a95bfe20f3c59f936cd61a44875d563f8e0f4ba1` | `8ee0c461d5cab6caff2beab0a39e996cd4916e1cbc701b2287cfce126fe6ae41` |

## 5. Verification evidence

- Isolated staged full suite: **1,453 passed**, coverage **90.79%**.
- Byte-final focused identity/config gate: **20 passed**.
- Byte-final clean-room Build 116 → 117 installer run: **1,453 passed**, one known warning, coverage **90.82%**.
- Installer payload: **74/74 hashes passed** and **73/73 content markers passed**.
- Post-install independent audit: **74 manifest entries, zero hash mismatches**.
- Installed CLI identity: `bundle-tool 2.1.117`.
- Installed governed config SHA-256: `5cf84eb590925f681a9d1026b8facf4c7b25e7e8c722384498fd8b3a77b6e69a`; read-only protection confirmed.
- Success teardown removed both incoming staging and rollback directories.

## 6. George disposition

- [ ] Approve the exact Build 117 release-identity diff above.
- [ ] Approve with conditions recorded below.
- [ ] Return for revision.

Conditions / notes:

> 

**George, Lead Architect:** ____________________  **Date:** __________

Ringo's Build 117 governance ratification is recorded above; product acceptance of the final installed build remains a separate release acceptance event.
