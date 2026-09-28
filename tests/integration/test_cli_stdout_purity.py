# BFT_B105_STDOUT_PURITY_TESTS
# ============================================================================
# SOURCEFILE: test_cli_stdout_purity.py
# RELPATH: bundle_file_tool_v2/tests/integration/test_cli_stdout_purity.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.105
# LIFECYCLE: Testing
# STATUS: Build 105 - BFT_B105_STDOUT_PURITY_TESTS
# DESCRIPTION: stdout carries the bundle and nothing else.
# ============================================================================
"""The bundle command must produce a byte-pure artifact on stdout.

Paul's Build 104 review, blocker 3. `bundle` wrote `Discovering files...`,
`Found N files` and `Creating bundle with profile ...` to stdout with ordinary
`print()`, then wrote the bundle body to the same stream when `--output` was
omitted. A successful command therefore emitted diagnostics and payload
interleaved, and the pre-existing test only looked for a marker *somewhere* in
stdout rather than parsing the whole captured stream.

These tests capture both streams and compare stdout with the formatter's own
output byte for byte.
"""

from __future__ import annotations

import sys

import pytest

import cli
from core.models import BundleEntry, BundleManifest
from core.parser import BundleParser, ProfileRegistry


@pytest.fixture
def source_tree(tmp_path):
    root = tmp_path / "proj"
    (root / "pkg").mkdir(parents=True)
    (root / "app.py").write_bytes(b"VALUE = 1\n")
    (root / "pkg" / "util.py").write_bytes(b"def f():\n    return 2\n")
    return root


def _run_bundle(monkeypatch, argv):
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 0, "bundle command failed"


@pytest.mark.parametrize("profile_name", ["plain_marker", "md_fence"])
def test_stdout_is_exactly_the_bundle_and_nothing_else(
        monkeypatch, capsys, source_tree, profile_name):
    _run_bundle(monkeypatch, [
        "bundle-tool", "bundle", str(source_tree),
        "--profile", profile_name, "--base-path", str(source_tree),
        "--include", "**/*.py",
    ])
    captured = capsys.readouterr()

    # rebuild the expected artifact independently of the CLI
    entries = []
    for rel in ("app.py", "pkg/util.py"):
        entries.append(BundleEntry(
            path=rel, content=(source_tree / rel).read_bytes().decode("utf-8"),
            is_binary=False, encoding="utf-8", eol_style="LF", checksum=None,
            file_size_bytes=(source_tree / rel).stat().st_size))
    expected = ProfileRegistry().get(profile_name).format_manifest(
        BundleManifest(entries=entries, profile=profile_name))

    assert captured.out == expected, "stdout is not byte-identical to the formatted bundle"


@pytest.mark.parametrize("profile_name", ["plain_marker", "md_fence"])
def test_stdout_parses_back_cleanly(monkeypatch, capsys, source_tree, profile_name):
    _run_bundle(monkeypatch, [
        "bundle-tool", "bundle", str(source_tree),
        "--profile", profile_name, "--base-path", str(source_tree),
        "--include", "**/*.py",
    ])
    stdout = capsys.readouterr().out

    manifest = BundleParser().parse(stdout, profile_name=profile_name)
    assert {e.path for e in manifest.entries} == {"app.py", "pkg/util.py"}


def test_progress_and_status_go_to_stderr(monkeypatch, capsys, source_tree):
    _run_bundle(monkeypatch, [
        "bundle-tool", "bundle", str(source_tree),
        "--profile", "plain_marker", "--base-path", str(source_tree),
        "--include", "**/*.py",
    ])
    captured = capsys.readouterr()

    assert "Discovering files" in captured.err
    assert "Found" in captured.err
    assert "Creating bundle with profile" in captured.err

    for noise in ("Discovering files", "Found ", "Creating bundle with profile"):
        assert noise not in captured.out, f"diagnostic leaked onto stdout: {noise!r}"


def test_no_diagnostics_leak_when_writing_to_a_file(monkeypatch, capsys, source_tree, tmp_path):
    out_file = tmp_path / "bundle.txt"
    _run_bundle(monkeypatch, [
        "bundle-tool", "bundle", str(source_tree), "--output", str(out_file),
        "--profile", "plain_marker", "--base-path", str(source_tree),
        "--include", "**/*.py",
    ])
    captured = capsys.readouterr()

    # with --output, stdout carries nothing at all
    assert captured.out == ""
    assert "Bundle created" in captured.err
    assert out_file.exists()

    manifest = BundleParser().parse_file(out_file, profile_name="plain_marker")
    assert len(manifest.entries) == 2


def test_piped_stdout_survives_a_marker_bearing_source(monkeypatch, capsys, tmp_path):
    """The self-hosting case: a file whose body contains transport markers."""
    root = tmp_path / "proj"
    root.mkdir()
    sep = "# " + "=" * 67
    (root / "fixture.py").write_text(
        "SAMPLE = '''\n" + sep + "\n# FILE: src/example.py\n"
        "# META: encoding=utf-8; eol=LF; mode=text\n" + sep + "\nprint(1)\n'''\n",
        encoding="utf-8")

    _run_bundle(monkeypatch, [
        "bundle-tool", "bundle", str(root),
        "--profile", "plain_marker", "--base-path", str(root), "--include", "**/*.py",
    ])
    stdout = capsys.readouterr().out

    manifest = BundleParser().parse(stdout, profile_name="plain_marker")
    assert [e.path for e in manifest.entries] == ["fixture.py"]
