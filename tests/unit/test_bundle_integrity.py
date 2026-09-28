# ============================================================================
# SOURCEFILE: test_bundle_integrity.py
# RELPATH: bundle_file_tool_v2/tests/unit/test_bundle_integrity.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.103
# LIFECYCLE: Testing
# STATUS: Build 104 - BFT_B104_INTEGRITY_TESTS (path rule) + BFT_B103_INTEGRITY_TESTS
# DESCRIPTION: bundle-integrity guard - nested-bundle detection (S1b/S2a) + dup-path helper (S2d)
# Relative Path: tests/unit/test_bundle_integrity.py
# Purpose:
# independent_entry_point:
# ============================================================================

"""
Unit tests for core/bundle_integrity.py.

Maps to Paul's test plan (S10): nested-by-path, model-rejects-dup, distinct-basenames-ok, clean-passes,
archive-entry-as-generated-caught, nested-by-content, marker-mentions-not-flagged, generator-write-gate.
Duplicate full paths are enforced at the model layer (BundleManifest.__post_init__), so the guard's
unique job is nested-bundle detection.

Build 103 (ratified 2026-08-04, Paul s5.5): the content classifier no longer counts marker mentions.
An entry is a nested bundle only when its body OPENS as a complete transport artifact.
"""

import pytest
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from core.models import BundleEntry, BundleManifest
from core.exceptions import ValidationError
from core.bundle_integrity import (
    bundle_integrity_report,
    assert_bundle_clean,
    find_nested_bundles,
    find_duplicate_paths,
)

_SEP = "# " + "=" * 67

# A genuine nested bundle: content that OPENS as a complete transport artifact
# (separator / '# FILE:' / '# META:').
NEST = (
    _SEP + "\n# FILE: core/appVersion.js\n"
    "# META: encoding=utf-8; eol=LF; mode=text\n" + _SEP + "\nx\n"
    + _SEP + "\n# FILE: core/caseFile.js\n"
    "# META: encoding=utf-8; eol=LF; mode=text\n" + _SEP + "\ny\n"
)

# A parser, fixture or document that merely SHOWS several markers mid-body.
MARKER_MENTIONS = (
    "def parse():\n"
    "    # example bundle markers, shown for documentation:\n"
    "# FILE: core/appVersion.js\n"
    "x\n"
    "# FILE: core/caseFile.js\n"
    "y\n"
)


def mk(entries):
    return BundleManifest(
        entries=[BundleEntry(path=p, content=c) for (p, c) in entries],
        profile='plain_marker',
    )


def test_nested_sentinel_by_path():
    m = mk([("core/appVersion.js", "a"), ("EDSS_src_bundle_v1_7_0_Build_151.txt", "hdr")])
    assert [p for p, _, _ in find_nested_bundles(m)] == ["EDSS_src_bundle_v1_7_0_Build_151.txt"]
    with pytest.raises(ValidationError):
        assert_bundle_clean(m, source_label="t1")


def test_model_rejects_duplicate_full_paths():
    # S2d is enforced at the MODEL layer: BundleManifest itself refuses duplicate full paths.
    with pytest.raises(ValueError):
        mk([("core/appVersion.js", "current"), ("core/appVersion.js", "stale-151")])
    # the pre-manifest helper flags them on a raw path list (generator discovery stage)
    assert find_duplicate_paths(["a/x.js", "a/x.js", "b/y.js"]) == {"a/x.js": 2}


def test_duplicate_basename_distinct_paths_ok():
    # same basename 'config.js', distinct expected relative paths -> NOT a collision (Paul guardrail)
    m = mk([("core/config.js", "a"), ("gui/config.js", "b")])
    assert find_duplicate_paths([e.path for e in m.entries]) == {}
    assert assert_bundle_clean(m, source_label="t3")['clean'] is True


def test_clean_bundle_passes():
    m = mk([("core/appVersion.js", "a"), ("gui/App.jsx", "b"), ("main.jsx", "c")])
    assert bundle_integrity_report(m)['clean'] is True
    assert_bundle_clean(m, source_label="t4")  # no raise


def test_archive_entry_as_generated_is_caught():
    # KEY: at generation the archive is ONE clean entry (unique path) that passes the model dup-check;
    # only the nested-bundle guard catches it -> refuse write (the gap the current tool misses).
    m = mk([
        ("core/appVersion.js", "current"),
        ("archives/EDSS_src_bundle_v1_7_0_Build_151.txt", NEST),
        ("gui/App.jsx", "current gui"),
    ])
    assert bundle_integrity_report(m)['nested_bundle_count'] == 1
    with pytest.raises(ValidationError):
        assert_bundle_clean(m, source_label="t5")


def test_nested_by_content_only():
    m = mk([("docs/notes.txt", NEST)])
    assert find_nested_bundles(m)[0][1] == 'content'
    with pytest.raises(ValidationError):
        assert_bundle_clean(m, source_label="t6")


def test_nested_by_content_tolerates_leading_blank_lines():
    m = mk([("docs/notes.txt", "\n\n" + NEST)])
    assert find_nested_bundles(m)[0][1] == 'content'


def test_multiple_marker_mentions_not_flagged():
    """A file quoting several markers mid-body is not a nested bundle.

    This is the case that previously blocked the tool from bundling its own
    test suite: the old classifier counted marker lines, so any parser,
    fixture or document showing two or more examples was refused before
    formatting ever ran.
    """
    m = mk([("tests/unit/test_plain_marker.py", MARKER_MENTIONS)])
    assert find_nested_bundles(m) == []
    assert_bundle_clean(m, source_label="t7b")  # no raise


def test_single_marker_mention_not_flagged():
    # a source file that mentions '# FILE:' once in a comment must NOT be flagged
    m = mk([("core/parser.py", "# handles a single '# FILE:' marker line\nprint(1)")])
    assert find_nested_bundles(m) == []
    assert_bundle_clean(m, source_label="t7")  # no raise


def test_marker_without_separator_prefix_not_flagged():
    # '# FILE:' first, no framing separator -> a fragment, not a transport artifact
    m = mk([("docs/fragment.txt", "# FILE: a.py\n# META: encoding=utf-8\nbody\n")])
    assert find_nested_bundles(m) == []


def test_binary_entry_content_is_not_scanned_as_text():
    m = mk([("assets/logo.png", "iVBORw0KGgoAAAANSUhEUg==")])
    m.entries[0].is_binary = True
    assert find_nested_bundles(m) == []


def test_generator_write_gate():
    # generator preflight: a bundle-typed artifact in the payload -> refuse before any write
    m = mk([("a.js", "1"), ("release/proj_bundle_9.txt", "hdr")])
    with pytest.raises(ValidationError):
        assert_bundle_clean(m, source_label="generator-preflight")


# ---------------------------------------------------------------------------
# Build 104 - R-BFT-02 path-rule widening
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("filename,expected", [
    # must still match - covered by the pre-existing tests above
    ("EDSS_src_bundle_v1_7_0_Build_151.txt", True),
    ("proj_bundle_9.txt", True),
    ("archive.zip", True),
    ("payload.tar", True),
    ("payload.tar.gz", True),
    # newly matched by the widening
    ("therm_bundle.txt", True),
    ("therm_bundle._20260202txt.txt", True),
    ("bft_self_build103.txt", True),
    ("my_bundle.json", True),
    # must NOT match - ordinary governed sources and config
    ("bundle_config.json", False),
    ("bundle_integrity.py", False),
    ("test_bundle_integrity.py", False),
    ("bundle_frame.py", False),
    ("deny_additions.json", False),
    ("project_manifest.json", False),
    ("BFT_v2_src_build_101.txt", False),
])
def test_bundle_artifact_path_rule(filename, expected):
    """The path rule is the primary control; the content rule is the backstop."""
    from core.bundle_integrity import _BUNDLE_ARTIFACT_RE
    assert bool(_BUNDLE_ARTIFACT_RE.search(filename)) is expected


def test_singular_bundle_name_is_refused_end_to_end():
    """therm_bundle.txt was the real specimen that slipped the old path rule."""
    m = mk([("src/app.py", "x = 1\n"), ("bundles/therm_bundle.txt", "anything")])
    hits = find_nested_bundles(m)
    assert [p for p, _, _ in hits] == ["bundles/therm_bundle.txt"]
    assert hits[0][1] == "path"
    with pytest.raises(ValidationError):
        assert_bundle_clean(m, source_label="widened")


# ---------------------------------------------------------------------------
# BFT_B116_STALE_HEADER_IS_NOT_A_BUNDLE
# ---------------------------------------------------------------------------

STALE_HEADER = (
    "# ===================================================================\n"
    "# FILE: seed_entry_points.py\n"
    "# META: encoding=utf-8; eol=LF; mode=text\n"
    "# ===================================================================\n"
    "import sys\n"
    "\n"
    "def main():\n"
    "    return 0\n"
)


def test_one_leftover_transport_header_is_not_a_nested_bundle():
    """The real case that blocked bundling a 1,115-file project.

    A source file extracted by an older build kept the transport header that
    extraction wrote into it. Its first three lines therefore open as a bundle,
    which was the entire test until Build 116 - so the file was refused as a
    nested bundle and the whole project could not be bundled.

    The diagnostic even printed the evidence against itself: "2 embedded
    '# FILE:' markers" on an entry that would need one per bundled file, i.e.
    over a thousand, to be what it was accused of being.
    """
    m = mk([("scripts/seed_entry_points.py", STALE_HEADER)])
    assert find_nested_bundles(m) == []
    assert_bundle_clean(m, source_label="stale")  # no raise


def test_a_leftover_header_is_still_reported():
    """Legitimate, but almost never intended - so it is said out loud."""
    from core.bundle_integrity import bundle_integrity_report, find_stale_headers

    m = mk([("scripts/seed_entry_points.py", STALE_HEADER)])
    assert find_stale_headers(m) == [("scripts/seed_entry_points.py", 1)]
    report = bundle_integrity_report(m)
    assert report["stale_header_count"] == 1
    assert report["clean"] is True, "a stale header must not fail the bundle"


def test_two_transport_blocks_are_still_a_nested_bundle():
    """The protection that matters is unchanged: a real bundle is refused."""
    m = mk([("docs/notes.txt", NEST)])
    assert find_nested_bundles(m)[0][1] == "content"
    with pytest.raises(ValidationError):
        assert_bundle_clean(m, source_label="still-nested")


def test_transport_blocks_are_counted_not_guessed():
    from core.bundle_integrity import count_transport_blocks

    assert count_transport_blocks(STALE_HEADER) == 1
    assert count_transport_blocks(NEST) == 2
    assert count_transport_blocks("just some source\n") == 0
    assert count_transport_blocks("") == 0


def test_a_bundle_named_file_is_still_refused_by_path():
    """Path-based detection is untouched; it is the stronger signal."""
    m = mk([("bundles/proj_src_bundle_v1.txt", "anything at all\n")])
    assert find_nested_bundles(m)[0][1] == "path"


def test_a_real_extracted_source_file_round_trips(tmp_path):
    """End to end: a tree containing a stale-header file bundles cleanly."""
    from core.writer import BundleCreator

    # The header must name the file it sits in - that is what makes it a
    # leftover rather than a one-entry bundle, and it is what extraction
    # actually writes.
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "seed_entry_points.py").write_text(
        STALE_HEADER, encoding="utf-8")
    (tmp_path / "ordinary.py").write_text("x = 1\n", encoding="utf-8")

    creator = BundleCreator(allow_globs=["**/*"], deny_globs=[])
    found = creator.discover_files(tmp_path, tmp_path)
    manifest = creator.create_manifest(found, tmp_path, "plain_marker")
    assert_bundle_clean(manifest, source_label="roundtrip")  # no raise
    assert manifest.get_file_count() == 2


def test_a_one_entry_bundle_naming_another_file_is_still_blocked():
    """Where block counting runs out, the self-naming rule takes over.

    A bundle carrying a single file is structurally identical to a leftover
    header: separator, '# FILE:', '# META:', separator, body. What separates
    them is which file the header names - extraction names the file it is
    writing, a bundle names somebody else's.
    """
    one_entry = (_SEP + "\n# FILE: core/thing.py\n"
                 "# META: encoding=utf-8; eol=LF; mode=text\n" + _SEP + "\nx = 1\n")
    m = mk([("docs/old_snapshot.txt", one_entry)])
    assert find_nested_bundles(m)[0][1] == "content"
    with pytest.raises(ValidationError):
        assert_bundle_clean(m, source_label="one-entry")


def test_the_discriminator_is_the_name_not_the_shape():
    """Identical bodies, different verdicts, decided only by the entry path."""
    from core.bundle_integrity import header_names_its_own_file

    body = (_SEP + "\n# FILE: seed_entry_points.py\n"
            "# META: encoding=utf-8; eol=LF; mode=text\n" + _SEP + "\nimport sys\n")
    assert header_names_its_own_file("scripts/seed_entry_points.py", body)
    assert not header_names_its_own_file("docs/something_else.txt", body)

    assert find_nested_bundles(mk([("scripts/seed_entry_points.py", body)])) == []
    assert find_nested_bundles(mk([("docs/something_else.txt", body)]))


def test_a_full_relative_path_in_the_header_also_counts_as_self_naming():
    from core.bundle_integrity import header_names_its_own_file

    body = (_SEP + "\n# FILE: scripts/seed_entry_points.py\n"
            "# META: encoding=utf-8\n" + _SEP + "\nimport sys\n")
    assert header_names_its_own_file("scripts/seed_entry_points.py", body)
