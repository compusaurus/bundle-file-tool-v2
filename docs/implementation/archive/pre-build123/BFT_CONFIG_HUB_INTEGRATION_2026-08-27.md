# BFT ConfigHub Settings Integration

BFT's **File → Settings** command now opens ConfigEdit's governed ConfigHub
through a BFT-scoped PyProjectMgr session. The integration deliberately spans
three projects without moving configuration ownership between them.

| Project | Incorporated information and responsibility |
| --- | --- |
| BFT | `.pyprojectmgr/setup_contribution.json`, `config/bft_settings.schema.json`, and `src/core/config_setup.py` define BFT identity, fields, hidden user-state pointers, validation, safety impact, activation, and postflight. `src/ui/config_hub_launcher.py` requests only application `bft`. |
| PyProjectMgr | `config/config_hub_registry.json` authenticates the BFT root and asset paths. The `bft` provider loads BFT's hook, rejects stale config/schema/manifest state, and commits the exact config bytes, synchronized manifest digest, and audit together. The CLI accepts `setup --application bft`. |
| ConfigEdit | `launch_config_hub(session, initial_app_id="bft")` selects the already-authorized BFT application. ConfigEdit receives working copies and proposals only; it does not resolve BFT paths or write governed files. |

Legacy `session`, `last_source_dir`, and `last_bundle_save_dir` values are not
rendered. They remain under `UserStateStore`. `ConfigManager.save()` remains a
hard failure, so ordinary BFT runtime code still cannot persist the governed
document.

The BFT commit set is:

1. `bundle_config.json` serialized from the reviewed working copy;
2. `.pyprojectmgr/project_manifest.json` with
   `governance.governed_config_sha256` calculated from those exact bytes; and
3. PyProjectMgr's ConfigHub audit record.

PyProjectMgr places all three through its recoverable multi-artifact
transaction, runs the BFT-owned postflight hook, rolls all three back on
postflight failure, and restores the prior read-only policy.

Focused acceptance coverage proves BFT-only scoping, contribution/manifest
identity binding, field and safety validation, stale-manifest rejection,
atomic config-plus-manifest placement, postflight rollback, read-only
restoration, and ConfigEdit initial-application selection.

## Build 118 delivery correction

The first Settings adapter selected `pythonw.exe` for the sibling
PyProjectMgr virtual environment. In this CLI-to-Tk startup path that process
exited before ConfigEdit opened, while `Popen` had already returned success and
Windows had no console on which to display the failure.

The adapter now prefers `python.exe` and retains `CREATE_NO_WINDOW`, so the
user still receives a console-free GUI launch without the `pythonw` stream
failure. BFT writes startup output to the per-user
`BundleFileTool/config_hub_launch.log`, watches the child for six seconds, and
shows an error dialog with the diagnostic tail if it exits during startup.
The success status is not displayed until that watch completes.
