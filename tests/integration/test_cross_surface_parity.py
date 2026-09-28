# BFT_B115_CROSS_SURFACE_PARITY
# ============================================================================
# SOURCEFILE: test_cross_surface_parity.py
# RELPATH: bundle_file_tool_v2/tests/integration/test_cross_surface_parity.py
# PROJECT: Bundle File Tool v2.2
# VERSION: 2.1.115
# LIFECYCLE: Testing
# STATUS: Build 115 - WP4 - BFT_B115_CROSS_SURFACE_PARITY
# ============================================================================
"""SEL-X-001 and the governance guarantees, across all three surfaces.

    SEL-X-001: The same sources, preset, rule file, and overrides produce the
    same ordered decisions in service, CLI, and Tkinter adapter tests.

Three surfaces, one answer. This is the criterion that makes the whole
architecture worth its cost, and the one that would decay first without a test:
each adapter is developed separately, and a divergence shows up as "the GUI
bundled something the CLI didn't" long after the cause is cold.

The CLI runs as a real subprocess so that nothing shared in-process can mask a
difference. SEL-X-002 - that no adapter reimplements precedence - is enforced
structurally, by parsing each adapter for imports of the engine internals.
"""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from core.config import ConfigManager
from core.service import BundleToolService
from ui.workspace_model import VIEW_INCLUDED, WorkspaceModel

SRC = Path(__file__).resolve().parents[2] / "src"


@pytest.fixture
def project(tmp_path):
    """One tree exercised identically by every surface."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_bytes(b"print(1)\n")
    (tmp_path / "src" / "util.py").write_bytes(b"x = 2\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guide.md").write_bytes(b"# guide\n")
    (tmp_path / "notes.log").write_bytes(b"noise\n")
    (tmp_path / "vendor.whl").write_bytes(b"PK\x03\x04")

    env = tmp_path / ".venv312"
    (env / "Scripts").mkdir(parents=True)
    (env / "pyvenv.cfg").write_bytes(b"home = C\n")
    (env / "Scripts" / "python.exe").write_bytes(b"MZ")
    (env / "junk.py").write_bytes(b"pass\n")
    return tmp_path


def cli_paths(project, *flags):
    """The CLI's answer, from a real process."""
    result = subprocess.run(
        [sys.executable, "-m", "cli", "plan", str(project), *flags, "--list"],
        capture_output=True, cwd=str(SRC))
    assert result.returncode == 0, result.stderr.decode()
    return result.stdout.decode().split()


# ---------------------------------------------------------------------------
# SEL-X-001
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("flags,kwargs", [
    ([], {}),
    (["--preset", "logs"], {"preset": ["logs"]}),
    (["--preset", "python-env"], {"preset": ["python-env"]}),
    (["--include", "src/**"], {"include": ["src/**"]}),
    (["--exclude", "docs/**"], {"exclude": ["docs/**"]}),
    (["--force-include", "**/*.whl"], {"force_include": ["**/*.whl"]}),
    (["--group", "d=docs/**", "--group", "c=src/**"],
     {"groups": ["d=docs/**", "c=src/**"]}),
])
def test_service_cli_and_workspace_agree(project, flags, kwargs):
    """The same inputs, the same ordered decisions, on all three surfaces."""
    service = BundleToolService()
    plan = service.plan_bundle([project], **kwargs)
    model = WorkspaceModel(service, plan)

    from_service = plan.plan.ordered_paths()
    from_cli = cli_paths(project, *flags)
    from_workspace = [row.path for row in model.rows(view=VIEW_INCLUDED)]

    assert from_service == from_cli, "service and CLI disagree"
    assert from_service == from_workspace, "service and workspace disagree"


def test_a_rules_file_produces_one_answer_everywhere(project, tmp_path):
    rules = tmp_path / "team.json"
    rules.write_text(json.dumps({"version": 1, "deny": ["docs/**"]}),
                     encoding="utf-8")
    service = BundleToolService()
    plan = service.plan_bundle([project], rules=rules)
    model = WorkspaceModel(service, plan)

    from_cli = cli_paths(project, "--rules", str(rules))
    assert plan.plan.ordered_paths() == from_cli
    assert [r.path for r in model.rows(view=VIEW_INCLUDED)] == from_cli
    assert "docs/guide.md" not in from_cli


def test_workspace_overrides_reproduce_on_the_command_line(project):
    """A selection made by clicking must be reproducible by flag.

    The workspace records `('exclude', 'docs/**')`; the CLI spells the same
    thing `--force-exclude docs/**`. If these diverged, a selection built in
    the GUI could not be scripted, which is the §6 promise.
    """
    service = BundleToolService()
    model = WorkspaceModel(service, service.plan_bundle([project]))
    model.set_folder("docs", include=False)

    from_workspace = [row.path for row in model.rows(view=VIEW_INCLUDED)]
    from_cli = cli_paths(project, "--force-exclude", "docs/**")
    assert from_workspace == from_cli


def test_every_surface_prunes_the_environment_identically(project):
    service = BundleToolService()
    plan = service.plan_bundle([project])
    model = WorkspaceModel(service, plan)
    from_cli = cli_paths(project)

    assert not any(p.startswith(".venv312/") for p in from_cli)
    assert not any(p.startswith(".venv312/") for p in plan.plan.ordered_paths())
    assert not any(node.path.startswith(".venv312/")
                   for node in model.tree(expanded=[".venv312"]))


def test_the_bundle_matches_what_the_workspace_showed(project, tmp_path):
    """The end of the chain: the artifact equals the preview."""
    service = BundleToolService()
    model = WorkspaceModel(service, service.plan_bundle([project],
                                                        preset=["logs"]))
    model.set_folder("docs", include=False)
    shown = [row.path for row in model.rows(view=VIEW_INCLUDED)]

    outcome = service.create_bundle(
        sources=model.result.sources, base_path=model.result.base_path,
        output_path=tmp_path / "out.txt", plan=model.result)
    written = [entry.path.replace(chr(92), "/") for entry in outcome.manifest.entries]
    assert sorted(written) == sorted(shown)


# ---------------------------------------------------------------------------
# SEL-X-002 - no adapter reimplements precedence
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("module", [
    "ui/workspace_model.py",
    "ui/selection_workspace.py",
    "ui/rule_editor.py",
    "cli_plan.py",
])
def test_no_adapter_constructs_its_own_selection_engine(module):
    """An adapter that built its own engine could answer differently."""
    source = (SRC / module).read_text(encoding="utf-8")
    tree = ast.parse(source)
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert "SelectionEngine" not in names, (
        f"{module} constructs a selection engine of its own")
    assert "rules_from_globs" not in names, (
        f"{module} assembles a governed rule stack of its own")


@pytest.mark.parametrize("module", [
    "cli.py",
    "ui/bundle_frame.py",
    "ui/selection_workspace.py",
])
def test_no_bundle_adapter_constructs_the_legacy_creator(module):
    """P0: presentation adapters may execute only through the service."""
    tree = ast.parse((SRC / module).read_text(encoding="utf-8"))
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert "BundleCreator" not in names


@pytest.mark.parametrize("module", ["ui/workspace_model.py", "cli_plan.py"])
def test_adapters_do_not_walk_the_filesystem_themselves(module):
    """Discovery belongs to the scanner; an adapter that walked would drift."""
    source = (SRC / module).read_text(encoding="utf-8")
    for forbidden in ("os.walk", "rglob", "iterdir"):
        assert forbidden not in source, f"{module} performs its own walk"


# ---------------------------------------------------------------------------
# SEL-GOV-001 - runtime never writes governed policy
# ---------------------------------------------------------------------------

def governed_digest() -> str:
    path = ConfigManager.governed_manifest_path().parent.parent / "bundle_config.json"
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_a_full_workspace_session_never_writes_the_governed_config(project):
    """SEL-GOV-001, asserted by hashing rather than by inspection."""
    before = governed_digest()
    service = BundleToolService()
    model = WorkspaceModel(service, service.plan_bundle([project]))

    model.set_folder("src", include=False)
    model.set_file("notes.log", include=True)
    model.set_presets(["logs", "python-env"])
    model.set_groups(["d=docs/**"])
    model.apply_bulk(False, search="guide")
    model.undo()
    model.redo()
    model.clear_all_overrides()
    model.include_root(".venv312")

    assert governed_digest() == before, "the governed configuration was modified"


def test_the_rule_editor_preview_writes_nothing(project):
    from ui.rule_editor import RuleEditorPreview

    before = governed_digest()
    service = BundleToolService()
    model = WorkspaceModel(service, service.plan_bundle([project]))
    previewer = RuleEditorPreview(model)
    for pattern in ("**/*.py", "docs/**", "", "src/app.py"):
        previewer.preview(pattern, include=False)
        previewer.preview(pattern, include=True)
    assert governed_digest() == before


def test_planning_creates_no_file_in_the_working_directory(project, tmp_path,
                                                           monkeypatch):
    """A stray state file beside the source tree would be its own defect."""
    monkeypatch.chdir(tmp_path)
    before = {p.name for p in tmp_path.iterdir()}
    service = BundleToolService()
    model = WorkspaceModel(service, service.plan_bundle([project]))
    model.set_folder("src", include=False)
    assert {p.name for p in tmp_path.iterdir()} == before
