# ============================================================================
# SOURCEFILE: test_selfhosting_roundtrip.py
# RELPATH: bundle_file_tool_v2/tests/unit/test_selfhosting_roundtrip.py
# PROJECT: Bundle File Tool v2.1
# VERSION: 2.1.102
# STATUS: Proposed
# DESCRIPTION:
#   Regression guard for the self-hosting round trip: bundling a file whose
#   CONTENT contains bundle marker syntax. Every pre-existing round-trip test
#   uses small marker-free fixtures, which is why the boundary defect survived
#   480 green tests. These tests fail on the pre-nonce parser.
# ============================================================================
"""Self-hosting round-trip regression tests (per-bundle nonce)."""

import pytest

from core.models import BundleEntry, BundleManifest
from core.parser import BundleParser
from core.profiles.plain_marker import PlainMarkerProfile


NESTED_FIXTURE = (
    "import pytest\n"
    "\n"
    "@pytest.fixture\n"
    "def sample_bundle():\n"
    '    return """# ===================================================================\n'
    "# FILE: src/example.py\n"
    "# META: encoding=utf-8; eol=LF; mode=text\n"
    "# ===================================================================\n"
    "def greet():\n"
    "    pass\n"
    '"""\n'
)


def _roundtrip(entries):
    profile = PlainMarkerProfile()
    manifest = BundleManifest(entries=entries, profile="plain_marker")
    text = profile.format_manifest(manifest)
    return text, BundleParser().parse(text, profile_name="plain_marker")


def _entry(path, content):
    return BundleEntry(
        path=path, content=content, is_binary=False,
        encoding="utf-8", eol_style="LF", checksum=None,
    )


def test_embedded_bundle_does_not_create_phantom_entries():
    """A sample bundle inside a file must not be split out as its own file."""
    _, back = _roundtrip([_entry("tests/conftest.py", NESTED_FIXTURE)])
    assert len(back.entries) == 1, [e.path for e in back.entries]
    assert back.entries[0].path == "tests/conftest.py"


def test_embedded_bundle_content_is_preserved_verbatim():
    """The embedded markers must survive the round trip unchanged."""
    _, back = _roundtrip([_entry("tests/conftest.py", NESTED_FIXTURE)])
    assert back.entries[0].content == NESTED_FIXTURE


def test_banner_lines_in_content_are_not_eaten():
    """A file's own '# ====' header banner is content, not a bundle border."""
    banner = (
        "# ============================================================\n"
        "# SOURCEFILE: thing.py\n"
        "# ============================================================\n"
        "VALUE = 1\n"
    )
    _, back = _roundtrip([_entry("src/thing.py", banner)])
    assert back.entries[0].content == banner


def test_meta_line_in_content_is_not_consumed_as_metadata():
    """A '# META:' line inside file content must stay in the content."""
    body = "# META: this line belongs to the file\nVALUE = 2\n"
    _, back = _roundtrip([_entry("src/thing.py", body)])
    assert back.entries[0].content == body


def test_multi_file_bundle_with_embedded_markers_is_exact():
    """Entry count and every body survive when several files carry markers."""
    entries = [
        _entry("tests/conftest.py", NESTED_FIXTURE),
        _entry("src/plain.py", "VALUE = 3\n"),
        _entry("tests/other.py", NESTED_FIXTURE.replace("example", "other")),
    ]
    _, back = _roundtrip(entries)
    assert len(back.entries) == len(entries)
    got = {e.path: e.content for e in back.entries}
    for e in entries:
        assert got[e.path] == e.content


def test_bundle_is_nonce_stamped_and_nonce_absent_from_content():
    """The nonce must be present in the bundle and absent from every body."""
    import re
    text, _ = _roundtrip([_entry("tests/conftest.py", NESTED_FIXTURE)])
    match = re.search(r"^# === BFT:([0-9a-f]{16}) =+$", text, re.MULTILINE)
    assert match, "bundle carries no nonce-stamped separator"
    assert match.group(1) not in NESTED_FIXTURE


def test_legacy_bundle_without_nonce_still_parses():
    """v1.1.5 compatibility: an un-stamped bundle still parses."""
    legacy = (
        "# ===================================================================\n"
        "# FILE: src/legacy.py\n"
        "# META: encoding=utf-8; eol=LF; mode=text\n"
        "# ===================================================================\n"
        "LEGACY = True\n"
    )
    manifest = BundleParser().parse(legacy, profile_name="plain_marker")
    assert len(manifest.entries) == 1
    assert manifest.entries[0].path == "src/legacy.py"
