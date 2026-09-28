"""Contract tests for the optional installed-package VCS adapter."""

from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from core.repository import RepositoryIntegrationError
from core.vcs_repository import (
    VCS_TOOL_RUNTIME_VERSION,
    VcsToolRepositoryReader,
)


def value(name):
    return SimpleNamespace(value=name)


def record(**kwargs):
    return SimpleNamespace(**kwargs)


def make_api(content=b"hello\n"):
    state = {"tools": [], "session_options": None, "read_tokens": []}

    class FakeVcsError(Exception):
        def __init__(self, code, message):
            self.code = code
            super().__init__(message)

    vcs_file = record(
        path="tracked.txt",
        is_tracked=True,
        is_untracked=False,
        is_ignored=False,
        index_status=value("none"),
        worktree_status=value("modified"),
    )
    warning = record(code="VCS_WARN_TEST")
    file_result = record(
        root_dir=str(Path("repo").resolve()),
        files=(vcs_file,),
        provider_id="git_cli",
        provider_version="2.test",
        warnings=(warning,),
    )
    status_result = record(
        requested_dir=str(Path("repo").resolve()),
        root_dir=str(Path("repo").resolve()),
        is_repository=True,
        worktree=record(is_clean=False),
        provider_id="git_cli",
        provider_version="2.test",
        warnings=(warning,),
    )
    tree = record(
        root_dir=str(Path("repo").resolve()),
        provider_id="git_cli",
        provider_version="2.test",
        warnings=(warning,),
        total_files=1,
        root=record(
            vcs_file=None,
            children=(record(vcs_file=vcs_file, children=()),),
        ),
        plan_manifest=record(manifest_digest="b" * 64),
        plan_token="session-token",
    )

    class FakeSession:
        def __init__(self):
            self.closed = False

        def tree(self):
            return tree

        def read_bytes(self, path, *, plan_token=None):
            state["read_tokens"].append((path, plan_token))
            return record(
                content=content,
                descriptor=record(
                    path=path,
                    size_bytes=len(content),
                    content_sha256=hashlib.sha256(content).hexdigest(),
                    plan_verified=True,
                ),
            )

        def close(self):
            self.closed = True

    raw_session = FakeSession()

    class FakeTool:
        def __init__(self, **kwargs):
            state["tools"].append(kwargs)

        def inspect(self):
            return status_result

        def list_files(self, options):
            state["file_options"] = options
            return file_result

        def open_read_session(self, options):
            state["session_options"] = options
            return raw_session

    def options(**kwargs):
        return record(**kwargs)

    api = record(
        __version__=VCS_TOOL_RUNTIME_VERSION,
        VcsError=FakeVcsError,
        VcsTool=FakeTool,
        VcsFileListOptions=options,
        VcsReadLimits=options,
        VcsReadSessionOptions=options,
        VcsContentAccess=options,
        ReadSourceKind=record(WORKING_TREE="working-tree"),
        HashMode=record(INVENTORY="inventory"),
        PlanConsistency=record(CONTENT_DIGEST="content-digest"),
    )
    return api, state, raw_session


def test_adapter_translates_inspect_and_file_inventory(monkeypatch):
    api, state, _session = make_api()
    monkeypatch.setattr("core.vcs_repository.import_module", lambda _name: api)
    root = Path("repo").resolve()
    reader = VcsToolRepositoryReader(git_executable=Path("git"))

    status = reader.inspect(root, allowed_root=root)
    inventory = reader.list_files(
        root,
        allowed_root=root,
        include_tracked=True,
        include_untracked=False,
        include_ignored=False,
    )

    assert status.repository_root == root
    assert status.is_clean is False
    assert status.warnings == ("VCS_WARN_TEST",)
    assert inventory.tracked_paths() == frozenset({"tracked.txt"})
    assert inventory.files[0].worktree_state == "modified"
    assert state["tools"][0]["allowed_roots"] == (root,)
    assert state["file_options"].include_untracked is False


def test_adapter_reads_only_plan_verified_content(monkeypatch):
    api, state, raw_session = make_api(b"from-vcs\n")
    monkeypatch.setattr("core.vcs_repository.import_module", lambda _name: api)
    root = Path("repo").resolve()
    reader = VcsToolRepositoryReader()

    with reader.open_read_session(
            root, allowed_root=root, max_file_bytes=1024) as session:
        assert session.inventory.tracked_paths() == frozenset({"tracked.txt"})
        assert session.plan_manifest_digest == "b" * 64
        assert session.read_bytes("tracked.txt") == b"from-vcs\n"

    assert state["read_tokens"] == [("tracked.txt", "session-token")]
    assert state["session_options"].include_untracked is False
    assert state["session_options"].limits.max_read_bytes_per_file == 1024
    assert raw_session.closed is True


def test_adapter_rejects_unverified_or_tampered_content(monkeypatch):
    api, _state, _session = make_api(b"content")
    monkeypatch.setattr("core.vcs_repository.import_module", lambda _name: api)
    root = Path("repo").resolve()
    session = VcsToolRepositoryReader().open_read_session(
        root, allowed_root=root, max_file_bytes=1024)
    session.raw.read_bytes = lambda path, plan_token=None: record(
        content=b"content",
        descriptor=record(
            path=path,
            size_bytes=7,
            content_sha256="0" * 64,
            plan_verified=True,
        ),
    )

    with pytest.raises(RepositoryIntegrationError, match="digest evidence"):
        session.read_bytes("tracked.txt")
    session.close()


def test_adapter_rejects_unpinned_runtime(monkeypatch):
    api, _state, _session = make_api()
    api.__version__ = "0.6.0"
    monkeypatch.setattr("core.vcs_repository.import_module", lambda _name: api)

    with pytest.raises(RepositoryIntegrationError, match="Unsupported VCS Tool"):
        VcsToolRepositoryReader().inspect(Path("repo"), allowed_root=Path("repo"))


def test_adapter_translates_vcs_errors(monkeypatch):
    api, _state, _session = make_api()

    class BrokenTool:
        def __init__(self, **_kwargs):
            pass

        def inspect(self):
            raise api.VcsError("VCS_SECURITY_ROOT_DENIED", "root denied")

    api.VcsTool = BrokenTool
    monkeypatch.setattr("core.vcs_repository.import_module", lambda _name: api)

    with pytest.raises(RepositoryIntegrationError, match="VCS_SECURITY_ROOT_DENIED"):
        VcsToolRepositoryReader().inspect(Path("repo"), allowed_root=Path("repo"))
