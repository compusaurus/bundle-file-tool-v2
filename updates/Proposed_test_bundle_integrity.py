# ============================================================================
# SOURCEILE: test_bundle_integrity.py
# RELPATH: bundle_file_tool_v2/tests/unit/test_bundle_integrity.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.0
# LIFECYCLE: Proposed
# DESCRIPTION: Build 198 bundle-integrity guard - nested-bundle detection (S1b/S2a) + dup-path helper (S2d)
# SOURCEFILE: test_bundle_integrity.py
# Relative Path: C:/Users/mpw/Python/bundle_file_project/bundle_file_tool_v2/tests/unit/test_bundle_integrity.py
# Purpose:
# independent_entry_point:
# ============================================================================

"""
Unit tests for core/bundle_integrity.py (Build 198 embedded-151 purge guard).

Maps to Paul's test plan (S10): nested-by-path, model-rejects-dup, distinct-basenames-ok, clean-passes,
archive-entry-as-generated-caught, nested-by-content, single-marker-not-flagged, generator-write-gate.
Duplicate full paths are enforced at the model layer (BundleManifest.__post_init__), so the guard's
unique job is nested-bundle detection.
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
# (separator / '# FILE:' / '# META:'). Per the 2026-08-04 ratification the
# classifier no longer counts marker mentions, so a fragment of bare '# FILE:'
# lines is deliberately NOT a nested bundle -- see MARKER_MENTIONS below.
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


def test_generator_write_gate():
    # generator preflight: a bundle-typed artifact in the payload -> refuse before any write
    m = mk([("a.js", "1"), ("release/proj_bundle_9.txt", "hdr")])
    with pytest.raises(ValidationError):
        assert_bundle_clean(m, source_label="generator-preflight")
