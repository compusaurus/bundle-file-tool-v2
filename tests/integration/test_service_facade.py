# BFT_B106_SERVICE_FACADE_TESTS
# ============================================================================
# SOURCEFILE: test_service_facade.py
# RELPATH: bundle_file_tool_v2/tests/integration/test_service_facade.py
# PROJECT: Bundle File Tool v2.1
# VERSION: 2.1.106
# LIFECYCLE: Testing
# STATUS: Build 106 - BFT_B106_SERVICE_FACADE_TESTS
# ============================================================================
"""WP2: the shared service beneath every interface.

Paul recorded WP2 as not started - the CLI constructs the parser, writer,
creator and registry directly, so each interface re-derives the same
orchestration and any two can drift. These tests exercise the facade end to end
so it is a proven component rather than a speculative one.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest

from core.exceptions import ValidationError
from core.progress import (
    OP_BUNDLE,
    OP_EXTRACT,
    PHASE_COMPLETE,
    PHASE_DISCOVER,
    PHASE_FINALIZE,
    PHASE_FORMAT,
    PHASE_INTEGRITY,
    PHASE_PLAN,
    PHASE_READ,
    PHASE_VERIFY,
    PHASE_VERIFY_READ,
    PHASE_VERIFY_SOURCE,
    PHASE_WRITE,
    ProgressRecorder,
)
from core.service import BundleResult, BundleToolService, ExtractResult, ValidationResult


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "proj"
    (root / "pkg").mkdir(parents=True)
    (root / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "pkg" / "util.py").write_text("def f():\n    return 2\n", encoding="utf-8")
    (root / "notes.log").write_text("noise\n", encoding="utf-8")
    return root


@pytest.fixture
def service():
    return BundleToolService()


# ---------------------------------------------------------------------------
# Round trip through the facade alone
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("profile", ["plain_marker", "md_fence"])
def test_bundle_extract_round_trip(service, project, tmp_path, profile):
    result = service.create_bundle(
        sources=[project], base_path=project, profile=profile, include=["**/*.py"])

    assert isinstance(result, BundleResult)
    assert result.file_count == 2
    assert result.profile == profile

    out = tmp_path / "extracted"
    extracted = service.extract_bundle(
        result.text, output_dir=out, profile=profile,
        overwrite_policy="overwrite", add_headers=False)

    assert isinstance(extracted, ExtractResult)
    assert extracted.processed == 2
    assert extracted.errors == 0
    assert (out / "app.py").read_text(encoding="utf-8") == "VALUE = 1\n"


def test_validate_through_the_facade(service, project):
    result = service.create_bundle(
        sources=[project], base_path=project, profile="plain_marker", include=["**/*.py"])
    report = service.validate_bundle(result.text, profile="plain_marker")

    assert isinstance(report, ValidationResult)
    assert report.valid is True
    assert report.file_count == 2
    assert report.errors == []


def test_include_and_exclude_are_honoured(service, project):
    result = service.create_bundle(
        sources=[project], base_path=project, profile="plain_marker",
        include=["**/*.py"], exclude=["**/*.log"])
    paths = {e.path for e in result.manifest.entries}
    assert paths == {"app.py", "pkg/util.py"}


def test_unplanned_service_bundle_still_uses_the_canonical_detector(
        service, project):
    """P0: facade convenience calls must not revive legacy discovery."""
    env = project / ".venv312"
    (env / "Scripts").mkdir(parents=True)
    (env / "pyvenv.cfg").write_text("home = C:\\Python\n", encoding="utf-8")
    (env / "Scripts" / "python.exe").write_bytes(b"MZ")
    (env / "secret.py").write_text("TOKEN = 'do-not-bundle'\n", encoding="utf-8")

    result = service.create_bundle(
        sources=[project], base_path=project, profile="plain_marker",
        include=["**/*"])

    paths = {entry.path.replace("\\", "/") for entry in result.manifest.entries}
    assert "app.py" in paths
    assert not any(path.startswith(".venv312/") for path in paths)


def test_writing_to_a_file_records_the_path(service, project, tmp_path):
    target = tmp_path / "out" / "bundle.txt"
    result = service.create_bundle(
        sources=[project], base_path=project, profile="plain_marker",
        include=["**/*.py"], output_path=target)
    assert result.output_path == target
    assert target.read_bytes() == result.text.encode("utf-8")


def test_large_no_output_result_is_a_streamable_temporary_artifact(
        service, project, monkeypatch):
    """Force the bounded path without allocating an actually huge fixture."""
    import core.service as service_module

    monkeypatch.setattr(service_module, "_INLINE_RESULT_LIMIT", 1)
    result = service.create_bundle(
        sources=[project], base_path=project, profile="plain_marker",
        include=["**/*.py"])
    artifact = result.artifact_path
    try:
        assert result.text == ""
        assert result.temporary_artifact is True
        assert artifact is not None and artifact.is_file()
        payload = BytesIO()
        assert result.write_to(payload) == result.byte_count
        assert payload.getvalue().decode("utf-8") == result.read_text()
    finally:
        result.cleanup()
    assert artifact is not None and not artifact.exists()


def test_large_published_result_stays_file_backed(
        service, project, tmp_path, monkeypatch):
    import core.service as service_module

    monkeypatch.setattr(service_module, "_INLINE_RESULT_LIMIT", 1)
    target = tmp_path / "out" / "large.txt"
    result = service.create_bundle(
        sources=[project], base_path=project, profile="plain_marker",
        include=["**/*.py"], output_path=target)

    assert result.text == ""
    assert result.artifact_path == target
    assert result.temporary_artifact is False
    assert result.byte_count == target.stat().st_size
    assert result.read_text().encode("utf-8") == target.read_bytes()


def test_complete_is_emitted_only_after_atomic_publication(
        service, project, tmp_path, monkeypatch):
    import core.service as service_module

    recorder = ProgressRecorder()
    target = tmp_path / "published.txt"
    replaced = []
    real_replace = service_module.os.replace

    def observed_replace(source, destination):
        assert PHASE_COMPLETE not in recorder.phases()
        replaced.append((Path(source), Path(destination)))
        return real_replace(source, destination)

    monkeypatch.setattr(service_module.os, "replace", observed_replace)
    service.create_bundle(
        sources=[project], base_path=project, profile="plain_marker",
        include=["**/*.py"], output_path=target, progress=recorder)

    assert replaced and replaced[-1][1] == target
    assert recorder.events[-1].phase == PHASE_COMPLETE


# ---------------------------------------------------------------------------
# The safety gates live in the service, not the adapters
# ---------------------------------------------------------------------------

def test_integrity_gate_runs_inside_the_service(service, tmp_path):
    """An adapter must not be able to skip the nested-bundle refusal."""
    root = tmp_path / "contaminated"
    root.mkdir()
    sep = "# " + "=" * 67
    (root / "old_bundle.txt").write_text(
        sep + "\n# FILE: core/x.py\n# META: encoding=utf-8; eol=LF; mode=text\n"
        + sep + "\nx = 1\n", encoding="utf-8")

    target = tmp_path / "should_not_exist.txt"
    with pytest.raises(ValidationError):
        service.create_bundle(sources=[root], base_path=root,
                              profile="plain_marker", include=["**/*.txt"],
                              output_path=target)
    assert not target.exists(), "the gate must fail before anything is written"


def test_extract_reconciliation_still_applies(service, project, tmp_path):
    result = service.create_bundle(
        sources=[project], base_path=project, profile="plain_marker", include=["**/*.py"])
    extracted = service.extract_bundle(
        result.text, output_dir=tmp_path / "out", overwrite_policy="overwrite")
    assert extracted.total == result.file_count


def test_dry_run_writes_nothing(service, project, tmp_path):
    result = service.create_bundle(
        sources=[project], base_path=project, profile="plain_marker", include=["**/*.py"])
    out = tmp_path / "dry"
    extracted = service.extract_bundle(result.text, output_dir=out,
                                       overwrite_policy="overwrite", dry_run=True)
    assert extracted.processed == 2
    assert not (out / "app.py").exists()


# ---------------------------------------------------------------------------
# Progress reaches the caller
# ---------------------------------------------------------------------------

def test_bundle_emits_the_full_phase_sequence(service, project):
    recorder = ProgressRecorder()
    service.create_bundle(sources=[project], base_path=project,
                          profile="plain_marker", include=["**/*.py"], progress=recorder)

    assert recorder.phases() == [
        PHASE_DISCOVER,
        PHASE_PLAN,
        PHASE_VERIFY,
        PHASE_VERIFY_SOURCE,
        PHASE_READ,
        PHASE_VERIFY_READ,
        PHASE_INTEGRITY,
        PHASE_FORMAT,
        PHASE_WRITE,
        PHASE_FINALIZE,
        PHASE_COMPLETE,
    ]
    assert all(e.operation == OP_BUNDLE for e in recorder.events)

    completion = recorder.last_for(PHASE_COMPLETE)
    assert completion.current == 2 and completion.total == 2


def test_extract_emits_progress(service, project, tmp_path):
    result = service.create_bundle(sources=[project], base_path=project,
                                   profile="plain_marker", include=["**/*.py"])
    recorder = ProgressRecorder()
    service.extract_bundle(result.text, output_dir=tmp_path / "out",
                           overwrite_policy="overwrite", progress=recorder)

    assert all(e.operation == OP_EXTRACT for e in recorder.events)
    assert PHASE_COMPLETE in recorder.phases()


def test_discovery_progress_is_indeterminate_then_determinate(service, project):
    """The handoff therm's promote() consumes.

    Canonical planning indexes excluded files as well so their reason chains
    remain explainable.  Discovery progress therefore reports files scanned,
    not only the two Python files eventually emitted.
    """
    recorder = ProgressRecorder()
    service.create_bundle(sources=[project], base_path=project,
                          profile="plain_marker", include=["**/*.py"], progress=recorder)

    discovery = [e for e in recorder.events if e.phase == PHASE_DISCOVER]
    assert discovery[0].total is None
    assert discovery[-1].total == 3


def test_every_event_serializes(service, project):
    import json
    recorder = ProgressRecorder()
    service.create_bundle(sources=[project], base_path=project,
                          profile="plain_marker", include=["**/*.py"], progress=recorder)
    json.dumps([e.to_dict() for e in recorder.events])


def test_operations_work_without_a_progress_sink(service, project, tmp_path):
    result = service.create_bundle(sources=[project], base_path=project,
                                   profile="plain_marker", include=["**/*.py"])
    service.extract_bundle(result.text, output_dir=tmp_path / "out",
                           overwrite_policy="overwrite")
    service.validate_bundle(result.text)


# ---------------------------------------------------------------------------
# The facade must not leak interface concerns
# ---------------------------------------------------------------------------

def test_service_returns_data_not_renderer_objects(service, project):
    result = service.create_bundle(sources=[project], base_path=project,
                                   profile="plain_marker", include=["**/*.py"])
    import json
    json.dumps(result.to_dict())


def test_service_module_imports_no_interface():
    source = (Path(__file__).resolve().parents[2]
              / "src" / "core" / "service.py").read_text(encoding="utf-8")
    lowered = source.lower()
    for forbidden in ("import tkinter", "from tkinter", "import therm",
                      "from therm", "import flask", "from flask"):
        assert forbidden not in lowered, f"the service imports {forbidden}"
    assert "print(" not in source, "the service must not write to a stream"


def test_service_defaults_come_from_configuration(service):
    assert service.default_profile() in service.available_profiles()
