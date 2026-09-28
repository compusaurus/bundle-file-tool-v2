"""The supported Python contract must agree across BFT delivery surfaces."""

from __future__ import annotations

import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_package_metadata_declares_the_three_runtime_matrix():
    project = tomllib.loads(
        (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )["project"]

    assert project["requires-python"] == ">=3.11,<3.14"
    classifiers = set(project["classifiers"])
    for version in ("3.11", "3.12", "3.13"):
        assert f"Programming Language :: Python :: {version}" in classifiers


def test_installer_accepts_exactly_the_supported_minor_range():
    installers = sorted(ROOT.glob("INSTALL_BUNDLETOOL_*.bat"))
    assert installers, "no governed BFT installer is present"
    installer = installers[-1].read_text(encoding="utf-8")

    assert "(3,11) <= (v[0],v[1]) < (3,14)" in installer
    assert "requires Python 3.11, 3.12, or 3.13" in installer
    for directory in (".venv311", ".venv312", ".venv313"):
        assert directory in installer
    assert "for %%E in (.venv .venv312 .venv313)" not in installer
    assert "legacy .venv is present" in installer
    assert "-TargetProjectRoot" in installer
    assert "-PayloadRoot" in installer


def test_environment_bootstrap_defines_all_supported_rows():
    bootstrap = (ROOT / "scripts" / "setup_supported_envs.ps1").read_text(
        encoding="utf-8"
    )

    for parameter in ("BFT_PYTHON311", "BFT_PYTHON312", "BFT_PYTHON313"):
        assert parameter in bootstrap
    for directory in ('Directory = ".venv311"', 'Directory = ".venv312"',
                      'Directory = ".venv313"'):
        assert directory in bootstrap
    assert "Legacy .venv exists" in bootstrap
    assert '[string]$TargetProjectRoot = ""' in bootstrap
    assert '[string]$PayloadRoot = ""' in bootstrap
