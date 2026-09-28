"""Mac-style framework file aliases must survive plan/check/create unchanged."""

from pathlib import Path

import pytest

from core.exceptions import BundleWriteError
from core.selection import State
from core.service import BundleToolService
from core.writer import BundleCreator


@pytest.fixture
def frameworks(tmp_path):
    source = tmp_path / "source"
    expected = {}
    for name in ("Mantle", "Squirrel", "ReactiveObjC"):
        framework = source / "runtime" / "Electron.app" / "Contents" / "Frameworks" / f"{name}.framework"
        version = framework / "Versions" / "A"
        version.mkdir(parents=True)
        payload = b"\x00\xffframework binary: " + name.encode()
        (version / name).write_bytes(payload)
        try:
            (framework / "Versions" / "Current").symlink_to("A", target_is_directory=True)
            (framework / name).symlink_to(Path("Versions") / "Current" / name)
        except OSError as error:
            pytest.skip(f"Host cannot create test symlinks: {error}")
        for path in (version / name, framework / name):
            expected[path.relative_to(source).as_posix()] = payload
    return source, expected


def test_framework_aliases_check_create_and_extract(frameworks, tmp_path):
    source, expected = frameworks
    service = BundleToolService()
    plan = service.plan_bundle([source], base_path=source)
    assert set(plan.plan.ordered_paths()) == set(expected)
    checked = service.check_selection(plan)
    assert checked.valid
    assert checked.file_count == len(expected)
    output = tmp_path / "frameworks.txt"
    created = service.create_bundle([source], source, output_path=output, plan=plan)
    assert {entry.path for entry in created.manifest.entries} == set(expected)
    assert service.check_bundle(output).valid
    extracted = tmp_path / "extracted"
    result = service.extract_bundle(output, extracted, add_headers=False)
    assert result.processed == len(expected)
    assert {path.relative_to(extracted).as_posix(): path.read_bytes()
            for path in extracted.rglob("*") if path.is_file()} == expected


def test_creator_keeps_file_aliases_when_discovering(frameworks):
    source, expected = frameworks
    creator = BundleCreator()
    files = creator.discover_files(source, base_path=source)
    manifest = creator.create_manifest(files, source, "plain_marker")
    assert {entry.path for entry in manifest.entries} == set(expected)


def test_framework_alias_cannot_read_outside_source(frameworks, tmp_path):
    source, _ = frameworks
    outside = tmp_path / "outside.txt"
    outside.write_text("outside data", encoding="utf-8")
    link = source / "outside-alias.txt"
    link.symlink_to(outside)
    plan = BundleToolService().plan_bundle([source], base_path=source)
    decision = next(d for d in plan.plan.decisions if d.path == link.name)
    assert decision.state is State.BLOCKED
    assert decision.code == "BLOCKED_OUTSIDE_BASE"
    with pytest.raises(BundleWriteError, match="outside"):
        BundleCreator().create_manifest([link], source, "plain_marker")


def test_creator_accepts_a_symlinked_source_root(frameworks, tmp_path):
    source, expected = frameworks
    alias = tmp_path / "source-alias"
    alias.symlink_to(source, target_is_directory=True)
    creator = BundleCreator()
    files = creator.discover_files(alias, base_path=alias)
    manifest = creator.create_manifest(files, alias, "plain_marker")
    assert {entry.path for entry in manifest.entries} == set(expected)
