"""Byte-fidelity coverage for the source-read side of bundle creation."""

from __future__ import annotations

import base64

import pytest

from core.exceptions import BundleWriteError
from core.parser import BundleParser
from core.profiles.plain_marker import PlainMarkerProfile
from core.writer import BundleCreator, BundleWriter


@pytest.mark.parametrize(
    ("payload", "expected_eol"),
    [
        (b"one\r\ntwo\r\n", "CRLF"),
        (b"one\rtwo\r", "CR"),
        (b"one\r\ntwo\nthree\r", "MIXED"),
        (b"one\ntwo\n", "LF"),
        (b"", "LF"),
        (b"x", "LF"),
    ],
)
def test_real_utf8_source_bytes_reach_the_entry_unchanged(
    tmp_path,
    payload,
    expected_eol,
):
    source = tmp_path / "source.txt"
    source.write_bytes(payload)

    entry = BundleCreator()._read_file_to_entry(source, source.name)

    assert entry.is_binary is False
    assert entry.eol_style == expected_eol
    assert entry.content.encode("utf-8") == payload


@pytest.mark.parametrize(
    "original",
    [
        b"one\r\ntwo\r\n",
        b"one\rtwo\r",
        b"one\r\ntwo\nthree\r",
        b"one\ntwo\n",
        b"",
        b"x",
    ],
)
def test_text_survives_disk_bundle_parse_and_extraction_byte_for_byte(
    tmp_path,
    original,
):
    source_root = tmp_path / "source"
    source_root.mkdir()
    source = source_root / "crlf.txt"
    source.write_bytes(original)

    creator = BundleCreator(allow_globs=["**/*"], deny_globs=[])
    manifest = creator.create_manifest(
        creator.discover_files(source_root),
        source_root,
        "plain_marker",
    )
    bundle = PlainMarkerProfile().format_manifest(manifest)
    bundle_path = tmp_path / "bundle.txt"
    bundle_path.write_bytes(bundle.encode("utf-8"))
    parsed = BundleParser().parse_file(bundle_path, profile_name="plain_marker")
    output = tmp_path / "output"
    BundleWriter(base_path=output, add_headers=False).extract_manifest(parsed, output)

    assert (output / "crlf.txt").read_bytes() == original


def test_non_utf8_byte_after_the_old_sniff_window_is_lossless_binary(tmp_path):
    source = tmp_path / "late-ansi.txt"
    original = b"A" * 2000 + b"cost \x97 five"
    source.write_bytes(original)

    entry = BundleCreator()._read_file_to_entry(source, source.name)

    assert entry.is_binary is True
    assert entry.encoding == "base64"
    assert base64.b64decode(entry.content) == original


def test_non_utf8_source_fails_closed_when_binary_handling_is_disabled(tmp_path):
    source = tmp_path / "late-ansi.txt"
    source.write_bytes(b"A" * 2000 + b"cost \x97 five")

    with pytest.raises(BundleWriteError, match="binary handling is disabled"):
        BundleCreator(treat_binary_as_base64=False)._read_file_to_entry(
            source,
            source.name,
        )


def test_utf8_code_point_straddling_old_sniff_boundary_stays_text(tmp_path):
    source = tmp_path / "boundary.txt"
    original = b"A" * 1023 + "é\n".encode()
    source.write_bytes(original)

    entry = BundleCreator()._read_file_to_entry(source, source.name)

    assert entry.is_binary is False
    assert entry.encoding == "utf-8"
    assert entry.content.encode("utf-8") == original
