# ============================================================================
# SOURCEFILE: test_bounded_transport.py
# RELPATH: bundle_file_tool_v2/tests/unit/test_bounded_transport.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.103
# LIFECYCLE: Testing
# STATUS: Build 103 - BFT_B103_BOUNDED_TRANSPORT_TESTS
# DESCRIPTION:
#   Paul s7 unit expansion, items 1-22: new-format content preservation,
#   structural corruption, compatibility and determinism. Sequenced AFTER the
#   eight integration tests per George's 2026-08-04 ratification.
# ============================================================================
"""Bounded transport grammar unit tests (Paul s7 items 1-22)."""

import base64
import re

import pytest

from core.exceptions import ProfileParseError
from core.models import BundleEntry, BundleManifest
from core.parser import BundleParser
from core.profiles.plain_marker import PlainMarkerProfile


_SEP = "# " + "=" * 67
FOREIGN_A = "a" * 32
FOREIGN_B = "b" * 32


def _entry(path, content, **kw):
    kw.setdefault("is_binary", False)
    kw.setdefault("encoding", "utf-8")
    kw.setdefault("eol_style", "LF")
    kw.setdefault("checksum", None)
    return BundleEntry(path=path, content=content, **kw)


def _manifest(*entries):
    return BundleManifest(entries=list(entries), profile="plain_marker")


def _format(*entries):
    return PlainMarkerProfile().format_manifest(_manifest(*entries))


def _roundtrip(*entries):
    return PlainMarkerProfile().parse_stream(_format(*entries))


def _active_token(text):
    match = re.search(r"\bboundary=([0-9a-f]{32})\b", text)
    assert match, "no boundary token in bundle"
    return match.group(1)


def _foreign_block(token, path="src/other.py", body="OTHER = 1\n"):
    return (_SEP + "\n"
            f"# FILE: {path}\n"
            f"# META: encoding=utf-8; eol=LF; mode=text; boundary={token}\n"
            + _SEP + "\n" + body)


# ---------------------------------------------------------------------------
# New-format content preservation (items 1-7)
# ---------------------------------------------------------------------------

def test_item1_foreign_token_frame_in_content_is_preserved():
    content = "before\n" + _foreign_block(FOREIGN_A) + "after\n"
    parsed = _roundtrip(_entry("tests/fixture.py", content))
    assert len(parsed.entries) == 1
    assert parsed.entries[0].content == content


def test_item2_multiple_distinct_foreign_tokens_are_preserved():
    content = _foreign_block(FOREIGN_A) + _foreign_block(FOREIGN_B, path="src/two.py")
    parsed = _roundtrip(_entry("tests/fixture.py", content))
    assert [e.path for e in parsed.entries] == ["tests/fixture.py"]
    assert parsed.entries[0].content == content


def test_item3_generic_source_banners_remain_exact():
    content = _SEP + "\n# SOURCEFILE: banner.py\n" + _SEP + "\nBANNER = 1\n"
    parsed = _roundtrip(_entry("src/banner.py", content))
    assert parsed.entries[0].content == content


def test_item4_content_file_and_meta_lines_remain_exact():
    content = ("# FILE: not/a/boundary.py\n"
               "# META: encoding=utf-16; eol=CRLF; mode=binary\n"
               "VALUE = 1\n")
    parsed = _roundtrip(_entry("src/holder.py", content))
    entry = parsed.entries[0]
    assert entry.content == content
    assert entry.encoding == "utf-8" and entry.eol_style == "LF" and not entry.is_binary


def test_item5_binary_content_roundtrips():
    raw = bytes(range(256))
    encoded = base64.b64encode(raw).decode("ascii")
    parsed = _roundtrip(_entry("assets/blob.bin", encoded, is_binary=True,
                               encoding="base64", eol_style="n/a"))
    entry = parsed.entries[0]
    assert entry.is_binary is True
    assert base64.b64decode(entry.content) == raw


def test_item5b_binary_bytes_content_roundtrips():
    raw = b"\x00\x01\x02binary\xff"
    parsed = _roundtrip(_entry("assets/raw.bin", raw, is_binary=True,
                               encoding="base64", eol_style="n/a"))
    assert base64.b64decode(parsed.entries[0].content) == raw


def test_item6_empty_text_file_roundtrips():
    parsed = _roundtrip(_entry("src/empty.py", ""), _entry("src/after.py", "A = 1\n"))
    assert [e.path for e in parsed.entries] == ["src/empty.py", "src/after.py"]
    assert parsed.entries[0].content == ""
    assert parsed.entries[1].content == "A = 1\n"


def test_item7_crlf_metadata_and_content_policy():
    content = "line one\r\nline two\r\n"
    text = _format(_entry("src/crlf.py", content, eol_style="CRLF"))
    parsed = PlainMarkerProfile().parse_stream(text)
    entry = parsed.entries[0]
    assert entry.eol_style == "CRLF"
    assert entry.content == content


# ---------------------------------------------------------------------------
# Structural corruption (items 8-14)
# ---------------------------------------------------------------------------

def test_item8_malformed_first_header_fails_loudly():
    text = _format(_entry("src/a.py", "A = 1\n"))
    damaged = text.replace(_SEP + "\n", "", 1)          # drop the opening separator
    with pytest.raises(ProfileParseError):
        PlainMarkerProfile().parse_stream(damaged)


def test_item9_malformed_closing_separator_fails_loudly():
    text = _format(_entry("src/a.py", "A = 1\n"), _entry("src/b.py", "B = 2\n"))
    lines = text.splitlines(keepends=True)
    # the first block's closing separator is line index 3
    assert lines[3].strip().startswith("#")
    damaged = "".join(lines[:3] + ["# NOT-A-SEPARATOR\n"] + lines[4:])
    with pytest.raises(ProfileParseError):
        PlainMarkerProfile().parse_stream(damaged)


def test_item9b_no_partial_manifest_when_a_later_block_is_damaged():
    """Item 14: valid earlier blocks must not be returned as partial success."""
    text = _format(_entry("src/a.py", "A = 1\n"), _entry("src/b.py", "B = 2\n"))
    token = _active_token(text)
    damaged = text.replace(
        _SEP + "\n# FILE: src/b.py\n", "# FILE: src/b.py\n", 1)
    assert token in damaged
    with pytest.raises(ProfileParseError):
        PlainMarkerProfile().parse_stream(damaged)


def test_item10_foreign_token_block_is_content_not_a_boundary():
    """Ratified semantics: the ACTIVE token is the sole boundary authority.

    Paul's item 10 was written against the withdrawn per-separator nonce
    design. Under the ratified grammar a block bearing a different token is,
    by construction, ordinary content - which is exactly what lets this
    project's own fixtures survive. Its bytes are preserved, not dropped.
    """
    text = _format(_entry("src/a.py", "A = 1\n"))
    injected = text + _foreign_block(FOREIGN_A)
    parsed = PlainMarkerProfile().parse_stream(injected)
    assert [e.path for e in parsed.entries] == ["src/a.py"]
    assert FOREIGN_A in parsed.entries[0].content
    assert "OTHER = 1" in parsed.entries[0].content


def test_item11_missing_meta_line_is_not_a_boundary():
    """Ratified policy: no META means no token means no boundary."""
    text = _format(_entry("src/a.py", "A = 1\n"))
    trailing = _SEP + "\n# FILE: src/ghost.py\n" + _SEP + "\nGHOST = 1\n"
    parsed = PlainMarkerProfile().parse_stream(text + trailing)
    assert [e.path for e in parsed.entries] == ["src/a.py"]
    assert "GHOST = 1" in parsed.entries[0].content


def test_item12_active_token_declared_outside_a_header_fails_loudly():
    text = _format(_entry("src/a.py", "A = 1\n"))
    token = _active_token(text)
    conflicting = text + f"# META: encoding=utf-8; boundary={token}\n"
    with pytest.raises(ProfileParseError):
        PlainMarkerProfile().parse_stream(conflicting)


def test_item13_truncated_tail_below_the_meta_line_is_content():
    """Documented limitation, pinned deliberately.

    Truncation that removes the META line removes the only evidence that a
    block ever existed, so the remaining header text is indistinguishable from
    a fixture and is preserved as content. Truncation that leaves the META line
    intact is caught by item 12. Closing the residual gap needs a bundle-level
    entry count, which is not part of this ratification.
    """
    text = _format(_entry("src/a.py", "A = 1\n"))
    truncated = text + _SEP + "\n# FILE: src/lost.py\n"
    parsed = PlainMarkerProfile().parse_stream(truncated)
    assert [e.path for e in parsed.entries] == ["src/a.py"]
    assert "# FILE: src/lost.py" in parsed.entries[0].content


def test_item14_damaged_bounded_bundle_never_falls_back_to_legacy():
    text = _format(_entry("src/a.py", "A = 1\n"))
    damaged = text.replace("# FILE: src/a.py\n", "", 1)
    with pytest.raises(ProfileParseError):
        PlainMarkerProfile().parse_stream(damaged)


# ---------------------------------------------------------------------------
# Compatibility (items 15-19)
# ---------------------------------------------------------------------------

def test_item15_new_reader_parses_canonical_legacy_bundle():
    legacy = (_SEP + "\n# FILE: src/legacy.py\n"
              "# META: encoding=utf-8; eol=LF; mode=text\n" + _SEP + "\nL = 1\n")
    parsed = PlainMarkerProfile().parse_stream(legacy)
    assert [e.path for e in parsed.entries] == ["src/legacy.py"]
    assert parsed.entries[0].content == "L = 1\n"


def test_item16_legacy_bundle_with_token_looking_content_stays_legacy():
    legacy = (_SEP + "\n# FILE: src/legacy.py\n"
              "# META: encoding=utf-8; eol=LF; mode=text\n" + _SEP + "\n"
              f"TOKEN = '{FOREIGN_A}'\n")
    parsed = PlainMarkerProfile().parse_stream(legacy)
    assert [e.path for e in parsed.entries] == ["src/legacy.py"]
    assert FOREIGN_A in parsed.entries[0].content


def test_item17_old_reader_framing_is_unchanged_by_the_new_writer():
    text = _format(_entry("src/a.py", "A = 1\n"))
    lines = text.splitlines()
    assert lines[0] == _SEP and lines[3] == _SEP
    assert lines[1] == "# FILE: src/a.py"
    # a Build 102 reader split META on ';' into key=value pairs; boundary is
    # simply one more unknown field to it
    fields = dict(re.findall(r"(\w+)\s*=\s*([^;]+)", lines[2].split(":", 1)[1]))
    assert fields["encoding"].strip() == "utf-8"
    assert fields["mode"].strip() == "text"
    assert re.fullmatch(r"[0-9a-f]{32}", fields["boundary"].strip())


def test_item18_legacy_bundle_without_meta_line():
    legacy = _SEP + "\n# FILE: src/nometa.py\n" + _SEP + "\nN = 1\n"
    parsed = PlainMarkerProfile().parse_stream(legacy)
    assert [e.path for e in parsed.entries] == ["src/nometa.py"]
    assert parsed.entries[0].encoding == "utf-8"
    assert parsed.entries[0].eol_style == "LF"


def test_item19_duplicate_path_semantics_last_one_wins():
    text = _format(_entry("src/a.py", "FIRST = 1\n"))
    token = _active_token(text)
    doubled = text + (_SEP + "\n# FILE: src/a.py\n"
                      f"# META: encoding=utf-8; eol=LF; mode=text; boundary={token}\n"
                      + _SEP + "\nSECOND = 2\n")
    parsed = PlainMarkerProfile().parse_stream(doubled)
    assert [e.path for e in parsed.entries] == ["src/a.py"]
    assert parsed.entries[0].content == "SECOND = 2\n"


# ---------------------------------------------------------------------------
# Determinism (items 20-22)
# ---------------------------------------------------------------------------

def test_item20_same_manifest_formats_identically():
    entries = [_entry("src/a.py", "A = 1\n"), _entry("src/b.py", "B = 2\n")]
    first = PlainMarkerProfile().format_manifest(_manifest(*entries))
    second = PlainMarkerProfile().format_manifest(_manifest(*[
        _entry(e.path, e.content) for e in entries]))
    assert first == second


@pytest.mark.parametrize("mutate", [
    lambda e: _entry("src/renamed.py", e.content),
    lambda e: _entry(e.path, e.content + "# changed\n"),
    lambda e: _entry(e.path, e.content, eol_style="CRLF"),
    lambda e: _entry(e.path, e.content, encoding="utf-8-sig"),
])
def test_item21_any_change_changes_the_token(mutate):
    base = _entry("src/a.py", "A = 1\n")
    baseline = _active_token(_format(base))
    mutated = _active_token(_format(mutate(_entry("src/a.py", "A = 1\n"))))
    assert mutated != baseline


def test_item21b_binary_payload_change_changes_the_token():
    first = _active_token(_format(_entry("assets/x.bin", b"\x01\x02", is_binary=True,
                                         encoding="base64", eol_style="n/a")))
    second = _active_token(_format(_entry("assets/x.bin", b"\x01\x03", is_binary=True,
                                          encoding="base64", eol_style="n/a")))
    assert first != second


def test_item22_collision_counter_is_deterministic_and_escapes_the_collision():
    """Force the collision path through the derivation's single seam."""

    class CollidingProfile(PlainMarkerProfile):
        candidates = []

        def _boundary_candidate(self, manifest, payloads, counter):
            token = ("c" * 32) if counter == 0 else ("d" * 32)
            self.candidates.append((counter, token))
            return token

    entry = _entry("src/a.py", "TOKEN = '" + "c" * 32 + "'\n")
    profile = CollidingProfile()
    text = profile.format_manifest(_manifest(entry))

    assert [c for c, _ in profile.candidates] == [0, 1]      # counter advanced
    assert _active_token(text) == "d" * 32                   # collision escaped

    parsed = profile.parse_stream(text)
    assert parsed.entries[0].content == entry.content        # colliding text kept


def test_derivation_gives_up_loudly_rather_than_emitting_a_colliding_token():
    from core.exceptions import ProfileFormatError

    class AlwaysCollidingProfile(PlainMarkerProfile):
        def _boundary_candidate(self, manifest, payloads, counter):
            return "e" * 32

    entry = _entry("src/a.py", "TOKEN = '" + "e" * 32 + "'\n")
    with pytest.raises(ProfileFormatError):
        AlwaysCollidingProfile().format_manifest(_manifest(entry))


def test_parser_dispatch_reports_the_transport_in_manifest_metadata():
    text = _format(_entry("src/a.py", "A = 1\n"))
    parsed = BundleParser().parse(text, profile_name="plain_marker")
    assert parsed.metadata["transport"] == "bounded"
    assert parsed.metadata["boundary"] == _active_token(text)
