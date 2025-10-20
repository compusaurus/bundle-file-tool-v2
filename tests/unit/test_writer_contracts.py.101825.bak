from pathlib import Path
import pytest
from core.writer import BundleWriter, OverwritePolicy
from core.models import BundleEntry, BundleManifest
from core.exceptions import OverwriteError, BundleWriteError

def test_prompt_policy_raises(tmp_path: Path):
    target = tmp_path / "file.txt"
    target.write_text("original", encoding="utf-8")
    writer = BundleWriter(base_path=tmp_path, overwrite_policy=OverwritePolicy.PROMPT, add_headers=False)
    entry = BundleEntry(path="file.txt", content="new", is_binary=False, encoding="utf-8", eol_style="LF")
    with pytest.raises(OverwriteError):
        writer.write_entry(entry)

def test_utf8_bom_mapping(tmp_path: Path):
    writer = BundleWriter(base_path=tmp_path, overwrite_policy=OverwritePolicy.OVERWRITE, add_headers=False)
    entry = BundleEntry(path="bom.txt", content="x", is_binary=False, encoding="utf-8-bom", eol_style="LF")
    status, p = writer.write_entry(entry)
    assert status == "processed"
    data = Path(p).read_bytes()
    assert data.startswith(b"\xef\xbb\xbf")

def test_verbatim_newlines(tmp_path: Path):
    writer = BundleWriter(base_path=tmp_path, overwrite_policy=OverwritePolicy.OVERWRITE, add_headers=False)
    text = "a\r\nb\nc\rd"
    entry = BundleEntry(path="mix.txt", content=text, is_binary=False, encoding="utf-8", eol_style="MIXED")
    writer.write_entry(entry)
    assert (tmp_path / "mix.txt").read_bytes() == text.encode("utf-8")

def test_bundlewriteerror_signature(tmp_path: Path):
    writer = BundleWriter(base_path=tmp_path, overwrite_policy=OverwritePolicy.OVERWRITE, add_headers=False)
    bad = BundleEntry(path="bin.dat", content="!!not_base64!!", is_binary=True, encoding="base64", eol_style="n/a")
    with pytest.raises(BundleWriteError) as ei:
        writer.write_entry(bad)
    # tuple args: (path, reason)
    assert len(ei.value.args) == 2
    assert "Base64 decode failed" in ei.value.args[1]
