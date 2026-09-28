# BFT_B113_DETECTOR_TESTS
# ============================================================================
# SOURCEFILE: test_detectors.py
# RELPATH: bundle_file_tool_v2/tests/unit/test_detectors.py
# PROJECT: Bundle File Tool v2.2
# VERSION: 2.1.113
# LIFECYCLE: Testing
# STATUS: Build 113 - WP2 - BFT_B113_DETECTOR_TESTS
# ============================================================================
"""WP2 exit gate: `.venv312` pruned before descent, ambiguity reported not guessed.

`SEL-DET-001`: conjunctive environment signatures prune before descent; ambiguous
single markers are traversed and reported.

The case that decided the design is `test_a_lone_activate_script_is_ambiguous`.
A repository may legitimately check in `bin/activate`. Under the first proposal -
a flat list where any single marker classified - that repository would have had
its entire subtree pruned before descent, so its files never reached the index
and the user could not see what was dropped, let alone override it.
"""

from __future__ import annotations

import pytest

from core.detectors import (
    AMBIGUOUS_MARKERS,
    DIRECTORY_FAMILIES,
    DetectorLedger,
    DetectorResult,
    classify_directory,
    should_prune,
)


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------

def make_venv(root, name=".venv312", *, interpreter="windows", config=True):
    env = root / name
    env.mkdir(parents=True)
    if config:
        (env / "pyvenv.cfg").write_text("home = C:/Python311\n", encoding="utf-8")
    if interpreter == "windows":
        (env / "Scripts").mkdir()
        (env / "Scripts" / "python.exe").write_bytes(b"MZ")
    elif interpreter == "posix":
        (env / "bin").mkdir()
        (env / "bin" / "python").write_text("#!/bin/sh\n", encoding="utf-8")
    return env


# ---------------------------------------------------------------------------
# 1. The screenshot case
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", [".venv", ".venv312", "env-app", "venv313", "myenv"])
def test_a_python_environment_is_found_by_structure_not_name(tmp_path, name):
    """The whole point: a versioned or custom name is still an environment."""
    env = make_venv(tmp_path, name)
    finding = classify_directory(str(env), name)

    assert finding.result is DetectorResult.DETECTED
    assert finding.family == "python-venv"
    assert finding.prunable is True
    assert "pyvenv.cfg" in finding.evidence
    assert finding.code == "DETECTED_PYTHON_ENV"


@pytest.mark.parametrize("interpreter", ["windows", "posix"])
def test_either_interpreter_layout_corroborates(tmp_path, interpreter):
    env = make_venv(tmp_path, ".venv", interpreter=interpreter)
    assert classify_directory(str(env)).result is DetectorResult.DETECTED


# ---------------------------------------------------------------------------
# 2. Conjunction - the ruling that replaced the flat signature list
# ---------------------------------------------------------------------------

def test_a_lone_activate_script_is_ambiguous_not_excluded(tmp_path):
    """The case that decided the design.

    A repository with a checked-in `bin/activate` and no interpreter is not an
    environment. Under a disjunction it would have been pruned before descent
    and its files would never have reached the index.
    """
    project = tmp_path / "tooling"
    (project / "bin").mkdir(parents=True)
    (project / "bin" / "activate").write_text("# helper\n", encoding="utf-8")

    finding = classify_directory(str(project), "tooling")

    assert finding.result is DetectorResult.UNKNOWN
    assert finding.prunable is False, "an ambiguous marker must never prune"
    assert finding.code == "UNKNOWN_ACTIVATE_WITHOUT_CONFIG"
    assert "pyvenv.cfg" in finding.missing
    assert "traversed" in finding.describe()


def test_pyvenv_cfg_without_an_interpreter_is_ambiguous(tmp_path):
    """A stripped or partially-deleted environment is reported, not assumed."""
    env = make_venv(tmp_path, ".venv-broken", interpreter=None)
    finding = classify_directory(str(env))

    assert finding.result is DetectorResult.UNKNOWN
    assert finding.prunable is False
    assert finding.code == "UNKNOWN_PYTHON_ENV_NO_INTERPRETER"
    assert "pyvenv.cfg" in finding.evidence
    assert any("python" in marker for marker in finding.missing)


def test_an_interpreter_layout_alone_does_not_classify(tmp_path):
    """A project with a `Scripts/python.exe` but no config is a project."""
    project = tmp_path / "vendored"
    (project / "Scripts").mkdir(parents=True)
    (project / "Scripts" / "python.exe").write_bytes(b"MZ")

    assert classify_directory(str(project), "vendored").result is DetectorResult.NONE


# ---------------------------------------------------------------------------
# 3. Other families
# ---------------------------------------------------------------------------

def test_conda_requires_history_as_corroboration(tmp_path):
    env = tmp_path / "condaenv"
    (env / "conda-meta").mkdir(parents=True)
    assert classify_directory(str(env), "condaenv").result is DetectorResult.UNKNOWN

    (env / "conda-meta" / "history").write_text("", encoding="utf-8")
    finding = classify_directory(str(env), "condaenv")
    assert finding.result is DetectorResult.DETECTED
    assert finding.code == "DETECTED_CONDA_ENV"


def test_node_modules_requires_a_parent_manifest(tmp_path):
    project = tmp_path / "webapp"
    modules = project / "node_modules"
    modules.mkdir(parents=True)

    assert classify_directory(str(modules), "node_modules").result is DetectorResult.UNKNOWN

    (project / "package.json").write_text("{}", encoding="utf-8")
    finding = classify_directory(str(modules), "node_modules")
    assert finding.result is DetectorResult.DETECTED
    assert finding.code == "DETECTED_NODE_MODULES"


def test_an_ordinary_directory_matches_nothing(tmp_path):
    plain = tmp_path / "src"
    plain.mkdir()
    (plain / "app.py").write_text("x = 1\n", encoding="utf-8")

    finding = classify_directory(str(plain), "src")
    assert finding.result is DetectorResult.NONE
    assert finding.prunable is False
    assert finding.describe() == "no detector matched"


# ---------------------------------------------------------------------------
# 4. Robustness
# ---------------------------------------------------------------------------

def test_a_missing_directory_classifies_as_none_rather_than_raising(tmp_path):
    assert classify_directory(str(tmp_path / "nope"), "nope").result is DetectorResult.NONE


def test_should_prune_agrees_with_classification(tmp_path):
    env = make_venv(tmp_path, ".venv312")
    plain = tmp_path / "src"
    plain.mkdir()

    assert should_prune(str(env)) is True
    assert should_prune(str(plain)) is False


def test_no_family_can_be_confirmed_by_a_single_marker_alone():
    """Guards the conjunction ruling against a future well-meaning edit."""
    for family in DIRECTORY_FAMILIES:
        assert family.corroborating or family.parent_marker, (
            f"{family.family} would classify on one marker - that is the "
            f"disjunction the addendum rejected"
        )


def test_ambiguous_markers_never_appear_as_confirming_evidence():
    confirming = {marker for family in DIRECTORY_FAMILIES
                  for marker in family.corroborating}
    ambiguous = {marker for marker, _, _ in AMBIGUOUS_MARKERS}
    assert not (confirming & ambiguous)


# ---------------------------------------------------------------------------
# 5. The ledger feeds the report
# ---------------------------------------------------------------------------

def test_the_ledger_records_both_pruned_and_ambiguous_directories(tmp_path):
    env = make_venv(tmp_path, ".venv312")
    odd = tmp_path / "tooling"
    (odd / "bin").mkdir(parents=True)
    (odd / "bin" / "activate").write_text("", encoding="utf-8")

    ledger = DetectorLedger()
    ledger.record(".venv312", classify_directory(str(env)))
    ledger.record("tooling", classify_directory(str(odd), "tooling"))

    assert ledger.pruned_roots() == [".venv312"]
    assert "tooling" in ledger.ambiguous

    rows = ledger.to_report()
    assert [row["path"] for row in rows] == [".venv312", "tooling"]
    assert rows[0]["result"] == "detected"
    assert rows[1]["result"] == "unknown"
    assert "missing" in rows[1], "an ambiguous row must say what was absent"


def test_report_rows_are_deterministic_and_serialisable(tmp_path):
    import json

    ledger = DetectorLedger()
    for name in ("b-env", "a-env"):
        env = make_venv(tmp_path, name)
        ledger.record(name, classify_directory(str(env)))

    rows = ledger.to_report()
    assert [row["path"] for row in rows] == ["a-env", "b-env"], "sorted output"
    json.dumps(rows)


# ---------------------------------------------------------------------------
# 6. Layering
# ---------------------------------------------------------------------------

def test_detectors_import_no_adapter():
    import ast
    from pathlib import Path

    module = Path(__file__).resolve().parents[2] / "src" / "core" / "detectors.py"
    tree = ast.parse(module.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])

    for banned in ("tkinter", "pythermx", "cli_progress", "ui", "cli"):
        assert banned not in imported, f"detectors.py imports {banned}"
