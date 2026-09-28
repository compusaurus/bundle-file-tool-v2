"""BFT-owned governed setup contract tests."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy

import pytest

from core.config_setup import validate_document, verify_committed


def _live_config():
    return json.loads((__import__("pathlib").Path(__file__).parents[2] / "bundle_config.json").read_text(encoding="utf-8"))


def test_live_governed_document_passes_application_setup_validation():
    assert not [issue for issue in validate_document(_live_config()) if issue.severity == "ERROR"]


def test_legacy_user_state_is_not_editable_through_governed_setup():
    baseline = _live_config()
    candidate = deepcopy(baseline)
    candidate["session"]["window_geometry"] = "900x700"

    issues = validate_document(candidate, baseline)

    assert any(issue.rule_id == "bft.read_only" and issue.pointer == "/session" for issue in issues)


def test_safety_change_requires_acknowledgement_and_cannot_weaken_required_patterns():
    baseline = _live_config()
    candidate = deepcopy(baseline)
    candidate["safety"]["deny_globs"].remove("**/*.zip")

    issues = validate_document(candidate, baseline)

    assert any(issue.rule_id == "bft.policy.deny_globs" and issue.severity == "ERROR" for issue in issues)
    assert any(issue.rule_id == "bft.safety.elevated" and issue.severity == "WARNING" for issue in issues)


def test_postflight_binds_committed_bytes_to_manifest_digest(tmp_path):
    config = tmp_path / "bundle_config.json"
    manifest = tmp_path / "project_manifest.json"
    config.write_text(json.dumps(_live_config(), indent=2) + "\n", encoding="utf-8")
    digest = hashlib.sha256(config.read_bytes()).hexdigest()
    manifest.write_text(json.dumps({"governance": {"governed_config_sha256": digest}}), encoding="utf-8")

    verify_committed(config, manifest)

    manifest.write_text(json.dumps({"governance": {"governed_config_sha256": "0" * 64}}), encoding="utf-8")
    with pytest.raises(ValueError, match="integrity mismatch"):
        verify_committed(config, manifest)
