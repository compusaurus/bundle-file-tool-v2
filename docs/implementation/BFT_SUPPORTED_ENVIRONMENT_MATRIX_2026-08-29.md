# BFT Supported Environment Matrix

**Updated:** 2026-08-31  
**Status:** cleanly recreated and release-qualified for Build 123  
**Declared Python range:** `>=3.11,<3.14`

## Outcome

BFT has three independent, explicitly named supported environments. The legacy
`.venv` directory was removed rather than reused because it was damaged and its
name did not identify the runtime it was intended to contain.

| Environment | Runtime | Purpose | PyThermX | Build 123 result |
| --- | --- | --- | --- | --- |
| `.venv311` | CPython 3.11.9, Tk 8.6.12 | Binding/default BFT environment | 0.5.3 | 1,538 passed; 87.41% branch coverage |
| `.venv312` | CPython 3.12.10, Tk 8.6.15 | Second supported-version matrix row | 0.5.3 | 1,538 passed |
| `.venv313` | CPython 3.13.15, Tk 8.6.15 | Third supported-version matrix row | 0.5.3 | 1,538 passed |

Each environment contains its own `Scripts\python.exe`, `activate.bat`, and
`deactivate.bat`. Each reports BFT `2.1.123`, imports the governed PyThermX
wheel from its own `site-packages`, and passes the same complete test suite.

## Reproducible provisioning

The pinned test toolchain is recorded in `requirements-test-matrix.txt`.
`scripts/setup_supported_envs.ps1` creates and provisions all three rows,
discovers registered per-user CPython installations when explicit paths are
absent, installs PyThermX only from the governed wheel under `vendor/`, and
creates a real Tk root during postflight.

Provide explicit interpreter paths or set `BFT_PYTHON311`, `BFT_PYTHON312`,
and `BFT_PYTHON313`:

```powershell
./scripts/setup_supported_envs.ps1 `
  -Python311 C:\path\to\Python311\python.exe `
  -Python312 C:\path\to\Python312\python.exe `
  -Python313 C:\path\to\Python313\python.exe
```

Use `-Recreate` only after every BFT process using any supported environment is
closed. Recursive deletion is limited to the exact project-root paths
`.venv311`, `.venv312`, and `.venv313`; the exact legacy `.venv` path is also
permitted only during an explicit `-Recreate` migration. Any legacy `.venv`
otherwise blocks provisioning and installation.

## Release binding

Python 3.11 is the binding coverage row. Python 3.12 and 3.13 run the identical
functional suite without duplicating coverage instrumentation. The Build 123
installer prefers `.venv311`, verifies all present standardized rows, rejects a
legacy `.venv`, and installs PyThermX 0.5.3 into every supported row present.
