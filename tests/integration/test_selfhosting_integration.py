# ============================================================================
# SOURCEFILE: test_selfhosting_integration.py
# RELPATH: bundle_file_tool_v2/tests/integration/test_selfhosting_integration.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.103
# LIFECYCLE: Testing
# STATUS: Build 103 - BFT_B103_SELFHOSTING_INTEGRATION_TESTS
# DESCRIPTION:
#   Full self-hosting workflow (Paul s7 items 23-30), sequenced BEFORE the unit
#   expansion per George's 2026-08-04 ratification. Exercises the path that 480
#   passing unit tests never covered: discovery -> manifest -> integrity gate ->
#   format -> parse -> extract, over the project's own trees.
# ============================================================================
"""Full self-hosting workflow integration tests."""

from __future__ import annotations

import pathlib

import pytest

from core.bundle_integrity import assert_bundle_clean, find_nested_bundles
from core.models import BundleEntry, BundleManifest
from core.parser import BundleParser
from core.profiles.plain_marker import PlainMarkerProfile
from core.writer import BundleCreator, BundleWriter


REPO = pathlib.Path(__file__).resolve().parents[2]
_SEP = "# " + "=" * 67


@pytest.fixture(scope="module")
def project_manifest() -> BundleManifest:
    """Item 23: bundle the actual src and tests trees through BundleCreator."""
    creator = BundleCreator(allow_globs=["**/*.py"])
    files = []
    for tree in ("src", "tests"):
        root = REPO / tree
        if root.exists():
            files.extend(creator.discover_files(root, base_path=REPO))
    if len(files) < 10:
        pytest.skip("project trees not available in this environment")
    return creator.create_manifest(sorted(files), REPO, "plain_marker")


@pytest.fixture(scope="module")
def project_bundle(project_manifest: BundleManifest) -> str:
    return PlainMarkerProfile().format_manifest(project_manifest)


def test_23_creator_discovers_both_project_trees(project_manifest):
    """The manifest must come from real discovery, not a hand-built list."""
    paths = {e.path for e in project_manifest.entries}
    assert "src/core/profiles/plain_marker.py" in paths
    assert "src/core/bundle_integrity.py" in paths
    assert any(p.startswith("tests/") for p in paths)
    assert not any("__pycache__" in p for p in paths)


def test_24_integrity_gate_accepts_the_projects_own_trees(project_manifest):
    """The tool must be allowed to bundle itself (Paul s7 item 24, s5.5)."""
    assert find_nested_bundles(project_manifest) == []
    assert_bundle_clean(project_manifest, source_label="self-hosting")


def test_25_27_roundtrip_preserves_every_file_exactly(project_manifest, project_bundle):
    """Format then parse must return the same paths and the same bodies."""
    back = BundleParser().parse(project_bundle, profile_name="plain_marker")

    assert len(back.entries) == len(project_manifest.entries), "entry count changed"
    assert {e.path for e in back.entries} == {e.path for e in project_manifest.entries}

    original = {e.path: e for e in project_manifest.entries}
    for entry in back.entries:
        source = original[entry.path]
        assert entry.content == source.content, f"content changed: {entry.path}"
        assert entry.encoding == source.encoding
        assert entry.eol_style == source.eol_style


def test_26_no_phantom_entries_are_invented(project_manifest, project_bundle):
    """No path may appear that was not bundled (the original defect)."""
    back = BundleParser().parse(project_bundle, profile_name="plain_marker")
    phantoms = {e.path for e in back.entries} - {e.path for e in project_manifest.entries}
    assert phantoms == set(), f"phantom entries invented: {sorted(phantoms)}"


def test_28_extraction_to_disk_matches_source(tmp_path, project_manifest, project_bundle):
    """Item 28: extract through the real writer and compare on disk.

    Headers are disabled so the comparison is against the transported body.
    With headers enabled the canonical repo header is prepended by policy, which
    is covered by the writer's own header tests.
    """
    back = BundleParser().parse(project_bundle, profile_name="plain_marker")
    writer = BundleWriter(output_dir=tmp_path, overwrite_policy="overwrite",
                          add_headers=False)

    stats = writer.extract_manifest(back, tmp_path)

    assert stats["errors"] == 0
    assert stats["processed"] == len(back.entries)
    assert stats["processed"] + stats["skipped"] + stats["errors"] == len(back.entries)

    original = {e.path: e for e in project_manifest.entries}
    for entry in back.entries:
        with open(tmp_path / entry.path, "r", encoding="utf-8", newline="") as fh:
            written = fh.read()
        assert written == original[entry.path].content, (
            f"disk content differs: {entry.path}"
        )


def test_29_real_historical_bundle_is_still_blocked():
    """The safety property must survive the classifier change."""
    nested = (_SEP + "\n# FILE: core/thing.py\n"
              "# META: encoding=utf-8; eol=LF; mode=text\n" + _SEP + "\nx = 1\n")
    manifest = BundleManifest(
        entries=[BundleEntry(path="docs/old_snapshot.txt", content=nested)],
        profile="plain_marker")

    assert find_nested_bundles(manifest)
    with pytest.raises(Exception):
        assert_bundle_clean(manifest, source_label="historical")


def test_30_marker_bearing_sources_are_not_blocked(project_manifest):
    """Real project files quoting markers must pass the integrity gate."""
    bearers = [e for e in project_manifest.entries if e.content.count("# FILE:") >= 2]
    assert bearers, "expected the project to contain marker-bearing sources"

    manifest = BundleManifest(entries=bearers, profile="plain_marker")
    assert find_nested_bundles(manifest) == []
    assert_bundle_clean(manifest, source_label="marker-bearing")


def test_determinism_same_input_same_artifact(project_manifest):
    """Delivery standard v3 s8 and BFT-B100-036 depend on this."""
    profile = PlainMarkerProfile()
    assert profile.format_manifest(project_manifest) == profile.format_manifest(project_manifest)


def test_sized_bounded_payload_preserves_trailing_newlines_exactly():
    """Bounded size metadata distinguishes payload bytes from format padding."""
    profile = PlainMarkerProfile()

    def roundtrip(content):
        manifest = BundleManifest(
            entries=[BundleEntry(path="a.py", content=content, is_binary=False,
                                 encoding="utf-8", eol_style="LF", checksum=None,
                                 file_size_bytes=len(content.encode("utf-8")))],
            profile="plain_marker")
        return profile.parse_stream(profile.format_manifest(manifest)).entries[0].content

    assert roundtrip("x = 1\n") == "x = 1\n"          # exact
    assert roundtrip("x = 1") == "x = 1"              # no final newline added
    assert roundtrip("x = 1\n\n") == "x = 1\n\n"      # trailing blank retained
