"""Filesystem safety and rollback contracts for fresh/upgrade deliveries."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("bft_installer", ROOT / "scripts/install_bft.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


def make_payload(root, version="2.1.132", extra=None):
    content = {"src/main.py": "# gui\n", "src/cli.py": "# cli\n", "VERSION.txt": version,
               "bundle_config.json": json.dumps({"version": version, "safety": {"enabled": True}}),
               ".pyprojectmgr/project_manifest.json": "{}", "pyproject.toml": "# package\n"}
    content.update(extra or {})
    lines = []
    for name, text in content.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        lines.append(hashlib.sha256(target.read_bytes()).hexdigest() + " " + name)
    (root / installer.MANIFEST).parent.mkdir(parents=True)
    (root / installer.MANIFEST).write_text("\n".join(lines), encoding="utf-8")
    return root


@pytest.fixture
def stub_runtime(monkeypatch):
    monkeypatch.setattr(installer, "prepare_runtime", lambda source, destination, runtime, report:
                        runtime / "bin/python")
    monkeypatch.setattr(installer, "validate_runtime", lambda *args: None)


def test_fresh_then_upgrade_preserves_unowned_files_and_backs_up_prior_build(tmp_path, stub_runtime):
    first = make_payload(tmp_path / "delivery131", "2.1.131")
    second = make_payload(tmp_path / "delivery132")
    target = tmp_path / "A fresh folder with spaces"
    old = installer.install(first, target, "fresh")
    (target / "INSTALL_BUNDLETOOL_prior.bat").write_text("old installer")
    (target / "my bundle.txt").write_text("user content")
    (target / ".bft_user_state.json").write_text('{"remember":true}')
    new = installer.install(second, target, "upgrade")
    assert (target / "VERSION.txt").read_text() == "2.1.132"
    assert (target / "my bundle.txt").read_text() == "user content"
    assert (target / ".bft_user_state.json").read_text() == '{"remember":true}'
    assert (Path(new["backup"]) / "VERSION.txt").read_text() == "2.1.131"
    assert old["runtime"] != new["runtime"]
    assert not (target / "INSTALL_BUNDLETOOL_prior.bat").exists()
    assert (Path(new["backup"]) / "INSTALL_BUNDLETOOL_prior.bat").read_text() == "old installer"


def test_runtime_failure_restores_program_and_active_runtime(tmp_path, stub_runtime, monkeypatch):
    first = make_payload(tmp_path / "delivery131", "2.1.131")
    second = make_payload(tmp_path / "delivery132")
    target = tmp_path / "installed"
    installer.install(first, target, "fresh")
    before = {p: (target / p).read_bytes() for p in
              [*installer.payload_files(first), installer.RUNTIME_POINTER, installer.RECEIPT]}
    def fail(*args):
        raise RuntimeError("Tk runtime failed")
    monkeypatch.setattr(installer, "validate_runtime", fail)
    with pytest.raises(RuntimeError, match="Tk runtime failed"):
        installer.install(second, target, "upgrade")
    assert before == {p: (target / p).read_bytes() for p in before}


def test_tampered_payload_fails_before_creating_destination(tmp_path, stub_runtime):
    source = make_payload(tmp_path / "delivery")
    (source / "src/main.py").write_text("tampered")
    target = tmp_path / "target"
    with pytest.raises(ValueError, match="checksum"):
        installer.install(source, target, "fresh")
    assert not target.exists()


@pytest.mark.parametrize("name", ["../outside", "C:/outside", "src/main.py:stream", "src/MAIN.py"])
def test_escaping_and_duplicate_payload_paths_are_rejected(tmp_path, name):
    source = make_payload(tmp_path / "delivery")
    with (source / installer.MANIFEST).open("a") as stream:
        stream.write("\n" + "0" * 64 + " " + name)
    with pytest.raises(ValueError, match="Invalid or duplicate"):
        installer.payload_files(source)


def test_fresh_refuses_nonempty_folder_and_upgrade_refuses_unrelated_folder(tmp_path, stub_runtime):
    source = make_payload(tmp_path / "delivery")
    target = tmp_path / "unrelated"
    target.mkdir()
    (target / "personal.txt").write_text("retain")
    for mode, message in (("fresh", "new or empty"), ("upgrade", "existing BFT")):
        with pytest.raises(ValueError, match=message):
            installer.install(source, target, mode)
    assert list(target.iterdir()) == [target / "personal.txt"]


def test_governed_settings_require_explicit_replacement_and_are_backed_up(tmp_path, stub_runtime):
    source = make_payload(tmp_path / "delivery")
    target = tmp_path / "installed"
    installer.install(source, target, "fresh")
    config = target / "bundle_config.json"
    config.chmod(0o644)
    config.write_text('{"version":"2.1.132","safety":{"enabled":false}}')
    customized = config.read_bytes()
    with pytest.raises(ValueError, match="Governed settings differ"):
        installer.install(source, target, "upgrade")
    assert config.read_bytes() == customized
    receipt = installer.install(source, target, "upgrade", replace_settings=True)
    assert (Path(receipt["backup"]) / "bundle_config.json").read_bytes() == customized


@pytest.mark.parametrize("name", ["config/pythermx_profile.json", "src/ui/assets/pysplashx_profile.json"])
def test_profile_defaults_upgrade_but_customizations_require_explicit_replacement(tmp_path, stub_runtime, name):
    first = make_payload(tmp_path / "first", "2.1.132", {name: '{"enabled":true}'})
    second = make_payload(tmp_path / "second", "2.1.133", {name: '{"enabled":false}'})
    target = tmp_path / "installed"
    installer.install(first, target, "fresh")
    # An untouched prior default should receive the corrected release default.
    installer.install(second, target, "upgrade")
    assert (target / name).read_text() == '{"enabled":false}'
    (target / name).write_text('{"enabled":true,"custom":true}')
    customized = (target / name).read_bytes()
    with pytest.raises(ValueError, match="Customized settings profile"):
        installer.install(second, target, "upgrade")
    assert (target / name).read_bytes() == customized
    receipt = installer.install(second, target, "upgrade", replace_settings=True)
    assert (Path(receipt["backup"]) / name).read_bytes() == customized


def test_upgrade_refuses_destination_links(tmp_path, stub_runtime, monkeypatch):
    source = make_payload(tmp_path / "delivery")
    target = tmp_path / "installed"
    installer.install(source, target, "fresh")
    original = installer.linked
    monkeypatch.setattr(installer, "linked", lambda p, boundary:
                        p == target / "src/main.py" or original(p, boundary))
    with pytest.raises(ValueError, match="linked destination"):
        installer.install(source, target, "upgrade")
