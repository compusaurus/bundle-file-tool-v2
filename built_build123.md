# Bundle File Tool v2.1 Build 123 - Build Record

**Prepared:** 2026-08-31  
**Status:** Corrective delivery candidate qualified  
**Release identity:** `2.1.123`

## Outcome

Build 123 repairs the shared no-cancel PyThermX Tk layout used by Open Bundle
and Validate Bundle. PyThermX 0.5.3 now performs its initial canvas grid pass
when the Cancel control is hidden, so BFT presents the configured full progress
indicator instead of a feather-sized window shell.

The build also removes 399 confirmed zero-byte BFT session logs, retains the
single populated diagnostic log, defers creation of future session files until
the first event, and suppresses legacy empty files in the log viewer.
The final matrix also binds all classic-frame Tk variables to their owners, so
the Python 3.12 row completes without a deferred finalizer warning.

## Dependency identity

| Artifact | SHA-256 |
|---|---|
| `vendor/pythermx-0.5.3-py3-none-any.whl` | `fdf58d38c61a91f539aed37f846eb25b94f8aaa7d3cba401308c312e517f2690` |
| `bundle_config.json` | `63b6225db94f8818cbba9347baf332094d4860cc768e26593b58da8db063dd5c` |
| `.pyprojectmgr/project_manifest.json` | `d1f780c18e943bf5112b10db8342be229ccf43fe399b8740319e5c7c3906e5b3` |

## Verification

- PyThermX real-Tk widget suite: 26 passed in the live checkout.
- BFT focused cross-version boundary: 151 passed on each supported runtime.
- BFT full matrix: 1,538 passed on Python 3.11, 3.12, and 3.13.
- Binding Python 3.11 branch coverage: 87.41 percent.
- Installer forces the 0.5.3 wheel replacement in all supported environments,
  then verifies package identity and runs the complete BFT acceptance suite.

Repository commit and tag actions remain reserved for the authorized
interactive release owner.
