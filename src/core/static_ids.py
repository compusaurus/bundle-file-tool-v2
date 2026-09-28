# ============================================================================
# SOURCEFILE: static_ids.py
# RELPATH: src/core/static_ids.py
# Project: pyprojectmgr
# Team: Ringo / George / John / Paul
# Version: 1.0.0
# STATUS: Generated
# DESCRIPTION: Ref-first registry of governed static asset references.
# Generated: 2026-09-23 02:48:13Z
# Manifest: .pyprojectmgr/project_manifest.json
# Manifest Version: 3.0.4
# Manifest Hash (sha256): 1da8cb9e1cdac9ae13bf75a75cb462df94c460055f78696d97eeb205dbd7f1cb
# ============================================================================

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StaticRef:
    uid: str
    relpath: str
    category: str
    owner_module_id: str
    description: str
    lifecycle: str
    content_hash: str | None = None

    def path(self, project_root: Path) -> Path:
        return project_root / self.relpath


class StaticIDs:
    """Generated namespace of static asset references."""
    # No static_assets defined in manifest.
    pass

