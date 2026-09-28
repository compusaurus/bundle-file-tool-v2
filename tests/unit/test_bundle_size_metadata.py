"""Bundle size metadata survives both shipped transport profiles."""

from __future__ import annotations

import pytest

from core.models import BundleEntry, BundleManifest
from core.profiles.markdown_fence import MarkdownFenceProfile
from core.profiles.plain_marker import PlainMarkerProfile


@pytest.mark.parametrize(
    "profile",
    [PlainMarkerProfile(), MarkdownFenceProfile()],
    ids=["plain-marker", "markdown-fence"],
)
@pytest.mark.parametrize("size", [0, 12_345])
def test_file_size_round_trips_through_the_transport(profile, size):
    entry = BundleEntry(
        path="src/data.bin",
        content="YWJj",
        is_binary=True,
        encoding="base64",
        eol_style="n/a",
        file_size_bytes=size,
    )
    manifest = BundleManifest(entries=[entry], profile=profile.profile_name)

    formatted = profile.format_manifest(manifest)
    reparsed = profile.parse_stream(formatted)

    assert f"size={size}" in formatted
    assert reparsed.entries[0].file_size_bytes == size


@pytest.mark.parametrize(
    "profile,text",
    [
        (
            PlainMarkerProfile(),
            """# ===================================================================
# FILE: old.txt
# META: encoding=utf-8; eol=LF; mode=text
# ===================================================================
legacy
""",
        ),
        (
            MarkdownFenceProfile(),
            """<!-- FILE: old.txt; encoding=utf-8; eol=LF; mode=text -->
```
legacy
```""",
        ),
    ],
    ids=["plain-marker", "markdown-fence"],
)
def test_legacy_bundles_without_size_metadata_still_parse(profile, text):
    manifest = profile.parse_stream(text)
    assert manifest.entries[0].file_size_bytes is None
