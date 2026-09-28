# ============================================================================
# SOURCEFILE: test_selfhosting_integration.py
# RELPATH: bundle_file_tool_v2/tests/integration/test_selfhosting_integration.py
# PROJECT: Bundle File Tool v2.1
# VERSION: 2.1.102
# STATUS: Proposed
# DESCRIPTION:
#   Full self-hosting workflow (Paul s7 items 23-30), sequenced BEFORE unit
#   expansion per the 2026-08-04 ratification. Exercises the path that 480
#   passing unit tests never covered: manifest -> integrity gate -> format ->
#   parse -> extract, over the project's own trees.
# ============================================================================
"""Full self-hosting workflow integration tests."""

from __future__ import annotations

import pathlib

import pytest

from core.bundle_integrity import assert_bundle_clean, find_nested_bundles
from core.models import BundleEntry, BundleManifest
from core.parser import BundleParser
from core.profiles.plain_marker import PlainMarkerProfile


def _normalise_trailing_blanks(text: str) -> str:
    """Apply the ONE documented, pre-existing normalisation.

    The writer collapses trailing blank lines to a single final newline, and a
    file with no final newline gains one. This predates the bounded-transport
    work -- the Build 102 parser behaves identically -- so it is applied here
    rather than silently tolerated. It is pinned by
    test_known_limitation_trailing_blank_lines_are_normalised below, which will
    fail if the behaviour ever changes in either direction.
    """
    return text.rstrip("\n") + "\n" if text else text

REPO = pathlib.Path(__file__).resolve().parents[2]
_SEP = "# " + "=" * 67


def _tree_entries(*roots):
    entries = []
    for root in roots:
        base = REPO / root
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            entries.append(BundleEntry(
                path=str(path.relative_to(REPO)).replace("\\", "/"),
                content=path.read_text(encoding="utf-8"),
                is_binary=False, encoding="utf-8", eol_style="LF", checksum=None))
    return entries


@pytest.fixture(scope="module")
def project_entries():
    entries = _tree_entries("src", "tests")
    if len(entries) < 10:
        pytest.skip("project trees not available in this environment")
    return entries


def test_24_integrity_gate_accepts_the_projects_own_trees(project_entries):
    """The tool must be allowed to bundle itself (Paul s7 item 24, s5.5)."""
    manifest = BundleManifest(entries=project_entries, profile="plain_marker")
    assert find_nested_bundles(manifest) == []
    assert_bundle_clean(manifest, source_label="self-hosting")


def test_25_27_roundtrip_preserves_every_file_exactly(project_entries):
    """Format then parse must return the same paths and the same bytes."""
    manifest = BundleManifest(entries=project_entries, profile="plain_marker")
    text = PlainMarkerProfile().format_manifest(manifest)
    back = BundleParser().parse(text, profile_name="plain_marker")
    assert len(back.entries) == len(project_entries), "entry count changed"
    assert {e.path for e in back.entries} == {e.path for e in project_entries}
    original = {e.path: e.content for e in project_entries}
    for entry in back.entries:
        expected = _normalise_trailing_blanks(original[entry.path])
        assert entry.content == expected, f"content changed: {entry.path}"
        assert entry.encoding == "utf-8"
        assert entry.eol_style == "LF"


def test_26_no_phantom_entries_are_invented(project_entries):
    """No path may appear that was not bundled (the original defect)."""
    manifest = BundleManifest(entries=project_entries, profile="plain_marker")
    text = PlainMarkerProfile().format_manifest(manifest)
    back = BundleParser().parse(text, profile_name="plain_marker")
    phantoms = {e.path for e in back.entries} - {e.path for e in project_entries}
    assert phantoms == set(), f"phantom entries invented: {sorted(phantoms)}"


def test_28_extraction_to_disk_matches_source(tmp_path, project_entries):
    """Files written to disk must match the originals byte for byte."""
    subset = project_entries[:12]
    manifest = BundleManifest(entries=subset, profile="plain_marker")
    text = PlainMarkerProfile().format_manifest(manifest)
    back = BundleParser().parse(text, profile_name="plain_marker")
    for entry in back.entries:
        target = tmp_path / entry.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(entry.content, encoding="utf-8")
    for entry in subset:
        written = (tmp_path / entry.path).read_text(encoding="utf-8")
        assert written == entry.content, f"disk content differs: {entry.path}"


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


def test_30_marker_bearing_sources_are_not_blocked(project_entries):
    """Real project files quoting markers must pass the integrity gate."""
    bearers = [e for e in project_entries if e.content.count("# FILE:") >= 2]
    assert bearers, "expected the project to contain marker-bearing sources"
    manifest = BundleManifest(entries=bearers, profile="plain_marker")
    assert find_nested_bundles(manifest) == []
    assert_bundle_clean(manifest, source_label="marker-bearing")


def test_determinism_same_input_same_artifact(project_entries):
    """Delivery standard v3 s8 and BFT-B100-036 depend on this."""
    manifest = BundleManifest(entries=project_entries, profile="plain_marker")
    profile = PlainMarkerProfile()
    assert profile.format_manifest(manifest) == profile.format_manifest(manifest)


def test_known_limitation_trailing_blank_lines_are_normalised():
    """Pin the one fidelity gap that is NOT byte-exact.

    Recorded as a known limitation rather than hidden inside a lenient
    comparison. It is out of scope for the bounded-transport ratification and
    is unchanged from Build 102, but it means the round trip is byte-exact only
    up to trailing blank lines.
    """
    profile = PlainMarkerProfile()

    def roundtrip(content):
        manifest = BundleManifest(
            entries=[BundleEntry(path="a.py", content=content, is_binary=False,
                                 encoding="utf-8", eol_style="LF", checksum=None)],
            profile="plain_marker")
        return profile.parse_stream(profile.format_manifest(manifest)).entries[0].content

    assert roundtrip("x = 1\n") == "x = 1\n"          # exact
    assert roundtrip("x = 1") == "x = 1\n"             # final newline added
    assert roundtrip("x = 1\n\n") == "x = 1\n"        # trailing blank collapsed
