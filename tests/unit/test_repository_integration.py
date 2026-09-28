"""Prototype acceptance tests for the read-only BFT/VCS boundary."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.exceptions import PlanDriftError
from core.repository import (
    RepositoryExtractionPolicy,
    RepositoryFile,
    RepositoryIntegrationError,
    RepositoryInventory,
    RepositoryStatus,
)
from core.service import BundleToolService
from core.selection import State


class StubRepositoryReader:
    """Deterministic protocol fake; it performs no Git or filesystem writes."""

    def __init__(self, root: Path, files=(), *, clean=True, is_repository=True,
                 source_bytes=None, session_files=None):
        self.root = Path(root).resolve()
        self.files = tuple(files)
        self.session_files = (None if session_files is None
                              else tuple(session_files))
        self.source_bytes = dict(source_bytes or {})
        self.clean = clean
        self.is_repository = is_repository
        self.inspect_calls = []
        self.list_calls = []
        self.session_calls = []
        self.read_calls = []

    def inspect(self, root: Path, *, allowed_root: Path) -> RepositoryStatus:
        requested = Path(root).resolve()
        self.inspect_calls.append((requested, Path(allowed_root).resolve()))
        return RepositoryStatus(
            requested_root=requested,
            repository_root=self.root if self.is_repository else None,
            is_repository=self.is_repository,
            is_clean=self.clean,
            provider_id="stub",
            provider_version="0.1",
        )

    def list_files(
        self,
        root: Path,
        *,
        allowed_root: Path,
        include_tracked: bool,
        include_untracked: bool,
        include_ignored: bool,
    ) -> RepositoryInventory:
        self.list_calls.append(
            {
                "root": Path(root).resolve(),
                "allowed_root": Path(allowed_root).resolve(),
                "tracked": include_tracked,
                "untracked": include_untracked,
                "ignored": include_ignored,
            }
        )
        selected = tuple(
            item
            for item in self.files
            if (
                (item.tracked and include_tracked)
                or (item.untracked and include_untracked)
                or (item.ignored and include_ignored)
            )
        )
        return RepositoryInventory(
            repository_root=self.root,
            files=selected,
            provider_id="stub",
            provider_version="0.1",
        )

    def open_read_session(self, root: Path, *, allowed_root: Path,
                          max_file_bytes: int):
        self.session_calls.append({
            "root": Path(root).resolve(),
            "allowed_root": Path(allowed_root).resolve(),
            "max_file_bytes": max_file_bytes,
        })
        files = self.files if self.session_files is None else self.session_files
        inventory = RepositoryInventory(
            repository_root=self.root,
            files=tuple(item for item in files if item.tracked),
            provider_id="stub",
            provider_version="0.1",
        )
        return StubRepositoryReadSession(self, inventory, max_file_bytes)


class StubRepositoryReadSession:
    def __init__(self, reader, inventory, max_file_bytes):
        self.reader = reader
        self.inventory = inventory
        self.max_file_bytes = max_file_bytes
        self.plan_manifest_digest = "a" * 64
        self.closed = False

    def read_bytes(self, path: str) -> bytes:
        if self.closed:
            raise RepositoryIntegrationError("stub session is closed")
        self.reader.read_calls.append(path)
        content = self.reader.source_bytes.get(path)
        if content is None:
            content = (self.reader.root / path).read_bytes()
        if len(content) > self.max_file_bytes:
            raise RepositoryIntegrationError("stub content exceeds read limit")
        return content

    def close(self):
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()


def write_tree(root: Path, files: dict[str, str]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for relative, content in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def make_bundle(tmp_path: Path, files: dict[str, str]) -> str:
    source = tmp_path / "bundle-source"
    write_tree(source, files)
    return (
        BundleToolService()
        .create_bundle(sources=[source], base_path=source, profile="plain_marker")
        .text
    )


def test_filesystem_mode_does_not_require_or_call_a_repository_reader(tmp_path):
    write_tree(tmp_path, {"a.py": "A\n", "b.py": "B\n"})

    plan = BundleToolService().plan_bundle([tmp_path], base_path=tmp_path)

    assert plan.repository is None
    assert plan.included_paths == ["a.py", "b.py"]


def test_tracked_mode_intersects_after_bft_selection(tmp_path):
    write_tree(tmp_path, {"a.py": "A\n", "notes.txt": "notes\n"})
    reader = StubRepositoryReader(tmp_path, [RepositoryFile("a.py", tracked=True)])
    service = BundleToolService(repository_reader=reader)

    plan = service.plan_bundle([tmp_path], base_path=tmp_path, source_mode="tracked")

    assert plan.included_paths == ["a.py"]
    excluded = plan.plan.explain("notes.txt")
    assert excluded is not None
    assert excluded.state is State.EXCLUDED
    assert excluded.code == "EXCLUDED_NOT_TRACKED"
    assert plan.repository is not None
    assert plan.to_dict()["repository"]["tracked_count"] == 1
    assert str(tmp_path.resolve()) not in str(plan.to_dict()["repository"])


def test_repository_filter_cannot_replace_a_bft_safety_block(tmp_path):
    write_tree(tmp_path, {"a.py": "A\n", "active.txt": "old\n"})
    reader = StubRepositoryReader(
        tmp_path,
        [RepositoryFile("a.py", tracked=True), RepositoryFile("active.txt", tracked=True)],
    )
    service = BundleToolService(repository_reader=reader)

    plan = service.plan_bundle(
        [tmp_path], base_path=tmp_path, source_mode="tracked", output_path=tmp_path / "active.txt"
    )

    blocked = plan.plan.explain("active.txt")
    assert blocked is not None
    assert blocked.state is State.BLOCKED
    assert blocked.code == "BLOCKED_ACTIVE_OUTPUT"


def test_replan_cannot_force_include_an_untracked_path(tmp_path):
    write_tree(tmp_path, {"tracked.py": "T\n", "scratch.py": "S\n"})
    reader = StubRepositoryReader(tmp_path, [RepositoryFile("tracked.py", tracked=True)])
    service = BundleToolService(repository_reader=reader)
    initial = service.plan_bundle([tmp_path], base_path=tmp_path, source_mode="tracked")

    replanned = service.replan(initial, overrides=[("include", "scratch.py")])

    scratch = replanned.plan.explain("scratch.py")
    assert scratch is not None
    assert scratch.state is State.EXCLUDED
    assert scratch.code == "EXCLUDED_NOT_TRACKED"


def test_bundle_creation_refuses_repository_inventory_drift(tmp_path):
    write_tree(tmp_path, {"a.py": "A\n", "b.py": "B\n"})
    reader = StubRepositoryReader(tmp_path, [RepositoryFile("a.py", tracked=True)])
    service = BundleToolService(repository_reader=reader)
    plan = service.plan_bundle([tmp_path], base_path=tmp_path, source_mode="tracked")
    reader.files = (RepositoryFile("b.py", tracked=True),)

    with pytest.raises(PlanDriftError, match="tracked-file inventory changed"):
        service.create_bundle(sources=[tmp_path], base_path=tmp_path, plan=plan)


def test_stable_tracked_plan_and_bundle_reconcile(tmp_path):
    write_tree(tmp_path, {"a.py": "A\n", "scratch.py": "S\n"})
    reader = StubRepositoryReader(tmp_path, [RepositoryFile("a.py", tracked=True)])
    service = BundleToolService(repository_reader=reader)
    plan = service.plan_bundle([tmp_path], base_path=tmp_path, source_mode="tracked")

    result = service.create_bundle(sources=[tmp_path], base_path=tmp_path, plan=plan)

    assert [entry.path for entry in result.manifest.entries] == ["a.py"]
    assert len(reader.list_calls) == 3  # plan, pre-read, post-read
    assert reader.read_calls == ["a.py"]
    assert len(reader.session_calls) == 1


def test_repository_mode_emits_bytes_from_the_plan_bound_session(tmp_path):
    write_tree(tmp_path, {"a.txt": "DISK"})
    reader = StubRepositoryReader(
        tmp_path,
        [RepositoryFile("a.txt", tracked=True)],
        source_bytes={"a.txt": b"VCS!"},
    )
    service = BundleToolService(repository_reader=reader)
    plan = service.plan_bundle([tmp_path], base_path=tmp_path, source_mode="tracked")

    result = service.create_bundle(sources=[tmp_path], base_path=tmp_path, plan=plan)

    assert result.manifest.entries[0].content == "VCS!"
    assert result.manifest.entries[0].file_size_bytes == 4
    assert reader.read_calls == ["a.txt"]


def test_repository_selection_check_reads_through_the_same_session_seam(tmp_path):
    write_tree(tmp_path, {"a.txt": "DISK"})
    reader = StubRepositoryReader(
        tmp_path,
        [RepositoryFile("a.txt", tracked=True)],
        source_bytes={"a.txt": b"VCS!"},
    )
    service = BundleToolService(repository_reader=reader)
    plan = service.plan_bundle([tmp_path], base_path=tmp_path, source_mode="tracked")

    result = service.check_selection(plan)

    assert result.valid is True
    assert reader.read_calls == ["a.txt"]


def test_repository_read_session_inventory_must_match_reviewed_plan(tmp_path):
    write_tree(tmp_path, {"a.py": "A\n", "b.py": "B\n"})
    reader = StubRepositoryReader(
        tmp_path,
        [RepositoryFile("a.py", tracked=True)],
        session_files=[RepositoryFile("b.py", tracked=True)],
    )
    service = BundleToolService(repository_reader=reader)
    plan = service.plan_bundle([tmp_path], base_path=tmp_path, source_mode="tracked")

    with pytest.raises(PlanDriftError, match="read-session inventory differs"):
        service.create_bundle(sources=[tmp_path], base_path=tmp_path, plan=plan)

    assert reader.read_calls == []


def test_repository_source_requires_the_exact_repository_root(tmp_path):
    source = tmp_path / "subdir"
    write_tree(source, {"a.py": "A\n"})
    reader = StubRepositoryReader(tmp_path, [RepositoryFile("subdir/a.py", tracked=True)])

    with pytest.raises(RepositoryIntegrationError, match="exact repository root"):
        BundleToolService(repository_reader=reader).plan_bundle(
            [source], base_path=source, source_mode="tracked"
        )


def test_extraction_preflight_classifies_every_existing_destination(tmp_path):
    target = tmp_path / "repo"
    write_tree(
        target,
        {
            "tracked.txt": "old tracked\n",
            "untracked.txt": "old untracked\n",
            "ignored.txt": "old ignored\n",
            "other.txt": "old other\n",
        },
    )
    bundle = make_bundle(
        tmp_path,
        {
            "tracked.txt": "new tracked\n",
            "untracked.txt": "new untracked\n",
            "ignored.txt": "new ignored\n",
            "other.txt": "new other\n",
            "new.txt": "new\n",
        },
    )
    reader = StubRepositoryReader(
        target,
        [
            RepositoryFile("tracked.txt", tracked=True),
            RepositoryFile("untracked.txt", untracked=True),
            RepositoryFile("ignored.txt", ignored=True),
        ],
    )
    service = BundleToolService(repository_reader=reader)

    result = service.preflight_repository_extraction(bundle, target)

    assert result.allowed is False
    assert [(item.path, item.classification) for item in result.collisions] == [
        ("ignored.txt", "ignored"),
        ("other.txt", "other"),
        ("tracked.txt", "tracked"),
        ("untracked.txt", "untracked"),
    ]
    assert "new.txt" not in {item.path for item in result.collisions}


def test_blocked_repository_preflight_writes_nothing(tmp_path):
    target = tmp_path / "repo"
    write_tree(target, {"tracked.txt": "original\n"})
    bundle = make_bundle(tmp_path, {"tracked.txt": "replacement\n"})
    reader = StubRepositoryReader(target, [RepositoryFile("tracked.txt", tracked=True)])
    service = BundleToolService(repository_reader=reader)

    with pytest.raises(RepositoryIntegrationError, match="overwrite was not approved"):
        service.extract_bundle(
            bundle,
            target,
            overwrite_policy="overwrite",
            add_headers=False,
            repository_policy=RepositoryExtractionPolicy(),
        )

    assert (target / "tracked.txt").read_text(encoding="utf-8") == "original\n"


def test_explicit_repository_policy_can_authorize_a_clean_overwrite(tmp_path):
    target = tmp_path / "repo"
    write_tree(target, {"tracked.txt": "original\n"})
    bundle = make_bundle(tmp_path, {"tracked.txt": "replacement\n"})
    reader = StubRepositoryReader(target, [RepositoryFile("tracked.txt", tracked=True)])
    service = BundleToolService(repository_reader=reader)

    result = service.extract_bundle(
        bundle,
        target,
        overwrite_policy="overwrite",
        add_headers=False,
        repository_policy=RepositoryExtractionPolicy(allow_tracked_overwrite=True),
    )

    assert result.repository_preflight is not None
    assert result.repository_preflight.allowed is True
    assert (target / "tracked.txt").read_text(encoding="utf-8") == "replacement\n"


def test_dirty_repository_is_blocked_even_when_no_path_collides(tmp_path):
    target = tmp_path / "repo"
    target.mkdir()
    bundle = make_bundle(tmp_path, {"new.txt": "new\n"})
    reader = StubRepositoryReader(target, clean=False)
    service = BundleToolService(repository_reader=reader)

    result = service.preflight_repository_extraction(bundle, target)

    assert result.allowed is False
    assert result.collisions == ()
    assert any("cleanliness is dirty" in reason for reason in result.reasons)


def test_non_repository_preflight_does_not_attempt_file_inventory(tmp_path):
    target = tmp_path / "ordinary"
    target.mkdir()
    bundle = make_bundle(tmp_path, {"new.txt": "new\n"})
    reader = StubRepositoryReader(target, is_repository=False)

    result = BundleToolService(repository_reader=reader).preflight_repository_extraction(
        bundle, target
    )

    assert result.allowed is False
    assert reader.list_calls == []
