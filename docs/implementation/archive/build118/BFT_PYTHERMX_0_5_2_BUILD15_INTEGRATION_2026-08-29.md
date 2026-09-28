# BFT / PyThermX 0.5.2 Build 15 Integration

**Date:** 2026-08-29  
**From:** Paul, Lead Analyst  
**To:** Ringo, George, John, and the BFT / PyThermX / ConfigHub team  
**Disposition:** Integrated and qualified in the BFT 2.1.118 delivery candidate.

## Team communication

Team,

BFT now integrates the most recent governed PyThermX delivery candidate:
PyThermX **0.5.2 Build 15**. I selected the sealed Build 15 artifact rather
than the newer uncommitted files in the live PyThermX checkout. That preserves
an auditable dependency identity while the later PyThermX work continues.

The BFT optional dependency floor, vendored wheel, installer selection and
identity gates, archive-selection test, and integration tests now agree on
0.5.2. The replaced 0.5.0 wheel was removed from `vendor/` after the new wheel
passed its post-copy digest check.

The PyThermX profile API was also exercised successfully. This integration does
not copy PyThermX presentation fields into `bundle_config.json`: ConfigHub
already treats BFT settings and the PyThermX presentation profile as separate
governed applications and ownership domains. Combining them would create two
configuration authorities immediately before baselining.

## Dependency identity

| Field | Integrated value |
| --- | --- |
| Package | `pythermx` |
| Version | `0.5.2` |
| Delivery build | `15` |
| Candidate commit | `d529071ba9b35a13f31ce6f04231e6016724095e` |
| Wheel | `pythermx-0.5.2-py3-none-any.whl` |
| Wheel size | `53,962` bytes |
| Wheel SHA-256 | `f42c4ae9e1c60d18ed8dc2588248aedc8d39bdcf3648f514fadd4aa6fe17dc13` |
| Source delivery | `INSTALL_PYTHERMX_0_5_2_build15_delivered_distributions_and_reproducible_kit.zip` |

The wheel digest was verified both in the sealed Build 15 delivery and after
placement in BFT. A new BFT contract test also validates every hashed member in
the wheel's `RECORD`, the package metadata, required profile assets, exact
filename, size, and top-level SHA-256.

## BFT changes

- Replaced vendored PyThermX 0.5.0 with the sealed 0.5.2 Build 15 wheel.
- Raised the optional `progress` dependency floor to
  `pythermx>=0.5.2,<0.6`; PyThermX remains optional.
- Updated the Build 118 installer to retain, install, and identity-check 0.5.2
  in every supported environment that is present.
- Updated the archive-selection regression fixture to the new wheel name.
- Raised the integration-test floor to 0.5.2.
- Added a hash-pinned vendored-wheel contract covering package metadata,
  profile assets, path safety, and all wheel `RECORD` hashes and sizes.

## Verification

The initial compatibility run used CPython 3.13.15 with `PYTHONPATH` placing
the exact vendored wheel ahead of site packages. BFT's supported Python 3.11,
3.12, and 3.13 environments were then standardized as a three-row matrix.

| Gate | Result |
| --- | --- |
| Direct wheel import and profile construction | PASS: version 0.5.2, schema 1.1, CLI and Tk styles constructed |
| Focused BFT/PyThermX boundary | **122 passed** |
| Offline `pip --no-index --no-deps` installation | PASS: installed 0.5.2; CLI, Tk, cancellation, and profile API probe passed |
| Broad BFT suite, Python 3.11.9 | **1,493 passed**, 89.52% coverage |
| Broad BFT suite, Python 3.12.10 | **1,493 passed**, 89.52% coverage |
| Broad BFT suite, Python 3.13.15 | **1,493 passed**, 89.52% coverage |
| Governance-ID assertion | PASS: generated IDs reference final manifest `362566c844a22bf...` |

The focused run's process status was non-zero only because the repository's
85% whole-suite coverage threshold was applied to the 122-test subset. Every
selected test passed. The broad gate satisfied the threshold.

## Baseline disposition

Build 118 completes the dependency portion of the baseline candidate:

1. The governed project manifest and generated ID references were synchronized
   after the final source set was frozen.
2. The installer payload manifest covers the exact 0.5.2 wheel and final BFT
   bytes.
3. The isolated installer gate passed all 1,493 tests at 89.52% coverage.
4. Repository commit and tag actions remain assigned to the authorized
   interactive release owner.

PyThermX Build 15's own record reports its Windows 3.11, 3.12, and 3.13 gates
green. It does not relabel Build 14's physical Linux results as Build 15
evidence, and this BFT integration does not broaden that claim.
