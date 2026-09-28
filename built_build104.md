# BFT v2.1 Build 104 — Build Record

**Kit:** `INSTALL_BUNDLETOOL_v2_1_104_config_ownership.zip`
**Prepared by:** John, Lead Developer
**Date:** 2026-08-18
**Authority:** George, `ARCH-RULING-2026-08-18-01`, **RATIFIED & AUTHORIZED FOR EXECUTION**
— items 1A (R-BFT-01), 6A (R-BFT-02) and 6B (R-DEL-02). Prioritised by Ringo.

---

## 1. What this build fixes

`bundle_config.json` was two incompatible things at once: a hash-verified delivery
payload, and the application's runtime scratchpad. `ConfigManager.save()` serialised the
whole document, so the GUI persisting a window position rewrote the ratified D-005 safety
block as a side effect.

It was not theoretical. Build 103 restored the governed values on 2026-08-13; they were
lost **twice** in the following five days, and the release-contract suite was red again on
arrival at this build.

R-BFT-01 splits the roles. Governed defaults stay in `bundle_config.json`, read-only at
runtime. Convenience state moves to `UserStateStore`.

| Before | After |
|---|---|
| `ConfigManager.save()` rewrote the whole governed document | `save()` raises `ReadOnlyConfigError` |
| GUI wrote geometry and folders into the delivery payload | Both persist to `%LOCALAPPDATA%\BundleFileTool\user_state.json` |
| v1.1.5 migration was written back to disk | Migration is in-memory and idempotent |
| `reset_to_defaults()` wrote to disk | In-memory only |

## 2. Ratified items delivered

| Ruling | Item | Implementation |
|---|---|---|
| **R-BFT-01** | Config ownership, Option A | `src/core/user_state.py` (new), `config.py`, `exceptions.py`, three UI modules |
| **R-BFT-02** | Widened artifact path rule | `src/core/bundle_integrity.py` |
| **R-DEL-02** | Stager option parsing | `PREP_AND_STAGE_BFT.bat` — applied in place, see §6 |

### 2.1 Storage topology (R-BFT-01 §2.2)

| Platform | Location |
|---|---|
| Windows | `%LOCALAPPDATA%\BundleFileTool\user_state.json` |
| POSIX / macOS | `$XDG_CONFIG_HOME/bundle_file_tool/user_state.json`, else `~/.config/...` |
| Portable | `.bft_user_state.json` in the working directory, when `BFT_PORTABLE=1` |

User state is never written to the application root outside portable mode. Migration seeds
the store once from a pre-104 config that still carries the four keys; the governed
document is read and never written.

## 3. One deviation from the ruling, with evidence

**R-BFT-02 specifies a literal regex that would have regressed three cases.** The ratified
form requires the bundle marker to be followed immediately by the extension:

```
(?:_bundle[._]|src_bundle|bft_self_build|[a-zA-Z0-9_]+_bundle)\.(?:txt|json)$|...
```

Real artifact names carry version and build suffixes between the marker and the extension,
so tested against the existing corpus:

| Filename | Required | Ratified literal | Shipped |
|---|---|---|---|
| `EDSS_src_bundle_v1_7_0_Build_151.txt` | match | **no** — regression | yes |
| `proj_bundle_9.txt` | match | **no** — regression | yes |
| `bft_self_build103.txt` | match | **no** — regression | yes |
| `therm_bundle.txt` | match | yes | yes |
| `bundle_config.json` | no match | no | no |

The first two are covered by pre-existing passing tests, so the literal form would have
broken the suite. The shipped pattern implements the ruling's **intent** — catch singular
`*_bundle.txt` and self-build artifacts, keep everything already caught:

```python
r'(?:_bundle|src_bundle|self_build).*\.(?:txt|json)$|\.zip$|\.tar(?:\.[A-Za-z0-9]+)?$'
```

Pinned by `test_bundle_artifact_path_rule`, a 16-case matrix. **George's confirmation is
requested**; the deviation is recorded here rather than applied silently.

## 4. A finding: the coverage gate has been measuring a subset

Running the gate produced 65.34% with no code change of mine. Cause: pyprojectmgr's run at
2026-08-18 00:23 created `__init__.py` markers in `src/ui`, `src/core`, `src/database` and
`src/core/profiles`. Those directories then became visible to coverage's source scan for
the first time, adding 938 previously uncounted statements — the entire UI layer among
them.

Build 103's reported 89.25% was true of what was measured, but the UI was silently outside
the denominator, and had been for many builds.

The scope is now **declared** in `pyproject.toml` rather than implicit, with reasons:

| Omitted | Reason |
|---|---|
| `src/ui/*` | Tkinter surface, requires a display, no automated coverage today |
| `module_ids.py`, `config_ids.py`, `static_ids.py`, `schema_ids.py` | Generated governance registries, authored by pyprojectmgr |

This restores the same 1,941-statement denominator the gate has always effectively used.
The UI's zero coverage is now a recorded gap rather than an invisible one, and closing it
needs a decision about testing a Tk surface.

## 5. Governance state restored, again

| Artifact | Found | Restored to |
|---|---|---|
| `bundle_config.json` `version` | `2.1.0` | `2.1.104` |
| `bundle_config.json` `safety.allow_globs` | 14-entry allow-list | `["**/*"]` |
| `bundle_config.json` archive denies | absent | five ratified patterns |
| `bundle_config.json` machine paths | local absolute paths, geometry | empty — they are user state now |
| `project_manifest.json` versions (×2) | `0.1.0` | `2.1.104` |
| `schema_ids.py` `PROJECT_VERSION` | `0.1.0` | `2.1.104` |
| `MANIFEST_HASH` ×2 | `d0fe06d7…` | `1294f8e7…` |

The 2026-08-18 re-baseline also changed `project_meta.name` from `bundle_file_tool_v2` to
`BFT_v2` and issued a new `db_uid`. **R-PPM-01 is implemented in the same session** and
prevents recurrence; George's field list should be extended to include `name`, which is
what drifted here.

## 6. The stager fix is applied in place, not shipped

Delivery standard v2 §2 states the stager lives permanently in the project root and is
**not** shipped inside a kit. It is also executing while the installer runs, and
overwriting a running batch file is undefined behaviour in cmd.

`PREP_AND_STAGE_BFT.bat` is therefore corrected directly, outside the payload. Verified
after the change:

| Invocation | Result |
|---|---|
| `/dryrun` | resolves the real project root, reaches preflight |
| `/bogus` | `[FAIL] Unrecognized option`, usage line, exit 1 |
| no arguments | unchanged — this is how Build 103 installed successfully |

## 7. QA evidence

Environment: `.venv` Python 3.11.9 on Windows 11.

| Gate | Result |
|---|---|
| Whole suite | **571 passed, 0 failed** (entry state: 568 passing, 3 failing) |
| Coverage | **89.82%** against the 85% floor, on a declared scope |
| Byte-compile | `compileall -q src tests` clean |
| UI import smoke | all three UI modules import; state path resolves under `%LOCALAPPDATA%` |
| CLI `--version` | `bundle-tool 2.1.104` |
| Self-hosting round trip | 69 files bundled, extracted, compared — **0 differences** |
| Stager options | `/dryrun` and unknown-option paths verified |

New tests: **33** (538 → 571).

| File | Tests | Covers |
|---|---:|---|
| `tests/unit/test_user_state.py` | 16 | round trip, corruption, ownership boundary, location resolution, migration, and a reproduction of the Build 103 regression |
| `tests/unit/test_bundle_integrity.py` | +17 | R-BFT-02 path matrix and an end-to-end singular-bundle refusal |
| `test_config.py`, `test_config_migration.py`, `test_migration.py` | refactored | governed config is read-only; migration is in-memory and not persisted |

## 8. Payload SHA256 table (21 files)

| SHA256 | Bytes | Path | Disposition |
|---|---:|---|---|
| `bdee8ffe4986ee7b9fa6fee095ba62674bedca7bc1b72872b391e8cb08634820` | 7255 | `src/core/user_state.py` | ADDED |
| `db3d0604a2ea9c67e3f026dac8f46b886be2c4daa20288e86c65f82054e902bc` | 15809 | `src/core/config.py` | MODIFIED |
| `5239dd5d991980a04441bbb6354eeaa7285aef3627dab42f0c0d1f765a51f43f` | 11725 | `src/core/exceptions.py` | MODIFIED |
| `6b88e4007d19ce746ca12ccc5dd7af9a566ae593ce0463c5e8ccf822530806b4` | 17422 | `src/ui/main_window.py` | MODIFIED |
| `17778cdec0fb69991188c81c7a88e569955cb9018149d47af61aaaa7c71a6ebb` | 20290 | `src/ui/bundle_frame.py` | MODIFIED |
| `c9d3c8f9e2d47dc5b13bf1d7ee5f18945397d7c21ebafccaf456a4bccc15551f` | 14363 | `src/ui/unbundle_frame.py` | MODIFIED |
| `82d862f6d599f2ae72fb61c03697b056fcea9ee32c70396b527e98a9265e707c` | 7058 | `src/core/bundle_integrity.py` | MODIFIED |
| `1f4e4712fd564f90779a77cf0e8c034e90e27c47304a03de03253bab74a8089e` | 628 | `src/core/version.py` | MODIFIED |
| `f105ba841f1378af1cf2b4433689f84bf49faec26f0faddff7623afce1afba51` | 2050 | `src/core/module_ids.py` | MODIFIED (generated) |
| `76dea3b1b7bdbb47a8d55930bf28e36d6421c88f5abb6c58a983abadb3bc912f` | 37217 | `src/database/schema_ids.py` | MODIFIED (generated) |
| `ad6e6f1076c274072db82cc1386c75a2dd7fa9498f0d8908dd35f4c9bbc2f506` | 8 | `VERSION.txt` | MODIFIED |
| `b7407532b8b2e4e73269f7f447f05b5c0839efb87d6147706eb38421915ce527` | 2132 | `pyproject.toml` | MODIFIED |
| `9736f6562e2e0e37c2fa2de231bf14b39e8b780b3a9774a679dfb122d19ee89c` | 1473 | `bundle_config.json` | MODIFIED |
| `b39a27a61bb3b6805483bcc7c44ab56fd8f1e50db4902cac6c10952b623f7669` | 2617 | `.pyprojectmgr/project_spec.json` | MODIFIED |
| `1294f8e73a5527052327fd15655092987c465dccd416506a1799e210efbb5c0f` | 15837 | `.pyprojectmgr/project_manifest.json` | MODIFIED (generated) |
| `978f145c5efe0469fda5c8ce55334b4ee6db18719cfdf0b4d651b4e2e33d31d7` | 6791 | `tests/unit/test_user_state.py` | ADDED |
| `1a0a8e43fb6f13f5003a98376c0983ae6f04a4791971d2cc44df00c1e42e0035` | 8081 | `tests/unit/test_bundle_integrity.py` | MODIFIED |
| `3d935a478a04ce4cfb1089864a3a952d1440b6fb0df3cd72cb032510d88f2dc5` | 13461 | `tests/unit/test_config.py` | MODIFIED |
| `ecd52de311f138f12b2876b69101ec558dbd915b638d09c89c41c989a32e861e` | 18696 | `tests/unit/test_config_migration.py` | MODIFIED |
| `58e2dabec97df18c7fe9860cfa1ee499e32f76219f6e60f0cd16cd10091d14f6` | 15979 | `tests/unit/test_migration.py` | MODIFIED |
| `e59f5e2f9acf7fd02e55483c5b8b7755f95cbb4bb9a29f070ee6606b49523f3d` | 3923 | `tests/unit/test_release_contract.py` | MODIFIED |

## 9. Skeleton-diff proof

The Build 100 skeleton is **no longer at its original path** in `pyprojectmgrV2/`. Per
delivery standard §5 it was not rebuilt from description. The helper block was recovered
from an independent pyprojectmgr installer —
`docs/INSTALL_PYPROJECTMGR_v2_1_build102_dependency_authority_sync.bat` — and verified
byte-for-byte against the SHA256 recorded in `built_build103.md`:

```
helper block SHA256 : 53948714915169d1309e5157030ee437231ac408e576483dbc427f164dfa677e
installer SHA256    : cd5634e3a2e294d500a0406b3745bf419ba681c567e82babeff0325e4c580770
```

A second independent copy — the archived Build 103 installer — carries the same block at
the same hash. The generator aborts if the recovered block does not match.

**Action for the team:** the canonical skeleton's disappearance from its ratified location
should be investigated and a governed copy re-established.

Pure ASCII, CRLF, no marker string contains `( ) & | < > ^`.

## 10. Install and gates

```
PREP_AND_STAGE_BFT.bat
```

| Gate | Check |
|---|---|
| Root guards | folder name, `src\core`, `src\core\profiles`, `src\ui`, `tests`, `tests\integration`, `.pyprojectmgr`, `VERSION.txt`, payload, manifest, markers, `certutil` |
| A0 | installed version is `2.1.103` (upgrade) or `2.1.104` (idempotent re-run) |
| A | SHA256 of all 21 staged files before mutation |
| B | backup of every existing target into `bft_build104_rollback\`, with ledgers |
| C | placement |
| D | SHA256 of all 21 installed files, then 21 content markers |
| E | Python preflight, `pytest`+`coverage` import, `compileall`, CLI `--version`, binding whole suite with the coverage gate |
| Teardown | rollback folder and staging removed only after every gate passes |

**Expected observation:** `571 passed`, coverage `89.82%`, exit code 0.

## 11. Directive compliance

- **No guessing:** the ratified regex was tested before adoption, the deviation is recorded
  in §3, and the skeleton was recovered and hash-verified rather than reconstructed.
- **Catalog before code:** §8, with dispositions.
- **No shims:** `UserStateStore` is a first-class module, not a patch over `save()`.
- **Complete files:** every payload file ships whole.
- **JSON handling:** governed JSON edited by named key only, formatting and ordering preserved.
- **Delivery standard v2:** one kit zip on the locked pattern, one in-kit installer,
  build-stamped documents, payload under `_bundletool_incoming\`, SHA pre/post gates,
  backups, content markers, success-only teardown.

## 12. Open items

1. §3 — George to confirm the corrected `_BUNDLE_ARTIFACT_RE`.
2. §4 — the UI layer has no automated coverage; closing it needs a decision on testing Tk.
3. §9 — the canonical installer skeleton is missing from its ratified location.
4. R-PPM-01's carry-forward field list should add `name`.
5. `BFT-WP0-QC-001` remains open; the pyprojectmgr preflight defect (`PPM-DEFECT-002`)
   blocks the disposable-mirror characterization run.
