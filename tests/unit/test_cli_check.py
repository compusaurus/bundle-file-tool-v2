"""Build 125 CLI coverage for the shared integrity-check contract."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from cli import build_parser, handle_check, handle_unbundle
from core.exceptions import ValidationError
from core.models import BundleEntry, BundleManifest
from core.profiles.plain_marker import PlainMarkerProfile


def _write_bundle(path, entries):
    manifest = BundleManifest(entries=list(entries), profile="plain_marker")
    path.write_text(
        PlainMarkerProfile().format_manifest(manifest),
        encoding="utf-8",
        newline="",
    )


def _check_args(path, *, format="text"):
    return SimpleNamespace(
        input_file=path,
        profile=None,
        encoding=None,
        progress="none",
        format=format,
    )


def test_parser_exposes_structured_check_command():
    args = build_parser().parse_args(["check", "sample.txt", "--format", "json"])
    assert args.command == "check"
    assert args.format == "json"


def test_check_json_is_machine_readable(tmp_path, capsys):
    bundle = tmp_path / "clean.txt"
    _write_bundle(bundle, [BundleEntry(path="src/a.txt", content="hello\n")])

    handle_check(_check_args(bundle, format="json"))

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "passed"
    assert payload["valid"] is True
    assert payload["file_count"] == 1
    assert payload["findings"] == []


def test_check_blocks_confirmed_nested_bundle(tmp_path, capsys):
    inner = PlainMarkerProfile().format_manifest(BundleManifest(
        entries=[BundleEntry(path="inside.txt", content="inside\n")],
        profile="plain_marker",
    ))
    outer = tmp_path / "outer.txt"
    _write_bundle(outer, [BundleEntry(path="demo.txt", content=inner)])

    with pytest.raises(SystemExit) as raised:
        handle_check(_check_args(outer))

    assert raised.value.code == 1
    assert "NESTED_BUNDLE_CONTENT" in capsys.readouterr().out


def test_unbundle_cannot_bypass_shared_check(tmp_path):
    inner = PlainMarkerProfile().format_manifest(BundleManifest(
        entries=[BundleEntry(path="inside.txt", content="inside\n")],
        profile="plain_marker",
    ))
    outer = tmp_path / "outer.txt"
    _write_bundle(outer, [BundleEntry(path="demo.txt", content=inner)])

    args = SimpleNamespace(
        input_file=outer,
        output=tmp_path / "out",
        profile=None,
        encoding=None,
        overwrite="overwrite",
        dry_run=False,
        no_headers=True,
        progress="none",
    )
    with pytest.raises(ValidationError, match="NESTED_BUNDLE_CONTENT"):
        handle_unbundle(args)

