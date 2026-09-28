"""Read-only log discovery contracts."""

from __future__ import annotations

import os

from ui.log_viewer import discover_log_files


def test_log_discovery_is_shallow_filtered_and_newest_first(tmp_path):
    older = tmp_path / "older.json"
    newer = tmp_path / "newer.log"
    empty = tmp_path / "empty.json"
    ignored = tmp_path / "payload.bin"
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "hidden.log").write_text("hidden", encoding="utf-8")
    older.write_text("old", encoding="utf-8")
    newer.write_text("new", encoding="utf-8")
    empty.touch()
    ignored.write_bytes(b"binary")
    os.utime(older, ns=(1_000_000_000, 1_000_000_000))
    os.utime(newer, ns=(2_000_000_000, 2_000_000_000))

    assert discover_log_files(tmp_path) == [newer, older]


def test_log_discovery_accepts_a_missing_directory(tmp_path):
    assert discover_log_files(tmp_path / "missing") == []
