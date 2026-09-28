"""Producer tags travel in transport metadata and never alter source files."""

import pytest

from core.exceptions import ProfileParseError
from core.models import BundleEntry, BundleManifest
from core.profiles.markdown_fence import MarkdownFenceProfile
from core.profiles.plain_marker import PlainMarkerProfile
from core.version import __version__


@pytest.mark.parametrize("profile", [PlainMarkerProfile(), MarkdownFenceProfile()])
def test_build_tag_is_readable_deterministic_and_outside_payload(profile):
    original = "hello café\r\nworld"
    manifest = BundleManifest(
        [BundleEntry(path="example.py", content=original, eol_style="MIXED",
                     file_size_bytes=len(original.encode()))], profile.profile_name)
    bundle = profile.format_manifest(manifest)
    assert f"bft_version={__version__}" in bundle
    assert profile.format_manifest(manifest) == bundle
    recovered = profile.parse_stream(bundle)
    assert recovered.metadata["bft_versions"] == [__version__]
    assert recovered.entries[0].content == original
    older = bundle.replace(f"; bft_version={__version__}", "")
    assert profile.parse_stream(older).metadata["bft_versions"] == []


@pytest.mark.parametrize("tag", [True, False])
def test_short_payload_reports_entry_sizes_and_known_producer(tag):
    profile = PlainMarkerProfile()
    manifest = BundleManifest(
        [BundleEntry(path="src/report.py", content="payload\n", file_size_bytes=8)],
        profile.profile_name)
    bundle = profile.format_manifest(manifest).replace("size=8", "size=99")
    if not tag:
        bundle = bundle.replace(f"; bft_version={__version__}", "")
    with pytest.raises(ProfileParseError) as caught:
        profile.parse_stream(bundle)
    assert "src/report.py" in str(caught.value)
    assert "declared 99, available 8 bytes" in str(caught.value)
    assert (f"BFT {__version__}" if tag else "producer build not recorded") in str(caught.value)


def test_legacy_bundle_without_tag_still_parses():
    bundle = "# FILE: original.txt\n# META: encoding=utf-8; eol=LF; mode=text\nhello\n"
    recovered = PlainMarkerProfile().parse_stream(bundle)
    assert recovered.entries[0].path == "original.txt"
    assert not recovered.metadata.get("bft_versions")
