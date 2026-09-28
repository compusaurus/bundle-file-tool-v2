"""Installed-wheel integration for the read-only VCS repository source."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from core.repository import RepositoryExtractionPolicy
from core.service import BundleToolService
from core.vcs_repository import VCS_TOOL_RUNTIME_VERSION, VcsToolRepositoryReader


def git(executable: str, root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [executable, "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.mark.integration
def test_installed_vcs_wheel_supplies_tracked_bundle_bytes(tmp_path):
    vcs_tool = pytest.importorskip("vcs_tool")
    assert vcs_tool.__version__ == VCS_TOOL_RUNTIME_VERSION
    executable = shutil.which("git")
    if executable is None:
        pytest.skip("Git is required for the installed-wheel integration test")

    root = tmp_path / "repository"
    root.mkdir()
    git(executable, root, "init", "--quiet")
    git(executable, root, "config", "user.name", "BFT VCS Test")
    git(executable, root, "config", "user.email", "bft-vcs@example.invalid")
    (root / ".gitattributes").write_text("* text=auto eol=lf\n", encoding="utf-8")
    (root / "tracked.txt").write_bytes(b"tracked through vcs\n")
    (root / "scratch.txt").write_bytes(b"untracked\n")
    git(executable, root, "add", "--", ".gitattributes", "tracked.txt")
    git(executable, root, "commit", "--quiet", "-m", "fixture")

    reader = VcsToolRepositoryReader(git_executable=Path(executable))
    service = BundleToolService(repository_reader=reader)
    plan = service.plan_bundle([root], base_path=root, source_mode="tracked")

    assert plan.included_paths == [".gitattributes", "tracked.txt"]
    result = service.create_bundle(sources=[root], base_path=root, plan=plan)

    assert [entry.path for entry in result.manifest.entries] == [
        ".gitattributes",
        "tracked.txt",
    ]
    assert result.manifest.entries[1].content == "tracked through vcs\n"


@pytest.mark.integration
def test_installed_vcs_wheel_preflights_bft_owned_extraction(tmp_path):
    vcs_tool = pytest.importorskip("vcs_tool")
    assert vcs_tool.__version__ == VCS_TOOL_RUNTIME_VERSION
    executable = shutil.which("git")
    if executable is None:
        pytest.skip("Git is required for the installed-wheel integration test")

    root = tmp_path / "repository"
    root.mkdir()
    git(executable, root, "init", "--quiet")
    git(executable, root, "config", "user.name", "BFT VCS Test")
    git(executable, root, "config", "user.email", "bft-vcs@example.invalid")
    (root / ".gitattributes").write_text("* text=auto eol=lf\n", encoding="utf-8")
    (root / "tracked.txt").write_bytes(b"original\n")
    git(executable, root, "add", "--", ".gitattributes", "tracked.txt")
    git(executable, root, "commit", "--quiet", "-m", "fixture")

    source = tmp_path / "bundle-source"
    source.mkdir()
    (source / "tracked.txt").write_bytes(b"replacement\n")
    bundle = BundleToolService().create_bundle(
        sources=[source], base_path=source, profile="plain_marker"
    ).text

    reader = VcsToolRepositoryReader(git_executable=Path(executable))
    service = BundleToolService(repository_reader=reader)
    preflight = service.preflight_repository_extraction(bundle, root)

    assert preflight.allowed is False
    assert [(item.path, item.classification) for item in preflight.collisions] == [
        ("tracked.txt", "tracked")
    ]

    result = service.extract_bundle(
        bundle,
        root,
        overwrite_policy="overwrite",
        add_headers=False,
        repository_policy=RepositoryExtractionPolicy(
            allow_tracked_overwrite=True
        ),
    )

    assert result.repository_preflight is not None
    assert result.repository_preflight.allowed is True
    assert (root / "tracked.txt").read_bytes() == b"replacement\n"
    status = git(executable, root, "status", "--short").stdout
    assert " M tracked.txt" in status
