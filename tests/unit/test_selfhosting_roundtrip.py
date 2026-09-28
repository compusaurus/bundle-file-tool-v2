# ============================================================================
# SOURCEFILE: test_selfhosting_roundtrip.py
# RELPATH: bundle_file_tool_v2/tests/unit/test_selfhosting_roundtrip.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.103
# LIFECYCLE: Testing
# STATUS: Build 103 - BFT_B103_SELFHOSTING_ROUNDTRIP_TESTS
# DESCRIPTION:
#   Regression guard for the self-hosting round trip: bundling a file whose
#   CONTENT contains bundle marker syntax. Every pre-existing round-trip test
#   uses small marker-free fixtures, which is why the boundary defect survived
#   480 green tests. These tests fail on the Build 102 parser.
#
#   Rewritten from the pre-ratification proposal: the boundary token lives in
#   # META: as boundary=<token>, per George's 2026-08-04 ratification, not in
#   the separator line as the withdrawn nonce-separator design proposed.
# ============================================================================
"""Self-hosting round-trip regression tests (bounded transport grammar)."""

import re

import pytest

from core.models import BundleEntry, BundleManifest
from core.parser import BundleParser
from core.profiles.plain_marker import PlainMarkerProfile


_SEP = "# " + "=" * 67

# A test fixture that holds a complete sample bundle inside its body. This is
# byte-identical to real transport structure - which is exactly why marker text
# alone can never be the boundary authority.
NESTED_FIXTURE = (
    "import pytest\n"
    "\n"
    "@pytest.fixture\n"
    "def sample_bundle():\n"
    '    return """' + _SEP + "\n"
    "# FILE: src/example.py\n"
    "# META: encoding=utf-8; eol=LF; mode=text\n"
    + _SEP + "\n"
    "print('hello')\n"
    '"""\n'
)


def _entry(path, content):
    return BundleEntry(path=path, content=content, is_binary=False,
                       encoding="utf-8", eol_style="LF", checksum=None)


def _roundtrip(entries):
    profile = PlainMarkerProfile()
    manifest = BundleManifest(entries=entries, profile="plain_marker")
    text = profile.format_manifest(manifest)
    return text, profile.parse_stream(text)


def test_embedded_bundle_does_not_create_phantom_entries():
    _, manifest = _roundtrip([_entry("tests/conftest.py", NESTED_FIXTURE)])
    assert [e.path for e in manifest.entries] == ["tests/conftest.py"]


def test_embedded_bundle_content_is_preserved_verbatim():
    _, manifest = _roundtrip([_entry("tests/conftest.py", NESTED_FIXTURE)])
    assert manifest.entries[0].content == NESTED_FIXTURE


def test_banner_lines_in_content_are_not_eaten():
    content = (
        _SEP + "\n"
        "# SOURCEFILE: thing.py\n"
        + _SEP + "\n"
        "VALUE = 1\n"
    )
    _, manifest = _roundtrip([_entry("src/thing.py", content)])
    assert manifest.entries[0].content == content


def test_meta_line_in_content_is_not_consumed_as_metadata():
    content = "# META: encoding=utf-16; eol=CRLF; mode=binary\nVALUE = 2\n"
    _, manifest = _roundtrip([_entry("src/meta_holder.py", content)])
    entry = manifest.entries[0]
    assert entry.content == content
    # the content META must not have leaked into the entry's real metadata
    assert entry.encoding == "utf-8"
    assert entry.eol_style == "LF"
    assert entry.is_binary is False


def test_multi_file_bundle_with_embedded_markers_is_exact():
    entries = [
        _entry("tests/conftest.py", NESTED_FIXTURE),
        _entry("src/plain.py", "X = 1\n"),
        _entry("docs/sample.md", "# FILE: not-a-real-boundary.py\ntext\n"),
    ]
    _, manifest = _roundtrip(entries)
    assert len(manifest.entries) == 3
    for source, parsed in zip(entries, manifest.entries):
        assert parsed.path == source.path
        assert parsed.content == source.content


def test_bundle_is_boundary_stamped_and_token_absent_from_content():
    """The token must be present in every META line and absent from every body."""
    text, _ = _roundtrip([_entry("tests/conftest.py", NESTED_FIXTURE)])
    tokens = re.findall(r"^# META:.*\bboundary=([0-9a-f]{32})\b.*$", text, re.MULTILINE)
    assert tokens, "bundle carries no boundary-stamped META line"
    assert len(set(tokens)) == 1, "every block must carry the one active token"
    assert tokens[0] not in NESTED_FIXTURE


def test_legacy_bundle_without_boundary_still_parses():
    """v1.1.5 compatibility: an un-stamped bundle still parses."""
    legacy = (
        _SEP + "\n"
        "# FILE: src/legacy.py\n"
        "# META: encoding=utf-8; eol=LF; mode=text\n"
        + _SEP + "\n"
        "LEGACY = True\n"
    )
    manifest = BundleParser().parse(legacy, profile_name="plain_marker")
    assert [e.path for e in manifest.entries] == ["src/legacy.py"]
    assert manifest.entries[0].content == "LEGACY = True\n"


def test_build102_reader_still_frames_a_build103_bundle():
    """Old-reader / new-bundle compatibility, proven structurally.

    A Build 102 reader recognised the separator and '# FILE:' lines and split
    META on ';' into key=value pairs. The Build 103 writer changes neither, so
    the legacy framing still holds and 'boundary' is just one more unknown
    field. This test asserts that property on the emitted text.
    """
    text, _ = _roundtrip([_entry("src/plain.py", "X = 1\n")])
    lines = text.splitlines()
    assert lines[0] == _SEP
    assert lines[1] == "# FILE: src/plain.py"
    assert lines[2].startswith("# META: encoding=utf-8; eol=LF; mode=text; boundary=")
    assert lines[3] == _SEP
