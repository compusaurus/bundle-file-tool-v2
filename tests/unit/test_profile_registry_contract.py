# BFT_B105_REGISTRY_CONTRACT_TESTS
# ============================================================================
# SOURCEFILE: test_profile_registry_contract.py
# RELPATH: bundle_file_tool_v2/tests/unit/test_profile_registry_contract.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.105
# LIFECYCLE: Testing
# STATUS: Build 105 - BFT_B105_REGISTRY_CONTRACT_TESTS
# DESCRIPTION: The configuration/registry/CLI contract. Build 104 shipped with
#              MarkdownFenceProfile implemented but unregistered; these tests
#              connect the three layers so that gap cannot reopen.
# ============================================================================
"""Contract tests binding configuration, the profile registry and the CLI.

Paul's Build 104 review, blocker 1. The existing suite missed the defect because
the Markdown tests instantiate `MarkdownFenceProfile` directly and the registry
tests only asserted that `plain_marker` exists. Nothing connected the profile a
configuration can *select* to the profile the registry can *produce*.
"""

from __future__ import annotations

import json

import pytest

from core.config import ConfigManager
from core.exceptions import ProfileNotFoundError
from core.models import BundleEntry, BundleManifest
from core.parser import BundleParser, ProfileRegistry
from core.profiles.base import ProfileBase


# ---------------------------------------------------------------------------
# Every profile the configuration can select must be registered
# ---------------------------------------------------------------------------

def test_default_profile_from_packaged_config_is_registered():
    """The single defect that shipped in Build 104.

    `ConfigManager.DEFAULT_CONFIG` selects `md_fence`, which the registry did
    not know about, so any invocation falling back to the packaged default
    raised ProfileNotFoundError.
    """
    default_profile = ConfigManager.DEFAULT_CONFIG["app_defaults"]["bundle_profile"]
    registry = ProfileRegistry()
    assert default_profile in registry.list_profiles()
    assert registry.get(default_profile).profile_name == default_profile


def test_governed_config_default_profile_is_registered():
    """The shipped config's default must also be produceable."""
    cfg = ConfigManager()
    selected = cfg.get("app_defaults.bundle_profile", None)
    assert selected, "the governed config must declare a bundle profile"
    assert selected in ProfileRegistry().list_profiles()


@pytest.mark.parametrize("profile_name", ["plain_marker", "md_fence"])
def test_every_shipped_profile_is_registered_and_usable(profile_name):
    registry = ProfileRegistry()
    assert profile_name in registry.list_profiles()
    profile = registry.get(profile_name)
    assert isinstance(profile, ProfileBase)
    assert profile.profile_name == profile_name


def test_registry_order_is_deterministic():
    """list_profiles() feeds user-facing diagnostics; it must not vary."""
    first = ProfileRegistry().list_profiles()
    for _ in range(5):
        assert ProfileRegistry().list_profiles() == first
    assert first == sorted(first)


def test_unknown_profile_still_fails_loudly_and_names_the_alternatives():
    registry = ProfileRegistry()
    with pytest.raises(ProfileNotFoundError) as excinfo:
        registry.get("no_such_profile")
    message = str(excinfo.value)
    for known in registry.list_profiles():
        assert known in message


# ---------------------------------------------------------------------------
# Each registered profile must actually round-trip
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("profile_name", ["plain_marker", "md_fence"])
def test_registered_profile_round_trips_through_the_parser(profile_name):
    entries = [
        BundleEntry(path="src/app.py", content="VALUE = 1\n", is_binary=False,
                    encoding="utf-8", eol_style="LF", checksum=None),
        BundleEntry(path="src/pkg/util.py", content="def f():\n    return 2\n",
                    is_binary=False, encoding="utf-8", eol_style="LF", checksum=None),
    ]
    manifest = BundleManifest(entries=entries, profile=profile_name)

    profile = ProfileRegistry().get(profile_name)
    text = profile.format_manifest(manifest)
    assert text.strip(), "the profile produced no output"

    back = BundleParser().parse(text, profile_name=profile_name)
    assert {e.path for e in back.entries} == {e.path for e in entries}


@pytest.mark.parametrize("profile_name", ["plain_marker", "md_fence"])
def test_registered_profile_validates_through_the_parser(profile_name):
    manifest = BundleManifest(
        entries=[BundleEntry(path="a.py", content="A = 1\n", is_binary=False,
                             encoding="utf-8", eol_style="LF", checksum=None)],
        profile=profile_name)
    text = ProfileRegistry().get(profile_name).format_manifest(manifest)

    result = BundleParser().validate_bundle(text, profile_name=profile_name)
    assert result["valid"] is True, result["errors"]
    assert result["profile"] == profile_name
    assert result["file_count"] == 1


# ---------------------------------------------------------------------------
# A missing or misplaced governed config must not silently change behaviour
# ---------------------------------------------------------------------------

def test_governed_config_resolves_from_the_application_root_not_the_cwd(monkeypatch, tmp_path):
    """Blocker 2. The governed document's location is a property of the
    installation, not of the directory the process was started in."""
    expected = ConfigManager.governed_config_path()

    monkeypatch.chdir(tmp_path)
    assert ConfigManager().config_file == expected

    src_dir = expected.parent / "src"
    if src_dir.is_dir():
        monkeypatch.chdir(src_dir)
        assert ConfigManager().config_file == expected


def test_missing_governed_config_uses_packaged_defaults_without_creating_a_file(
        monkeypatch, tmp_path, capsys):
    """It must never write a governed-looking file into an arbitrary directory."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(ConfigManager, "governed_config_path",
                        staticmethod(lambda: tmp_path / "bundle_config.json"))

    cfg = ConfigManager()

    assert not (tmp_path / "bundle_config.json").exists(), (
        "a missing governed config must not be recreated on the fly"
    )
    assert cfg.get("safety.allow_globs") == ["**/*"]
    assert "not found" in capsys.readouterr().err

    # and the default profile is still one the registry can produce
    assert cfg.get("app_defaults.bundle_profile") in ProfileRegistry().list_profiles()


def test_policy_drift_is_reported(tmp_path):
    """The drift that recurred three times is now detectable by the application."""
    drifted = tmp_path / "bundle_config.json"
    drifted.write_text(json.dumps({
        "version": "2.1.0",
        "schema_version": "2.1",
        "safety": {"allow_globs": ["**/*.py"], "deny_globs": ["**/.git/**"], "max_file_mb": 10},
        "app_defaults": {"bundle_profile": "plain_marker"},
    }), encoding="utf-8")

    findings = ConfigManager(str(drifted)).check_governed_policy()

    assert any("allow_globs" in f for f in findings)
    assert any("deny_globs" in f for f in findings)
    assert any("version" in f for f in findings)


def test_clean_governed_config_reports_no_drift():
    assert ConfigManager().check_governed_policy() == []
