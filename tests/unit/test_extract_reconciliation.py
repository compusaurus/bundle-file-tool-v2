# ============================================================================
# SOURCEFILE: test_extract_reconciliation.py
# RELPATH: bundle_file_tool_v2/tests/unit/test_extract_reconciliation.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.103
# LIFECYCLE: Testing
# STATUS: Build 103 - BFT_B103_EXTRACT_RECONCILIATION_TESTS
# DESCRIPTION:
#   Ratified item 6 (George, 2026-08-04): the extract path reconciles the
#   manifest entry count at runtime and halts on a mismatch instead of
#   reporting a partial extraction as complete.
# ============================================================================
"""Entry-count reconciliation tests for the extract path."""

import pytest

from core.exceptions import ValidationError
from core.models import BundleEntry, BundleManifest
from core.writer import BundleWriter


def _entry(path, content="X = 1\n"):
    return BundleEntry(path=path, content=content, is_binary=False,
                       encoding="utf-8", eol_style="LF", checksum=None)


def _manifest(*paths):
    return BundleManifest(entries=[_entry(p) for p in paths], profile="plain_marker")


def test_clean_extraction_reconciles(tmp_path):
    manifest = _manifest("a.py", "pkg/b.py", "pkg/deep/c.py")
    writer = BundleWriter(output_dir=tmp_path, overwrite_policy="overwrite",
                          add_headers=False)

    stats = writer.extract_manifest(manifest, tmp_path)

    assert stats["processed"] == 3
    assert stats["processed"] + stats["skipped"] + stats["errors"] == 3
    assert len(writer.files_written) == 3


def test_dry_run_reconciles(tmp_path):
    manifest = _manifest("a.py", "b.py")
    writer = BundleWriter(output_dir=tmp_path, overwrite_policy="overwrite",
                          dry_run=True, add_headers=False)

    stats = writer.extract_manifest(manifest, tmp_path)

    assert stats["processed"] == 2
    assert not (tmp_path / "a.py").exists()


def test_skipped_entries_are_still_accounted_for(tmp_path):
    (tmp_path / "a.py").write_text("existing", encoding="utf-8")
    manifest = _manifest("a.py", "b.py")
    writer = BundleWriter(output_dir=tmp_path, overwrite_policy="skip",
                          add_headers=False)

    stats = writer.extract_manifest(manifest, tmp_path)

    assert stats["skipped"] == 1
    assert stats["processed"] == 1
    assert stats["processed"] + stats["skipped"] + stats["errors"] == 2


def test_empty_manifest_reconciles(tmp_path):
    manifest = BundleManifest(entries=[], profile="plain_marker")
    writer = BundleWriter(output_dir=tmp_path, add_headers=False)

    assert writer.extract_manifest(manifest, tmp_path) == {
        "processed": 0, "skipped": 0, "errors": 0}


def test_unaccounted_entry_halts_extraction(tmp_path, monkeypatch):
    """The failure class this guard exists for: an entry that leaves through
    no outcome at all would previously return a short, 'successful' stats dict.
    """
    manifest = _manifest("a.py", "b.py", "c.py")
    writer = BundleWriter(output_dir=tmp_path, overwrite_policy="overwrite",
                          add_headers=False)
    real_write_entry = writer.write_entry

    def dropping_write_entry(entry, output_path=None, *, apply_headers=None):
        if entry.path == "b.py":
            return ("ignored", str(output_path))      # accounted for by nothing
        return real_write_entry(entry, output_path, apply_headers=apply_headers)

    monkeypatch.setattr(writer, "write_entry", dropping_write_entry)

    with pytest.raises(ValidationError) as excinfo:
        writer.extract_manifest(manifest, tmp_path)

    message = str(excinfo.value)
    assert "reconciliation FAILED" in message
    assert "declares 3 entries" in message


def test_counter_without_a_write_ledger_entry_halts_extraction(tmp_path, monkeypatch):
    manifest = _manifest("a.py", "b.py")
    writer = BundleWriter(output_dir=tmp_path, overwrite_policy="overwrite",
                          add_headers=False)

    def phantom_write_entry(entry, output_path=None, *, apply_headers=None):
        return ("processed", str(output_path))        # never touches the ledger

    monkeypatch.setattr(writer, "write_entry", phantom_write_entry)

    with pytest.raises(ValidationError) as excinfo:
        writer.extract_manifest(manifest, tmp_path)

    assert "write ledgers" in str(excinfo.value)


def test_entry_errors_are_accounted_for_and_do_not_halt(tmp_path, monkeypatch):
    from core.exceptions import BundleWriteError

    manifest = _manifest("a.py", "b.py")
    writer = BundleWriter(output_dir=tmp_path, overwrite_policy="overwrite",
                          add_headers=False)
    real_write_entry = writer.write_entry

    def failing_write_entry(entry, output_path=None, *, apply_headers=None):
        if entry.path == "b.py":
            raise BundleWriteError(str(output_path), "simulated filesystem failure")
        return real_write_entry(entry, output_path, apply_headers=apply_headers)

    monkeypatch.setattr(writer, "write_entry", failing_write_entry)

    stats = writer.extract_manifest(manifest, tmp_path)

    assert stats == {"processed": 1, "skipped": 0, "errors": 1}
