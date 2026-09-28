# BFT v2.1 Build 100 — WP0 Source Reconciliation

**Record ID:** BFT-WP0-SRC-001
**Prepared by:** Paul, Lead Analyst
**Date:** 2026-07-23
**Source artifact:** `C:\Users\mpw\Python\bundles\BFT_v2_src_build_101.txt`

## 1. Entry-state result

The attached Build 101 bundle contains 21 governed source files. All 21 match the corresponding live source files exactly after normalizing line endings for comparison.

This proves that the attachment and live `src` tree represented the same candidate source baseline at WP0 entry. It did not, by itself, prove that the candidate passed tests or that the wider repository was clean.

## 2. File evidence

| File | Bytes | Live SHA256 | Bundle match |
|---|---:|---|---|
| `src/cli.py` | 10225 | `82db07bb121e756cc776d794fc22f70ba828b255b6e471263db87f3a3033faee` | Exact |
| `src/core/bundle_integrity.py` | 4744 | `96b7781f7ebbd110a49d29d331a9feb7b23021e408f4315f015bcf50ea17e65d` | Exact |
| `src/core/config.py` | 14400 | `c9bc9c1f68790ed6b2c6e022ace0159b7885adedab876fbe5e3cc4390222cfdf` | Exact |
| `src/core/config_ids.py` | 1166 | `fb1d8bab1834299e42846959816fdaad7bffeb651fcd72bc6173e8f6a9e19d8d` | Exact |
| `src/core/exceptions.py` | 11092 | `ef507db63ab8ffb8c7031b0c07efc29d5dfca26f370b479e6b9ea173871318d5` | Exact |
| `src/core/logging.py` | 16769 | `96fc6c973f3c6b3b52ee78d8907c080cbcf59397ceb2bc14db7e6c1a54f1729e` | Exact |
| `src/core/models.py` | 8314 | `33af1de49b8b070d470e2945bc9791482e4efe2be985d7647ee9d4c37bcbe6f9` | Exact |
| `src/core/module_ids.py` | 8454 | `e33eba82f73638a0e912a5dd5a2f1cce18e09d17f4f358940aa31b9c34cb4cbf` | Exact |
| `src/core/parser.py` | 10061 | `fb0e04fd50910281da8eac89eee16bf4adbb1571e8a83c0a6b251a6593129204` | Exact |
| `src/core/profiles/base.py` | 13249 | `62eb9e890712479b024bf9795ffcff4fb383eb8fb132ac5dd23207bdc4283808` | Exact |
| `src/core/profiles/markdown_fence.py` | 13361 | `54488f11d433bf70672533ca6dd4343ecc9b6aaecff50a0ab5cb22b791e114d9` | Exact |
| `src/core/profiles/plain_marker.py` | 19940 | `302abfb8366d48ca8f4349d0491dcf98d4e0e33e0aa26dfca523ef6e3f90aea0` | Exact |
| `src/core/static_ids.py` | 1320 | `7138aeab37bafc4482a932f5e3174a814bb89186491464b50230316255d5ac61` | Exact |
| `src/core/validators.py` | 19754 | `197ac919ca3f6975453456a044ece57649e0a8b93b5a9e4a89873e61b5112f50` | Exact |
| `src/core/writer.py` | 35304 | `bc8d22bf5083b6dd7ed0e7a3ddccfe8e67966bdb9f95352f09b707eeb70ed030` | Exact |
| `src/database/schema_ids.py` | 38132 | `52b2261160201885d48f7b464f83b02a17d077e21553e414a74bd0b839191c9b` | Exact |
| `src/main.py` | 4237 | `d2f8f612eabc2163a6a48a8a8ebe710a3b02c156a524fb042e15959b819b5603` | Exact |
| `src/ui/bundle_frame.py` | 21478 | `2e3bf742769e3c2ad1d302c01aafb1399daf57c524bde235e1f5a25d2118466b` | Exact |
| `src/ui/main_window.py` | 17150 | `8c6570066bc87f5596edeaa54f7a290e3f1a715e9d9247f9bcfee31a4db3a54b` | Exact |
| `src/ui/mode_manager.py` | 6999 | `f1a183b6fcf80d09a0b1c4d85a1e2d00905c34d961476bc42bdc14a5a54534da` | Exact |
| `src/ui/unbundle_frame.py` | 14633 | `45c4ec7a93699c6d4d2c233bad052adf4a029e0b6608f20f53f38dc6fe5dbc0e` | Exact |

## 3. Pre-ratification WP0 normalization delta

WP0 deliberately changed nine of the 21 source files after the exact entry-state comparison. Three contain functional corrections; six contain whitespace-only normalization. The other 12 source files remain byte-for-byte identical to the attached bundle after line-ending and terminal-newline normalization.

| File | Post-normalization bytes | Post-normalization SHA256 | Approved reason for divergence |
|---|---:|---|---|
| `src/cli.py` | 10017 | `094b5db5d33ab028e7db18e497a85cc7740f1315a688e3e509d1d5e4163f1efc` | Remove trailing whitespace only. |
| `src/core/logging.py` | 18111 | `2da274e5ab96163f457272de034c1e7314b0b5f3477c626f1b83dae2876830e2` | Restore the documented structured completion/error schema, make log-directory fallback safe, and remove trailing whitespace. |
| `src/core/models.py` | 8018 | `e89935995743865de95578112d2e7ebe60ccfb2a1396175b1bd5cc39dedcee65` | Enforce the model invariant that paths cannot be null, empty, or whitespace-only; remove trailing whitespace. |
| `src/core/parser.py` | 9759 | `4e1b27b022a42a05b986e96c1d470d0ed0f47fca6845b92e27168a6072996693` | Remove trailing whitespace only. |
| `src/core/profiles/base.py` | 12791 | `f2aa723e6a70a950476b9134b825339860959aef82c4a246085e5d1d74607068` | Remove trailing whitespace only. |
| `src/core/writer.py` | 32599 | `d6ed95018caf7ab4b32412da436b473571311f979b51590adad39c749c77cbaf` | Remove the production monkeypatch of `builtins.all` and its test-only compatibility wrapper classes; use strict Base64 validation. |
| `src/database/schema_ids.py` | 37196 | `b2db1b55cc0e12d9822805c75c0616b0f9df1712bebc0b881a4ed1a0ed82fe57` | Remove trailing whitespace only. |
| `src/main.py` | 4189 | `977cd85fcbd9b47d2364c3a85f1670e32dacbb9beb1c30af8384d67c64a2c605` | Remove trailing whitespace only. |
| `src/ui/bundle_frame.py` | 20710 | `143ae8321ea84ae87f77a67cbed98e90ed1ada49797350a5af023cf0056190bc` | Remove trailing whitespace only. |

The code-catalog comparison found 21 source files before and after normalization. It found no lost product module or product function. The only removed callables were 13 writer compatibility-shim functions and methods associated with `_safe_all`, `_IterableBool`, `_LengthProxy`, and `OperationLog`. Whitespace-only normalization does not alter the catalog.

## 4. Ringo ratification implementation delta

Ringo ratified the remaining policy decisions on 2026-07-23. Implementing those decisions changed eight existing source files and added one package-version module. The current governed source set therefore contains 22 files.

| File | Current bytes | Current SHA256 | Ratified reason for divergence |
|---|---:|---|---|
| `src/cli.py` | 10175 | `7ca498f9722dc4f90de32baadc374c76660eed33408b8cf310af6579d57567d8` | Add `--version` using the package-owned version source. |
| `src/core/config.py` | 14489 | `4117b6e86fe1d4e98e1a2ba0d58a036a1e347b8b66c938dd4061a3b8dbaf8482` | Synchronize the approved deny-list safety default and package/schema version metadata. |
| `src/core/config_ids.py` | 1165 | `4a9daa9011e3c53cf87355d6edb35be3ffac47b6af9cc540cbb38e589a7b762f` | Synchronize generated governance metadata to the ratified manifest. |
| `src/core/module_ids.py` | 8452 | `c7d614fa85ca4ed13cc51fa655a95a3510d36e863fb50e501ee508d7e86b7d58` | Synchronize generated governance metadata to the ratified manifest. |
| `src/core/static_ids.py` | 1319 | `b439366dafbf5f8ba0bb96e74605a37ce69406835a58496f42afee0a3c592455` | Synchronize generated governance metadata to the ratified manifest. |
| `src/core/version.py` | 474 | `e14137ae9eb19187acf1fc327f7cdaeaa330b2f82b4e36d89560e7518b7d00e9` | Establish package-owned installed version `2.1.102` with a source-tree fallback. |
| `src/core/writer.py` | 32597 | `b26df1b0641337210e1ebb98d44abb5b1a6526b17f518fab2f5e110fb7708fa0` | Use the package-owned version in generated bundle headers. |
| `src/database/schema_ids.py` | 37196 | `052ccbcceb1859a289d956235cee4bfb6255b0843e8b574ae22bb47fa7f9ed2a` | Synchronize project version and generated governance metadata to the ratified manifest. |
| `src/ui/main_window.py` | 17202 | `07e0262174f3e5f558ce76f84f56e2dcb9f349643ce3c52bf716a601e351aa4a` | Use the package-owned version in visible application metadata. |

The current catalog contains 22 source files. No pre-existing product module or callable was lost; `src/core/version.py` adds the package-version accessor used by the CLI, writer, configuration, and desktop UI.

## 5. Reconciliation notes

- The source bundle is authoritative for candidate source content, not for version policy.
- Mixed source-header versions remain metadata debt and are not runtime version truth.
- The production test-compatibility patch of `builtins.all` has been removed, and the malformed assertion that depended on it was corrected in the test suite.
- The attached source does not contain `BundleToolService`, JSONL profile implementation, or Web package. Those remain later work packages.
- The wider baseline includes tests, policies, scripts, governance data, and delivery controls not carried by the source bundle; those are cataloged separately.
- Repository awareness is formally deferred to Build 101.
- The required `.pyprojectmgr/project_spec.json` now records the intentional host-ACL separation-of-duties policy for protected Git metadata.

## 6. Source acceptance gate

The current 22-file candidate source set, including the pre-ratification normalization and the ratified implementation delta, is accepted as the normalized WP0 source baseline because:

- the full configured suite passes: 480 tests, zero failures;
- configured coverage is 88.49%, above the 85% gate;
- no production test monkeypatch remains;
- the code-catalog comparison reports no lost product source;
- package version `2.1.102`, deny-list synchronization, required project specification, generated governance metadata, and non-incrementing stager behavior are covered by release-contract tests;
- every post-bundle source change is enumerated above and the candidate passes Git's whitespace check.

Runtime version ownership is ratified and implemented. The protected branch commit is an intentional separation-of-duties delivery control: an authorized interactive account must create the commit without weakening the `.git` ACL.
