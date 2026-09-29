"""Regression tests for the ratified WP0 release and governance contracts."""

from __future__ import annotations

import json
import hashlib
import re
import tomllib
from pathlib import Path

from core.config import ConfigManager
from core.version import __version__
from cli import build_parser
from core import module_ids


ROOT = Path(__file__).resolve().parents[2]
EXPECTED_VERSION = "2.1.136"
ARCHIVE_DENIES = {
    "**/*_bundle_*.txt",
    "**/*.zip",
    "**/*.tar",
    "**/*.tar.*",
    "**/archives/**",
}


def test_package_owned_version_sources_agree() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    bundle_config = json.loads((ROOT / "bundle_config.json").read_text(encoding="utf-8"))
    project_spec = json.loads(
        (ROOT / ".pyprojectmgr" / "project_spec.json").read_text(encoding="utf-8")
    )
    manifest = json.loads(
        (ROOT / ".pyprojectmgr" / "project_manifest.json").read_text(encoding="utf-8")
    )

    assert __version__ == EXPECTED_VERSION
    assert (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip() == EXPECTED_VERSION
    assert pyproject["project"]["version"] == EXPECTED_VERSION
    assert bundle_config["version"] == EXPECTED_VERSION
    assert project_spec["version"] == EXPECTED_VERSION
    assert manifest["project_meta"]["version"] == EXPECTED_VERSION
    assert manifest["meta"]["version"] == EXPECTED_VERSION


def test_safety_defaults_are_deny_list_based_and_synchronized() -> None:
    bundle_config = json.loads((ROOT / "bundle_config.json").read_text(encoding="utf-8"))
    shipped_safety = bundle_config["safety"]
    code_safety = ConfigManager.DEFAULT_CONFIG["safety"]

    assert shipped_safety["allow_globs"] == ["**/*"]
    assert code_safety["allow_globs"] == ["**/*"]
    assert ARCHIVE_DENIES <= set(shipped_safety["deny_globs"])
    assert ARCHIVE_DENIES <= set(code_safety["deny_globs"])


def test_project_spec_records_required_git_separation_of_duties() -> None:
    project_spec = json.loads(
        (ROOT / ".pyprojectmgr" / "project_spec.json").read_text(encoding="utf-8")
    )
    policy = project_spec["governance"]["repository_controls"][
        "git_metadata_write_policy"
    ]

    assert policy["mode"] == "separation_of_duties"
    assert policy["automated_agents"] == "deny"
    assert policy["authorized_interactive_accounts"] == "allow"
    assert policy["enforcement"] == "host_acl"


def test_generated_governance_ids_reference_current_manifest() -> None:
    manifest_bytes = (ROOT / ".pyprojectmgr" / "project_manifest.json").read_bytes()
    manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()
    schema_source = (ROOT / "src" / "database" / "schema_ids.py").read_text(
        encoding="utf-8"
    )
    schema_hash = re.search(
        r'^MANIFEST_HASH: Final\[str\] = "([0-9a-f]{64})"$',
        schema_source,
        re.MULTILINE,
    )
    schema_version = re.search(
        r'^PROJECT_VERSION: Final\[str\] = "([^"]+)"$',
        schema_source,
        re.MULTILINE,
    )

    assert module_ids.MANIFEST_HASH == manifest_hash
    assert schema_hash and schema_hash.group(1) == manifest_hash
    assert schema_version and schema_version.group(1) == EXPECTED_VERSION


def test_stager_never_increments_package_owned_version() -> None:
    stager = (ROOT / "PREP_AND_STAGE_BFT.bat").read_text(encoding="utf-8")

    assert "set /a NEWBUILD" not in stager
    assert 'echo %MAJOR%.%MINOR%.%NEWBUILD%>"%VERSIONFILE%"' not in stager
    assert "VERSION.txt remains package-owned" in stager


def test_stager_snapshot_is_bounded_atomic_and_diagnostic() -> None:
    stager = (ROOT / "PREP_AND_STAGE_BFT.bat").read_text(encoding="utf-8")

    assert 'set "SNAPWORK=%SNAPDIR%.partial"' in stager
    assert 'robocopy "%ROOT%" "%SNAPWORK%" /E /XJ' in stager
    for excluded in (
        '"%ROOT%\\.venv"',
        '"%ROOT%\\.venv311"',
        '"%ROOT%\\.venv312"',
        '"%ROOT%\\.venv313"',
        '"%ROOT%\\.git"',
        '"%ROOT%\\out"',
        '"%ROOT%\\tmp"',
        '"%ROOT%\\.ruff_cache"',
        '"%ROOT%\\htmlcov"',
        '"%ROOT%\\build"',
        '"%ROOT%\\dist"',
    ):
        assert excluded in stager
    assert 'set "RRC=%ERRORLEVEL%"' in stager
    assert 'type "%ROBOLOG%"' in stager
    assert 'move /y "%SNAPWORK%" "%SNAPDIR%"' in stager


def test_stager_verifies_and_archives_delivery_checksum_with_zip() -> None:
    stager = (ROOT / "PREP_AND_STAGE_BFT.bat").read_text(encoding="utf-8")

    assert 'set "DELSHA=%DELZIP%.sha256"' in stager
    assert 'call :hashVerify "%DELZIP%" "!DEL_EXPECTED!"' in stager
    assert 'move /y "%DELSHA%" "%ARCHIVES%\\"' in stager
    assert 'move /y "%DELZIP%" "%ARCHIVES%\\"' in stager


def test_installer_handles_transient_mapped_file_copy_errors_fail_closed() -> None:
    installers = sorted(ROOT.glob("INSTALL_BUNDLETOOL_*.bat"))
    assert len(installers) == 1
    installer = installers[0].read_text(encoding="ascii")

    assert 'call :placeResilient "%INCOMING%\\%%I" "%ROOT%\\%%I"' in installer
    assert "for /l %%R in (1,1,3) do (" in installer
    assert 'call :hashVerify "%~2" "!PLACE_EXPECTED!"' in installer
    assert "copy returned nonzero after destination bytes matched" in installer
    assert "copy failed after 3 attempts" in installer


def test_installer_delivers_the_cross_product_config_hub_contract() -> None:
    installers = sorted(ROOT.glob("INSTALL_BUNDLETOOL_*.bat"))
    assert len(installers) == 1
    installer = installers[0].read_text(encoding="ascii")

    assert 'set "INTEGRATION_MANIFEST=%SUPPORT%\\integration_manifest.sha256"' in installer
    assert 'set "PPMROOT=%PYPROJECTMGR_PROJECT_ROOT%"' in installer
    assert 'set "CONFIGEDITORROOT=%CONFIGEDITOR_PROJECT_ROOT%"' in installer
    assert 'call :resolveIntegration "%%I" "%%J"' in installer
    assert 'call :placeResilient "!INTSOURCE!" "!INTTARGET!"' in installer
    assert "test_pythermx_vertical_slice.py" in installer
    assert "test_config_hub_real_tk.py" in installer
    assert "tests\\test_config_edit_hub.py" in installer


def test_cli_reports_package_owned_version(capsys) -> None:
    parser = build_parser()

    try:
        parser.parse_args(["--version"])
    except SystemExit as exc:
        assert exc.code == 0
    else:
        raise AssertionError("--version did not terminate through argparse")

    assert capsys.readouterr().out.strip() == f"bundle-tool {EXPECTED_VERSION}"


def test_build130_delivery_markers_are_batch_quote_safe() -> None:
    builder = (ROOT / "scripts" / "build_build130_delivery.ps1").read_text(
        encoding="utf-8"
    )

    assert 'src\\web\\static\\app.css|.skin-picker button.active' in builder
    assert 'src\\web\\static\\app.css|:root[data-skin=' not in builder
    assert "Batch-unsafe delivery marker" in builder


def test_current_installer_accepts_branded_pysplashx_version_output() -> None:
    installer = (
        ROOT / "INSTALL_BUNDLETOOL_v2_1_136_macos_confighub_launch.bat"
    ).read_text(encoding="ascii")

    assert 'for /f "tokens=2" %%V in' in installer
    assert 'if /i not "!ENV_SXVER!"=="!SXVER!"' in installer
    assert 'if /i not "!ENV_SXVER!"=="0.1.0"' not in installer
