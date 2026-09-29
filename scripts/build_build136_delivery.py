"""Build the Build 136 delivery kit: one zip plus its SHA256 sidecar.

A Python port of ``build_build136_delivery.ps1`` for machines where
PowerShell execution is blocked. It produces the same tree, the same
manifest and marker files, and the same sidecar format, so either script
yields an equivalent delivery for ``PREP_AND_STAGE_BFT.bat`` to stage.

    python scripts\\build_build136_delivery.py [--output-directory DIR]

Team Delivery Standard v2.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import zipfile
from pathlib import Path

BUILD_NAME = "INSTALL_BUNDLETOOL_v2_1_136_macos_confighub_launch"
BUILD_DIRECTORY = "build136_delivery"
BUILD_RECORD = "built_build136.md"

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Mirrors the PowerShell pipeline's exclusions.
EXCLUDED_DIRECTORIES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}

ROOT_FILES = (
    ".gitattributes",
    ".gitignore",
    "bundle_config.json",
    "PREP_AND_STAGE_BFT.bat",
    "pyproject.toml",
    "pytest.ini",
    "requirements-test-matrix.txt",
    "requirements.txt",
    "README.md",
    "USER_GUIDE.md",
    "CHANGELOG.md",
    "docs/MACOS_SETUP.md",
    "docs/LINUX_SETUP.md",
    "LICENSE.txt",
    "VERSION.txt",
    "INSTALL_BFT.cmd",
    "INSTALL_BFT.command",
    "docs/INSTALLATION.md",
    ".pyprojectmgr/project_manifest.json",
    ".pyprojectmgr/project_spec.json",
    ".pyprojectmgr/setup_contribution.json",
    BUILD_RECORD,
    f"{BUILD_NAME}.bat",
)

ROOT_TREES = ("config", "docs/implementation", "launchers", "scripts", "src", "tests", "vendor")

INTEGRATIONS = (
    ("ppm", "src/configuration_hub/launcher.py"),
    ("ppm", "src/configuration_hub/providers.py"),
    ("ppm", "src/cli/cli_interface.py"),
    ("ppm", "config/config_hub_registry.json"),
    ("ppm", "tests/configuration_hub/test_pythermx_vertical_slice.py"),
    ("ppm", "tests/configuration_hub/test_config_hub_real_tk.py"),
    ("configeditor", "config_edit_hub.py"),
    ("configeditor", "config_edit_hub_tkinter.py"),
    ("configeditor", "tests/test_config_edit_hub.py"),
)

MARKERS = (
    "README.md|Bundle File Tool (BFT) creates, reviews, validates, and extracts",
    "USER_GUIDE.md|identifies BFT as the requester",
    "CHANGELOG.md|2.1.136",
    "LICENSE.txt|All rights reserved.",
    "VERSION.txt|2.1.136",
    r"scripts\setup_supported_envs.ps1|.venv311",
    r"src\core\module_ids.py|{manifest_hash}",
    r"src\core\service.py|class PlanEstimate",
    r"src\core\startup.py|def begin_gui_startup",
    r"src\ui\config_hub_launcher.py|--target-work-area=",
    r"src\ui\config_hub_launcher.py|_fallback_executable_dirs",
    r"launchers\macos\Bundle File Tool.app\Contents\MacOS\bft-gui|export PATH",
    r"launchers\macos\Bundle File Tool Web.app\Contents\MacOS\bft-web|export PATH",
    r".gitattributes|project_manifest.json -text",
    r"src\ui\log_viewer.py|class LogViewer",
    r"src\ui\log_viewer.py|path.stat().st_size > 0",
    r"src\ui\main_window.py|def menu_validate_bundle",
    r"src\ui\main_window.py|def menu_unbundle_clipboard",
    r"src\ui\main_window.py|apply_window_icon",
    r"src\ui\window_icon.py|def apply_window_icon",
    r"src\ui\assets\pysplashx_profile.json|Bundle File Tool Crex Startup",
    r"src\core\splash.py|def run_startup_splash",
    r"src\core\splash.py|place_process_tree_windows",
    r"src\railgun_display\resolver.py|def resolve_application_launch",
    r"src\railgun_display\windows.py|def place_process_tree_windows",
    r"src\main.py|launch_work_area",
    r"src\cli.py|--skip-splash",
    r"src\ui\config_hub_launcher.py|pysplashx",
    r"src\ui\main_window.py|def show_startup_preferences",
    r"src\core\checking.py|bft.check-result.v1",
    r"src\ui\selection_workspace.py|def check_selection",
    r"src\ui\workspace_layout.py|class WorkspaceLayout",
    r"src\railgun_display\resolver.py|def other_display",
    r"src\ui\unbundle_frame.py|def check_current_bundle",
    r"src\ui\check_results.py|class CheckResultsDialog",
    r"src\ui\check_preferences.py|class CheckPreferencesDialog",
    r"src\cli.py|def handle_check",
    r"src\web\server.py|LOOPBACK_HOST",
    r"src\web\adapter.py|class WebAdapter",
    r"src\web\jobs.py|class JobManager",
    r"src\web\static\index.html|browse-source",
    r"src\web\static\index.html|bft-web-mark.png",
    r"src\web\static\index.html|pysplashx-splash",
    r"src\web\static\index.html|replay-splash",
    r"src\web\static\app.js|api/dialogs",
    r"src\web\static\app.js|ensurePlanTargetsOutput",
    r"src\web\static\app.js|api/preferences/skin",
    r"src\web\static\app.js|NodeThermXWeb.WebThermometer",
    r"src\web\static\app.css|.skin-picker button.active",
    r"src\core\user_state.py|web_skin",
    r"src\web\static\nodethermx-web.js|global.NodeThermXWeb = api",
    r"src\web\static\nodethermx-web.css|thermx-indeterminate",
    r"src\web\static\pysplashx-splash.mjs|class PySplashXSplash",
    r"src\web\static\pysplashx-splash.css|position: fixed",
    r"src\web\server.py|def _send_media_bytes",
    r"vendor\NODETHERMX_LICENSE.txt|NodeThermX 0.3.0 Build 3",
    r"src\web_main.py|create_server",
    r"launchers\windows\Bundle File Tool.vbs|pythonw.exe",
    r"launchers\windows\Bundle File Tool Web.vbs|web_main.py",
    r"launchers\macos\Bundle File Tool.app\Contents\Info.plist|CFBundleExecutable",
    r"launchers\macos\Bundle File Tool Web.app\Contents\Info.plist|bft-web",
    r"src\ui\text_viewer.py|class TextFileViewer",
    r"tests\unit\test_logging.py|test_log_file_created_on_first_event",
    r"tests\unit\test_pythermx_tk_integration.py|test_no_cancel_dialog_maps_a_full_progress_canvas",
    r"tests\unit\test_ui_public_surface.py|test_native_ui_contains_no_public_placeholder_messages",
)


class DeliveryError(RuntimeError):
    """A delivery precondition was not met; nothing is written."""


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_lines(path: Path, lines: list[str]) -> None:
    """Match .NET WriteAllLines: UTF-8 without BOM, CRLF after every line."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes("".join(f"{line}\r\n" for line in lines).encode("utf-8"))


def remove_exact_build_directory(path: Path) -> None:
    expected_parent = (PROJECT_ROOT / "tmp").resolve()
    if path.parent.resolve() != expected_parent or path.name != BUILD_DIRECTORY:
        raise DeliveryError(f"Refusing to remove an unexpected delivery directory: {path}")
    if path.exists():
        shutil.rmtree(path)


def copy_relative_file(source_root: Path, relative: str, destination_root: Path) -> Path:
    source = source_root / relative
    if not source.is_file():
        raise DeliveryError(f"Required delivery source is missing: {source}")
    destination = destination_root / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return destination


def copy_relative_tree(relative_root: str, incoming_root: Path) -> None:
    source_root = PROJECT_ROOT / relative_root
    if not source_root.is_dir():
        raise DeliveryError(f"Required delivery tree is missing: {source_root}")
    for path in sorted(source_root.rglob("*")):
        if not path.is_file():
            continue
        parts = set(path.relative_to(PROJECT_ROOT).parts)
        if parts & EXCLUDED_DIRECTORIES or any(p.endswith(".egg-info") for p in parts):
            continue
        if path.suffix in EXCLUDED_SUFFIXES:
            continue
        copy_relative_file(PROJECT_ROOT, str(path.relative_to(PROJECT_ROOT)), incoming_root)


def build(output_directory: Path, suite_root: Path) -> Path:
    delivery_root = PROJECT_ROOT / "tmp" / BUILD_DIRECTORY
    incoming_root = delivery_root / "_bundletool_incoming"
    support_root = incoming_root / "_delivery"
    integration_root = incoming_root / "_integrations"

    ppm_root = suite_root / "pyprojectmgr_project" / "pyprojectmgrV2"
    config_editor_root = suite_root / "config_edit_project" / "config_edit_tool"
    for required in (ppm_root, config_editor_root):
        if not required.is_dir():
            raise DeliveryError(
                f"Required sibling project is missing: {required}\n"
                "Pass --suite-root if the suite lives elsewhere."
            )

    remove_exact_build_directory(delivery_root)
    for directory in (support_root, integration_root, output_directory):
        directory.mkdir(parents=True, exist_ok=True)

    for relative in ROOT_FILES:
        copy_relative_file(PROJECT_ROOT, relative, incoming_root)
    for tree in ROOT_TREES:
        copy_relative_tree(tree, incoming_root)

    integration_lines = []
    for key, relative in INTEGRATIONS:
        source_root = ppm_root if key == "ppm" else config_editor_root
        folder = "pyprojectmgr" if key == "ppm" else "configeditor"
        copied = copy_relative_file(source_root, relative, integration_root / folder)
        windows_relative = relative.replace("/", "\\")
        integration_lines.append(f"{sha256_of(copied)} {key} {windows_relative}")
    write_lines(support_root / "integration_manifest.sha256", integration_lines)

    payload = [
        path
        for path in incoming_root.rglob("*")
        if path.is_file() and support_root not in path.parents and integration_root not in path.parents
    ]
    manifest_lines = [
        f"{sha256_of(path)} {str(path.relative_to(incoming_root)).replace('/', chr(92))}"
        for path in sorted(payload, key=lambda p: str(p).lower())
    ]
    write_lines(support_root / "delivery_manifest.sha256", manifest_lines)

    manifest_hash = sha256_of(PROJECT_ROOT / ".pyprojectmgr" / "project_manifest.json")
    markers = [marker.replace("{manifest_hash}", manifest_hash) for marker in MARKERS]
    for marker in markers:
        text = marker.split("|", 1)[1]
        if '"' in text or "%" in text:
            raise DeliveryError(f"Batch-unsafe delivery marker: {marker}")
    write_lines(support_root / "delivery_markers.txt", markers)

    for top_level in (f"{BUILD_NAME}.bat", BUILD_RECORD, "INSTALL_BFT.cmd", "INSTALL_BFT.command"):
        source = PROJECT_ROOT / top_level
        if not source.is_file():
            raise DeliveryError(f"Required top-level delivery file is missing: {source}")
        shutil.copy2(source, delivery_root / top_level)

    zip_path = output_directory / f"{BUILD_NAME}.zip"
    sidecar_path = zip_path.with_name(zip_path.name + ".sha256")
    for stale in (zip_path, sidecar_path):
        if stale.exists():
            stale.unlink()

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(delivery_root.rglob("*"), key=lambda p: str(p).lower()):
            if path.is_file():
                archive.write(path, path.relative_to(delivery_root).as_posix())

    zip_hash = sha256_of(zip_path)
    sidecar_path.write_bytes(f"{zip_hash}  {zip_path.name}\r\n".encode("ascii"))

    print(f"Build 136 delivery: {zip_path}")
    print(f"SHA256 sidecar  : {sidecar_path}")
    print(f"BFT files      : {len(manifest_lines)}")
    print(f"Integration    : {len(integration_lines)}")
    print(f"SHA256         : {zip_hash}")
    return zip_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the Build 136 delivery kit.")
    parser.add_argument("--output-directory", default=str(PROJECT_ROOT / "tmp"))
    parser.add_argument(
        "--suite-root",
        default=str(PROJECT_ROOT.parents[1]),
        help="Directory holding pyprojectmgr_project and config_edit_project.",
    )
    args = parser.parse_args(argv)
    try:
        build(Path(args.output_directory).resolve(), Path(args.suite_root).resolve())
    except DeliveryError as failure:
        print(f"[FAIL] {failure}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
