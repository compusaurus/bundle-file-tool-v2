"""UTF-8 BOM handling at the shared bundle ingress boundary.

The bounded plain-marker grammar correctly rejects a malformed first frame.
A UTF-8 signature decoded as U+FEFF used to make a valid separator look
malformed before that grammar ran.  These tests pin the boundary correction
without relaxing profile regexes or consuming BOMs inside file payloads.
"""

from pathlib import Path
from types import SimpleNamespace

from core.models import BundleEntry, BundleManifest
from core.parser import BundleParser
from core.profiles.markdown_fence import MarkdownFenceProfile
from core.profiles.plain_marker import PlainMarkerProfile


def _entry(path: str, content: str) -> BundleEntry:
    return BundleEntry(
        path=path,
        content=content,
        is_binary=False,
        encoding="utf-8",
        eol_style="LF",
        checksum=None,
    )


def _plain_text(content: str = "VALUE = 1\n") -> str:
    manifest = BundleManifest(
        entries=[_entry("src/example.py", content)],
        profile="plain_marker",
    )
    return PlainMarkerProfile().format_manifest(manifest)


def _markdown_text() -> str:
    manifest = BundleManifest(
        entries=[_entry("docs/example.txt", "hello\n")],
        profile="md_fence",
    )
    return MarkdownFenceProfile().format_manifest(manifest)


def _write_with_transport_bom(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8-sig", newline="")


def test_bounded_plain_marker_file_accepts_utf8_bom_with_both_read_paths(
        tmp_path: Path) -> None:
    """Normal and progress-reporting reads must strip the same outer BOM."""
    bundle = tmp_path / "bounded-bom.txt"
    _write_with_transport_bom(bundle, _plain_text())
    assert bundle.read_bytes().startswith(b"\xef\xbb\xbf")

    parser = BundleParser()
    direct = parser.parse_file(bundle)
    events = []
    observed = parser.parse_file(bundle, progress=events.append)

    assert direct.profile == observed.profile == "plain_marker"
    assert [entry.path for entry in direct.entries] == ["src/example.py"]
    assert [entry.content for entry in observed.entries] == ["VALUE = 1\n"]
    assert events, "progress-reporting ingress did not report any work"


def test_markdown_fence_file_accepts_utf8_bom(tmp_path: Path) -> None:
    """BOM handling belongs above profiles and therefore covers md_fence too."""
    bundle = tmp_path / "markdown-bom.txt"
    _write_with_transport_bom(bundle, _markdown_text())

    parsed = BundleParser().parse_file(bundle)

    assert parsed.profile == "md_fence"
    assert [entry.path for entry in parsed.entries] == ["docs/example.txt"]
    assert parsed.entries[0].content == "hello\n"


def test_public_string_parse_detection_and_validation_accept_leading_bom() -> None:
    """Already-decoded callers get the same ingress semantics as file callers."""
    text = "\ufeff" + _plain_text()
    parser = BundleParser()

    parsed = parser.parse(text)
    report = parser.validate_bundle(text)

    assert parser.detect_profile_name(text) == "plain_marker"
    assert [entry.path for entry in parsed.entries] == ["src/example.py"]
    assert report["valid"] is True
    assert report["profile"] == "plain_marker"
    assert report["file_count"] == 1


def test_cli_validate_surface_accepts_utf8_bom(tmp_path: Path, capsys) -> None:
    """The CLI enters the same strict byte boundary as every file surface."""
    from cli import handle_validate

    bundle = tmp_path / "cli-bom.txt"
    _write_with_transport_bom(bundle, _plain_text())

    handle_validate(SimpleNamespace(input_file=bundle, profile=None))

    output = capsys.readouterr().out
    assert "Status: ✓ VALID" in output
    assert "File count: 1" in output


def test_service_validate_surface_accepts_utf8_bom(tmp_path: Path) -> None:
    """The shared service receives the same normalized parser semantics."""
    from core.service import BundleToolService

    bundle = tmp_path / "service-bom.txt"
    _write_with_transport_bom(bundle, _plain_text())

    result = BundleToolService().validate_bundle(bundle)

    assert result.valid is True
    assert result.profile == "plain_marker"
    assert result.file_count == 1


def test_only_transport_bom_is_removed_payload_bom_is_preserved(
        tmp_path: Path) -> None:
    """A BOM at the start of the first bundled file remains payload data."""
    payload = "\ufeff<!doctype html>\n"
    bundle = tmp_path / "outer-and-payload-bom.txt"
    _write_with_transport_bom(bundle, _plain_text(payload))

    parsed = BundleParser().parse_file(bundle)

    assert parsed.entries[0].content == payload
    assert parsed.entries[0].content.startswith("\ufeff")


def test_bom_free_bundle_behavior_is_unchanged(tmp_path: Path) -> None:
    bundle = tmp_path / "ordinary.txt"
    text = _plain_text("NO_BOM = True\n")
    bundle.write_text(text, encoding="utf-8", newline="")

    parsed_from_file = BundleParser().parse_file(bundle)
    parsed_from_text = BundleParser().parse(text)

    assert parsed_from_file.entries == parsed_from_text.entries
    assert parsed_from_file.entries[0].content == "NO_BOM = True\n"
