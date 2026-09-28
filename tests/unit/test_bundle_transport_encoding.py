"""Fail-closed bundle transport decoding and explicit encoding overrides."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from core.exceptions import BundleReadError
from core.models import BundleEntry, BundleManifest
from core.parser import BundleParser
from core.profiles.plain_marker import PlainMarkerProfile
from core.service import BundleToolService


def _plain_text(content: str = "VALUE = 1\n") -> str:
    manifest = BundleManifest(
        entries=[BundleEntry(
            path="src/example.py",
            content=content,
            is_binary=False,
            encoding="utf-8",
            eol_style="LF",
            checksum=None,
        )],
        profile="plain_marker",
    )
    return PlainMarkerProfile().format_manifest(manifest)


@pytest.mark.parametrize("with_progress", [False, True])
def test_cp1252_fails_closed_and_names_offset_and_byte(
        tmp_path: Path, with_progress: bool) -> None:
    bundle = tmp_path / "cp1252.txt"
    bundle.write_bytes(_plain_text("TITLE = 'BFT — safe'\n").encode("cp1252"))

    kwargs = {"progress": lambda event: None} if with_progress else {}
    with pytest.raises(BundleReadError) as caught:
        BundleParser().parse_file(bundle, **kwargs)

    reason = caught.value.reason
    assert "byte offset" in reason
    assert "0x97" in reason
    assert "--encoding cp1252" in reason


def test_explicit_cp1252_override_preserves_payload_across_parser_and_service(
        tmp_path: Path) -> None:
    content = "TITLE = 'BFT — safe'\n"
    bundle = tmp_path / "cp1252.txt"
    bundle.write_bytes(_plain_text(content).encode("cp1252"))

    parsed = BundleParser().parse_file(bundle, encoding="cp1252")
    service = BundleToolService()
    validated = service.validate_bundle(bundle, encoding="cp1252")
    extracted = service.extract_bundle(
        bundle,
        output_dir=tmp_path / "out",
        overwrite_policy="overwrite",
        add_headers=False,
        encoding="cp1252",
    )

    assert parsed.entries[0].content == content
    assert validated.valid is True
    assert validated.file_count == 1
    assert extracted.processed == 1
    assert (tmp_path / "out" / "src" / "example.py").read_text(
        encoding="utf-8") == content


def test_service_default_rejects_cp1252_before_validation(tmp_path: Path) -> None:
    bundle = tmp_path / "cp1252.txt"
    bundle.write_bytes(_plain_text("# BFT — safe\n").encode("cp1252"))

    with pytest.raises(BundleReadError):
        BundleToolService().validate_bundle(bundle)


def test_decode_error_offset_includes_utf8_signature_bytes(tmp_path: Path) -> None:
    bundle = tmp_path / "signed-cp1252.txt"
    raw = b"\xef\xbb\xbf" + _plain_text("# BFT — safe\n").encode("cp1252")
    bundle.write_bytes(raw)

    with pytest.raises(BundleReadError) as caught:
        BundleParser().parse_file(bundle)

    expected_offset = raw.index(bytes([0x97]))
    assert f"byte offset {expected_offset}" in caught.value.reason
    assert "0x97" in caught.value.reason


@pytest.mark.parametrize(
    ("python_encoding", "detected_name", "override"),
    [
        ("utf-16", "UTF-16", "utf-16"),
        ("utf-32", "UTF-32", "utf-32"),
    ],
)
def test_wide_unicode_bom_is_named_and_explicit_override_is_supported(
        tmp_path: Path,
        python_encoding: str,
        detected_name: str,
        override: str) -> None:
    bundle = tmp_path / f"{python_encoding}.txt"
    bundle.write_bytes(_plain_text().encode(python_encoding))

    with pytest.raises(BundleReadError) as caught:
        BundleParser().parse_file(bundle)

    assert detected_name in caught.value.reason
    assert f"--encoding {override}" in caught.value.reason
    parsed = BundleParser().parse_file(bundle, encoding=override)
    assert parsed.entries[0].content == "VALUE = 1\n"


def test_trailing_incomplete_utf8_sequence_fails_closed(tmp_path: Path) -> None:
    bundle = tmp_path / "truncated.txt"
    clean = _plain_text().encode("utf-8")
    bundle.write_bytes(clean + b"\xc3")

    with pytest.raises(BundleReadError) as caught:
        BundleParser().parse_file(bundle)

    assert f"byte offset {len(clean)}" in caught.value.reason
    assert "0xC3" in caught.value.reason


def test_unknown_explicit_encoding_is_a_bundle_read_error(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle.txt"
    bundle.write_bytes(_plain_text().encode("utf-8"))

    with pytest.raises(BundleReadError) as caught:
        BundleParser().parse_file(bundle, encoding="not-an-encoding")

    assert "unknown text encoding 'not-an-encoding'" in caught.value.reason


def test_cli_exposes_encoding_on_validate_and_unbundle() -> None:
    from cli import build_parser

    validate = build_parser().parse_args(
        ["validate", "bundle.txt", "--encoding", "cp1252"])
    unbundle = build_parser().parse_args(
        ["unbundle", "bundle.txt", "--encoding", "latin-1"])

    assert validate.encoding == "cp1252"
    assert unbundle.encoding == "latin-1"


def test_cli_validate_honours_explicit_encoding(
        tmp_path: Path, capsys) -> None:
    from cli import handle_validate

    bundle = tmp_path / "cp1252.txt"
    bundle.write_bytes(_plain_text("# BFT — safe\n").encode("cp1252"))

    handle_validate(SimpleNamespace(
        input_file=bundle,
        profile=None,
        encoding="cp1252",
    ))

    output = capsys.readouterr().out
    assert "Status: ✓ VALID" in output
    assert "File count: 1" in output
