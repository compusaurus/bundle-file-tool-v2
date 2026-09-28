"""Application-owned validation hooks for governed BFT setup.

ConfigEditor edits only an in-memory working copy.  PyProjectMgr loads this
module from BFT's governed setup contribution and calls these pure functions
before and after its multi-artifact transaction.  No function in this module
writes configuration or user state.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SetupIssue:
    """A field-addressed BFT setup diagnostic."""

    severity: str
    rule_id: str
    pointer: str
    message: str


_REQUIRED_DENY_GLOBS = (
    "**/*_bundle_*.txt",
    "**/*.zip",
    "**/*.tar",
    "**/*.tar.*",
    "**/archives/**",
)

_READ_ONLY_POINTERS = (
    "/version",
    "/schema_version",
    "/session",
    "/global_settings/last_source_dir",
    "/global_settings/last_bundle_save_dir",
    "/global_settings/relative_base_path",
    "/app_defaults/encoding",
    "/app_defaults/eol",
    "/ui/layout",
    "/ui/show_info_panel",
    "/ui/show_log_panel",
    "/ui/progress/show_elapsed",
    "/ui/progress/show_rate",
)


def validate_document(
    candidate: dict[str, Any],
    baseline: dict[str, Any] | None = None,
) -> list[SetupIssue]:
    """Validate a proposed BFT governed configuration without side effects."""

    issues: list[SetupIssue] = []
    if not isinstance(candidate, dict):
        return [
            SetupIssue("ERROR", "bft.root.type", "", "Configuration root must be an object")
        ]

    for section in ("global_settings", "app_defaults"):
        if not isinstance(candidate.get(section), dict):
            issues.append(
                SetupIssue(
                    "ERROR",
                    "bft.section.required",
                    f"/{section}",
                    f"Required section '{section}' is missing or is not an object",
                )
            )

    _enum(issues, candidate, "/app_defaults/default_mode", ("unbundle", "bundle"))
    _enum(
        issues,
        candidate,
        "/app_defaults/bundle_profile",
        ("plain_marker", "md_fence"),
    )
    _enum(
        issues,
        candidate,
        "/app_defaults/overwrite_policy",
        ("prompt", "skip", "rename", "overwrite"),
    )
    _enum(issues, candidate, "/ui/layout", ("top", "middle", "bottom"), optional=True)
    _enum(issues, candidate, "/ui/bundle_mode", ("workspace", "classic"), optional=True)
    _enum(
        issues,
        candidate,
        "/global_settings/ui_layout/buttons_position",
        ("top", "bottom"),
        optional=True,
    )
    _enum(
        issues,
        candidate,
        "/global_settings/ui_layout/info_panel_position",
        ("top", "middle", "bottom"),
        optional=True,
    )

    max_file_mb = _get(candidate, "/safety/max_file_mb")
    if isinstance(max_file_mb, bool) or not isinstance(max_file_mb, (int, float)) or max_file_mb <= 0:
        issues.append(
            SetupIssue(
                "ERROR",
                "bft.safety.max_file_mb",
                "/safety/max_file_mb",
                "Maximum file size must be a positive number",
            )
        )

    allow_globs = _get(candidate, "/safety/allow_globs")
    if allow_globs != ["**/*"]:
        issues.append(
            SetupIssue(
                "ERROR",
                "bft.policy.allow_globs",
                "/safety/allow_globs",
                "The ratified allow list must remain ['**/*']",
            )
        )

    deny_globs = _get(candidate, "/safety/deny_globs")
    if not isinstance(deny_globs, list) or not all(isinstance(item, str) for item in deny_globs):
        issues.append(
            SetupIssue(
                "ERROR",
                "bft.safety.deny_globs.type",
                "/safety/deny_globs",
                "Deny patterns must be an array of strings",
            )
        )
    else:
        missing = [item for item in _REQUIRED_DENY_GLOBS if item not in deny_globs]
        if missing:
            issues.append(
                SetupIssue(
                    "ERROR",
                    "bft.policy.deny_globs",
                    "/safety/deny_globs",
                    f"Required safety patterns are missing: {', '.join(missing)}",
                )
            )

    if baseline is not None:
        for pointer in _READ_ONLY_POINTERS:
            if _get(candidate, pointer, _MISSING) != _get(baseline, pointer, _MISSING):
                issues.append(
                    SetupIssue(
                        "ERROR",
                        "bft.read_only",
                        pointer,
                        "This value is identity or per-user state and is not editable here",
                    )
                )
        if _get(candidate, "/safety", _MISSING) != _get(baseline, "/safety", _MISSING):
            issues.append(
                SetupIssue(
                    "WARNING",
                    "bft.safety.elevated",
                    "/safety",
                    "Safety policy changed; explicit warning acknowledgement is required",
                )
            )

    return issues


def verify_committed(config_path: str | Path, manifest_path: str | Path) -> None:
    """Strict postflight for a PyProjectMgr BFT settings transaction."""

    config_file = Path(config_path)
    manifest_file = Path(manifest_path)
    config_bytes = config_file.read_bytes()
    candidate = json.loads(config_bytes.decode("utf-8"))
    issues = [issue for issue in validate_document(candidate) if issue.severity == "ERROR"]
    if issues:
        raise ValueError("; ".join(f"{issue.pointer}: {issue.message}" for issue in issues[:3]))

    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    expected = manifest.get("governance", {}).get("governed_config_sha256")
    actual = hashlib.sha256(config_bytes).hexdigest()
    if expected != actual:
        raise ValueError(
            "BFT manifest/config integrity mismatch after commit: "
            f"expected {expected!r}, actual {actual}"
        )


class _Missing:
    pass


_MISSING = _Missing()


def _get(document: Any, pointer: str, default: Any = None) -> Any:
    current = document
    try:
        for segment in pointer.strip("/").split("/"):
            if not segment:
                continue
            current = current[segment.replace("~1", "/").replace("~0", "~")]
    except (KeyError, TypeError):
        return default
    return current


def _enum(
    issues: list[SetupIssue],
    document: dict[str, Any],
    pointer: str,
    allowed: Iterable[Any],
    *,
    optional: bool = False,
) -> None:
    value = _get(document, pointer, _MISSING)
    if optional and value is _MISSING:
        return
    allowed_values = tuple(allowed)
    if value not in allowed_values:
        issues.append(
            SetupIssue(
                "ERROR",
                "bft.enum",
                pointer,
                f"Value must be one of: {', '.join(map(str, allowed_values))}",
            )
        )


__all__ = ["SetupIssue", "validate_document", "verify_committed"]
