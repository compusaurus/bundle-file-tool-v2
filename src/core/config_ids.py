# ============================================================================
# SOURCEFILE: config_ids.py
# RELPATH: src/core/config_ids.py
# Project: pyprojectmgr
# Team: Ringo / George / John / Paul
# Version: 1.0.0
# STATUS: Generated
# DESCRIPTION: Ref-first registry of governed configuration items.
# Generated: 2026-09-23 02:48:13Z
# Manifest: .pyprojectmgr/project_manifest.json
# Manifest Version: 3.0.4
# Manifest Hash (sha256): 1da8cb9e1cdac9ae13bf75a75cb462df94c460055f78696d97eeb205dbd7f1cb
# ============================================================================

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConfigRef:
    uid: str
    key: str
    owner_module_id: str
    description: str
    scope: str
    lifecycle: str


class ConfigIDs:
    """Generated namespace of configuration item references."""
    # No config_items defined in manifest.
    pass

