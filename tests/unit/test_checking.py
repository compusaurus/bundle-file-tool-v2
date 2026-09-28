"""Build 125 structured integrity-checking contract."""

from pathlib import Path

import pytest

from core.checking import (
    SUBJECT_BUNDLE,
    SUBJECT_SELECTION,
    check_manifest,
)
from core.exceptions import ValidationError
from core.models import BundleEntry, BundleManifest
from core.parser import ProfileRegistry
from core.progress import OP_CHECK, PHASE_INTEGRITY, PHASE_VERIFY
from core.service import BundleToolService


SEP = "# " + "=" * 70


def manifest(entries):
    return BundleManifest(entries=list(entries), profile="plain_marker")


def nested_text():
    return (
        f"{SEP}\n# FILE: src/a.py\n"
        "# META: encoding=utf-8; eol=LF; mode=text\n"
        f"{SEP}\nA = 1\n"
        f"{SEP}\n# FILE: src/b.py\n"
        "# META: encoding=utf-8; eol=LF; mode=text\n"
        f"{SEP}\nB = 2\n"
    )


def test_clean_manifest_is_ready_and_serializable():
    result = check_manifest(manifest([
        BundleEntry("src/app.py", "print('ok')", file_size_bytes=11),
    ]), label="clean.txt")

    assert result.valid is True
    assert result.status == "passed"
    assert result.total_bytes == 11
    assert result.to_dict()["schema"] == "bft.check-result.v1"
    assert result.to_dict()["findings"] == []


def test_check_progress_moves_to_a_visible_verification_phase():
    events = []
    check_manifest(
        manifest([BundleEntry("src/app.py", "print('ok')")]),
        progress=events.append,
    )

    assert {event.operation for event in events} == {OP_CHECK}
    phases = [event.phase for event in events]
    assert PHASE_INTEGRITY in phases
    assert PHASE_VERIFY in phases
    verification = [event for event in events if event.phase == PHASE_VERIFY]
    assert verification[-1].current == verification[-1].total == 1


def test_nested_content_is_an_actionable_blocker():
    result = check_manifest(manifest([
        BundleEntry("demo.txt", nested_text()),
    ]), subject=SUBJECT_SELECTION, generation=7)

    assert result.valid is False
    assert result.status == "blocked"
    assert result.generation == 7
    finding = result.blockers[0]
    assert finding.code == "NESTED_BUNDLE_CONTENT"
    assert finding.path == "demo.txt"
    assert "Exclude" in finding.remediation


def test_bundle_artifact_name_is_a_path_blocker():
    result = check_manifest(manifest([
        BundleEntry("docs/archive/old_code_bundle.txt", "ordinary text"),
    ]))

    assert [item.code for item in result.blockers] == ["NESTED_BUNDLE_PATH"]


def test_stale_self_header_is_a_warning_not_a_blocker():
    body = (
        f"{SEP}\n# FILE: source.py\n"
        "# META: encoding=utf-8; eol=LF; mode=text\n"
        f"{SEP}\nprint('source')\n"
    )
    result = check_manifest(manifest([BundleEntry("src/source.py", body)]))

    assert result.valid is True
    assert result.status == "warnings"
    assert result.warnings[0].code == "STALE_TRANSPORT_HEADER"


@pytest.mark.parametrize("path", ["../escape.py", "/rooted.py", "C:/drive.py"])
def test_unsafe_transport_paths_are_blocked(path):
    result = check_manifest(manifest([BundleEntry(path, "x")]))

    assert "UNSAFE_TRANSPORT_PATH" in {
        item.code for item in result.blockers
    }


def test_portable_case_collision_is_blocked():
    result = check_manifest(manifest([
        BundleEntry("src/App.py", "A"),
        BundleEntry("src/app.py", "B"),
    ]))

    assert "PORTABLE_PATH_COLLISION" in {
        item.code for item in result.blockers
    }


def test_checksum_mismatch_is_blocked():
    result = check_manifest(manifest([
        BundleEntry("a.txt", "actual", checksum="0" * 64),
    ]))

    assert "CHECKSUM_MISMATCH" in {item.code for item in result.blockers}


def test_service_checks_a_selection_without_writing(tmp_path):
    (tmp_path / "demo.txt").write_text(nested_text(), encoding="utf-8")
    service = BundleToolService()
    plan = service.plan_bundle([tmp_path], preset=[])

    result = service.check_selection(plan)

    assert result.subject == SUBJECT_SELECTION
    assert result.valid is False
    assert result.blockers[0].path == "demo.txt"
    assert list(tmp_path.glob("*_bundle.txt")) == []


def test_selection_check_uses_one_operation_identity(tmp_path):
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    service = BundleToolService()
    plan = service.plan_bundle([tmp_path], preset=[])
    events = []

    service.check_selection(plan, progress=events.append)

    assert events
    assert {event.operation for event in events} == {OP_CHECK}


def test_service_loads_and_checks_an_existing_bundle_once(tmp_path):
    outer = manifest([BundleEntry("demo.txt", nested_text())])
    text = ProfileRegistry().get("plain_marker").format_manifest(outer)
    bundle = tmp_path / "outer.txt"
    bundle.write_text(text, encoding="utf-8")

    loaded = BundleToolService().load_checked_bundle(bundle)

    assert loaded.manifest.get_file_count() == 1
    assert loaded.check.subject == SUBJECT_BUNDLE
    assert loaded.check.valid is False


def test_shared_extraction_service_cannot_bypass_a_blocker(tmp_path):
    outer = manifest([BundleEntry("demo.txt", nested_text())])
    text = ProfileRegistry().get("plain_marker").format_manifest(outer)

    with pytest.raises(ValidationError, match="Integrity check blocked"):
        BundleToolService().extract_bundle(text, tmp_path / "out")

    assert not (tmp_path / "out").exists()
