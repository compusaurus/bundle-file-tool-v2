"""Static browser shell contracts that do not need a browser driver."""

from __future__ import annotations

import hashlib
from pathlib import Path
import tomllib


ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "src" / "web" / "static"


def test_working_surface_has_all_local_path_selectors():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    for control in (
        "browse-source-folder", "browse-source-file",
        "browse-bundle-output", "browse-bundle-path", "browse-extract-output",
    ):
        assert f'id="{control}"' in html
    assert 'id="browse-source"' not in html
    assert "Browse folders…" in html
    assert "Browse files…" in html
    assert html.count("Browse…") == 3


def test_source_picker_is_direct_and_invalidates_a_stale_plan():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    javascript = (STATIC / "app.js").read_text(encoding="utf-8")
    assert "source-kind-menu" not in html
    assert 'choosePath("folder", "source-path", "Choose source folder")' in javascript
    assert 'choosePath("file", "source-path", "Choose source file")' in javascript
    assert 'byId("source-path").addEventListener("input", invalidateSourcePlan)' in javascript
    assert "function invalidateSourcePlan()" in javascript


def test_static_shell_obeys_no_inline_script_policy_and_escapes_dynamic_text():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    javascript = (STATIC / "app.js").read_text(encoding="utf-8")
    splash_stylesheet = '<link rel="stylesheet" href="assets/pysplashx-splash.css">'
    thermx_script = '<script src="assets/nodethermx-web.js" defer></script>'
    splash_script = '<script type="module" src="assets/pysplashx-splash.mjs"></script>'
    app_script = '<script src="assets/app.js" defer></script>'
    assert thermx_script in html
    # The splash component loads this inside its shadow root. Loading it in the
    # document would apply its absolute-positioned Skip button rules to all buttons.
    assert splash_stylesheet not in html
    assert splash_script in html
    assert app_script in html
    assert html.index(thermx_script) < html.index(app_script)
    assert "onclick=" not in html
    assert ".innerHTML" not in javascript
    assert ".textContent" in javascript


def test_two_web_skins_and_long_path_displays_are_first_class_controls():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    javascript = (STATIC / "app.js").read_text(encoding="utf-8")
    stylesheet = (STATIC / "app.css").read_text(encoding="utf-8")

    assert 'data-skin="studio"' in html
    assert 'data-skin="midnight"' in html
    assert ':root[data-skin="midnight"]' in stylesheet
    assert 'id="source-path-preview"' in html
    assert "overflow-wrap: anywhere" in stylesheet
    assert 'cell.className = "path-cell"' in javascript
    assert 'cell.title = value' in javascript
    assert 'request("api/preferences/skin"' in javascript


def test_custom_web_identity_assets_are_real_local_pngs():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    for name in ("bft-web-mark.png", "bft-web-icon.png"):
        payload = (STATIC / name).read_bytes()
        assert payload.startswith(b"\x89PNG\r\n\x1a\n")
        assert len(payload) > 10_000
        assert f"assets/{name}" in html


def test_web_splash_uses_packaged_pysplashx_component_and_crex_media():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    component = STATIC / "pysplashx-splash.mjs"
    stylesheet = STATIC / "pysplashx-splash.css"
    javascript = (STATIC / "app.js").read_text(encoding="utf-8")

    assert component.is_file() and stylesheet.is_file()
    assert 'new URL("./pysplashx-splash.css", import.meta.url)' in component.read_text(
        encoding="utf-8"
    )
    assert "<style>" not in component.read_text(encoding="utf-8")
    splash_css = stylesheet.read_text(encoding="utf-8")
    assert ":host {" in splash_css
    assert "pysplashx-splash," in splash_css
    assert "position: fixed" in splash_css
    assert "z-index: 2147483647" in splash_css
    assert ":host([hidden])" in splash_css
    assert "<pysplashx-splash" in html
    assert 'enabled="false"' in html
    assert 'Object.entries(data.splash || {})' in javascript
    assert 'shape="rounded"' not in html
    assert 'once-per-session="false"' in html
    assert 'id="replay-splash"' in html
    assert "pysplashx-splash.mjs" in html
    assert "function replaySplash()" in javascript
    assert 'byId("replay-splash").addEventListener("click", replaySplash)' in javascript


def test_completed_plan_enables_create_and_defers_output_selection_to_click():
    javascript = (STATIC / "app.js").read_text(encoding="utf-8")

    assert 'byId("create-bundle").disabled = !state.plan' in javascript
    gate = javascript.split('byId("create-bundle").disabled = ', 1)[1].split(";", 1)[0]
    assert "bundle-output" not in gate
    assert 'outputPath = await choosePath("save", "bundle-output"' in javascript
    assert "await ensurePlanTargetsOutput(outputPath)" in javascript
    assert 'output_path: outputPath' in javascript


def test_web_progress_uses_the_governed_nodethermx_distribution():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    javascript = (STATIC / "app.js").read_text(encoding="utf-8")
    stylesheet = (STATIC / "app.css").read_text(encoding="utf-8")
    assets = {
        "nodethermx-web.js": "10f654b2dc936a8b99394629b1e1dbb122dbb7ab7038dedd8eab786ba434cb62",
        "nodethermx-web.css": "8d1b844c32c328b4a830fb668d17a515d270febded626e2a3ff237b1dcc933ff",
    }

    for name, expected in assets.items():
        assert hashlib.sha256((STATIC / name).read_bytes()).hexdigest() == expected
        assert f'assets/{name}' in html
    assert "new window.NodeThermXWeb.WebThermometer" in javascript
    assert 'state_version: "1.1"' in javascript
    assert 'cancellation_state: cancellationState' in javascript
    assert 'terminal_outcome: terminalOutcome' in javascript
    assert "progress-fill" not in html
    assert "progress-track" not in stylesheet
    assert (ROOT / "vendor" / "NODETHERMX_LICENSE.txt").is_file()


def test_packaging_includes_web_entry_point_package_and_assets():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["scripts"]["bft-web"] == "web_main:main"
    assert "web*" in project["tool"]["setuptools"]["packages"]["find"]["include"]
    assert set(project["tool"]["setuptools"]["package-data"]["web"]) == {
        "static/*.html", "static/*.css", "static/*.js", "static/*.mjs",
        "static/*.png"}


def test_tk_tools_menu_exposes_web_workspace():
    source = (ROOT / "src" / "ui" / "main_window.py").read_text(encoding="utf-8")
    assert 'label="Open Web Workspace..."' in source
    assert "def menu_open_web_workspace" in source
    assert 'project_root / "src" / "web_main.py"' in source
