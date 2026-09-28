# BFT_B109_MULTIFORMAT_ROUNDTRIP_DEFAULT
# ============================================================================
# SOURCEFILE: test_multiformat_roundtrip_default.py
# RELPATH: bundle_file_tool_v2/tests/integration/test_multiformat_roundtrip_default.py
# PROJECT: Bundle File Tool v2.1
# VERSION: 2.1.109
# LIFECYCLE: Testing
# STATUS: Build 109 - BFT_B109_MULTIFORMAT_ROUNDTRIP_DEFAULT
# ============================================================================
"""The control that was missing: round-trip fidelity at the DEFAULT setting.

`ARCH-RULING-2026-08-23-02` §4 item 2 mandates this suite. It exists because of
how F-01 survived for so long: every test in `tests/unit/test_roundtrip.py`
constructs `BundleWriter(..., add_headers=False)`, which its own header records
deliberately, so that byte-for-byte assertions would hold. The consequence was
that fidelity was proven only in a configuration users do not run.

So this suite changes nothing about the configuration. It bundles and extracts
through the real CLI with no format flags and no `--no-headers`, exactly as an
operator would, and then checks each file with its own native parser.

Structured formats must be byte-pure. `#`-comment formats must carry the
provenance block and an unaltered payload. Binaries must be byte-identical.
"""

from __future__ import annotations

import ast
import configparser
import csv
import io
import json
import os
import subprocess
import sys
import tomllib
import xml.etree.ElementTree as ElementTree
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src"

# --- the synthetic repository ----------------------------------------------
# Every value is content a native parser can verify, not filler.

TEXT_FILES = {
    # path                     content
    "src/app.py":              "import sys\n\n\ndef main() -> int:\n    return 0\n",
    "scripts/run.sh":          "#!/usr/bin/env bash\nset -euo pipefail\necho ok\n",
    "config/settings.yaml":    "service:\n  name: bundle-tool\n  retries: 3\n",
    "config/alt.yml":          "enabled: true\n",
    "pyproject.toml":          '[project]\nname = "sample"\nversion = "1.0.0"\n',
    "setup.cfg":               "[metadata]\nname = sample\n",
    "config/app.ini":          "[server]\nhost = localhost\nport = 8080\n",
    "tools/task.ps1":          "Write-Output 'ok'\n",
    "Dockerfile":              "FROM python:3.11-slim\nWORKDIR /app\n",
    "Makefile":                "all:\n\techo ok\n",
    ".env":                    "TOKEN=abc123\nDEBUG=1\n",
    "data/records.json":       '{\n  "items": [1, 2, 3],\n  "ok": true\n}\n',
    "data/feed.xml":           '<?xml version="1.0" encoding="UTF-8"?>\n<feed><item id="1"/></feed>\n',
    "web/index.html":          "<!doctype html>\n<html><body><p>hi</p></body></html>\n",
    "web/site.css":            "body { color: #222; margin: 0; }\n",
    "web/main.js":             "export const answer = 42;\n",
    "db/schema.sql":           "CREATE TABLE t (id INTEGER PRIMARY KEY);\n",
    "data/rows.csv":           "id,name\n1,alpha\n2,beta\n",
    "README.md":               "# Sample\n\nA line of prose.\n",
    "notes.txt":               "plain text, unchanged\n",
    "LICENSE":                 "MIT License\n\nPermission is hereby granted.\n",
    "src/native.c":            "int main(void) { return 0; }\n",
}

BINARY_FILES = {
    # a real PNG header plus arbitrary bytes, and a plain binary blob
    "assets/logo.png": bytes.fromhex("89504e470d0a1a0a") + bytes(range(64)),
    "assets/blob.bin": bytes(range(256)),
}

# Files that must carry a provenance header after extraction.
EXPECT_HEADER = {
    "src/app.py", "scripts/run.sh", "config/settings.yaml", "config/alt.yml",
    "pyproject.toml", "setup.cfg", "config/app.ini", "tools/task.ps1",
    "Dockerfile", "Makefile", ".env",
}

# Everything else in TEXT_FILES must come back byte-for-byte identical.
EXPECT_BYTE_PURE = set(TEXT_FILES) - EXPECT_HEADER


@pytest.fixture(scope="module")
def round_trip(tmp_path_factory):
    """Bundle and extract the synthetic repo through the CLI, using defaults."""
    base = tmp_path_factory.mktemp("multiformat")
    source, out = base / "source", base / "extracted"
    source.mkdir()

    for rel, text in TEXT_FILES.items():
        target = source / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8", newline="")
    for rel, raw in BINARY_FILES.items():
        target = source / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)

    # a wheel, to confirm governed safety policy still excludes it
    (source / "assets" / "pkg-1.0-py3-none-any.whl").write_bytes(b"PK\x03\x04stub")

    bundle = base / "sample.txt"
    env = {**os.environ, "PYTHONPATH": str(SRC)}

    made = subprocess.run(
        [sys.executable, "-m", "cli", "bundle", str(source),
         "--base-path", str(source), "-o", str(bundle), "--progress", "none"],
        cwd=str(SRC), capture_output=True, text=True, env=env)
    assert made.returncode == 0, made.stderr

    # No --no-headers. No --profile. The default configuration, as shipped.
    taken = subprocess.run(
        [sys.executable, "-m", "cli", "unbundle", str(bundle),
         "-o", str(out), "--overwrite", "overwrite", "--progress", "none"],
        cwd=str(SRC), capture_output=True, text=True, env=env)
    assert taken.returncode == 0, taken.stderr

    return {"source": source, "out": out, "bundle": bundle}


def _payload_after_header(text: str) -> str:
    """Recover the original payload from an extracted file.

    A shebang is retained on line 1 with the provenance block inserted beneath
    it, so the shebang must be put back rather than counted as header.
    """
    shebang = ""
    if text.startswith("#!"):
        cut = text.find("\n")
        shebang, text = text[:cut + 1], text[cut + 1:]

    lines = text.splitlines(keepends=True)
    index = 0
    while index < len(lines) and lines[index].lstrip().startswith("#"):
        index += 1
    while index < len(lines) and not lines[index].strip():
        index += 1
    return shebang + "".join(lines[index:])


# ---------------------------------------------------------------------------
# 1. Every file survived the trip
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("rel", sorted(TEXT_FILES))
def test_every_text_file_is_extracted(round_trip, rel):
    assert (round_trip["out"] / rel).is_file(), f"{rel} missing after extraction"


@pytest.mark.parametrize("rel", sorted(BINARY_FILES))
def test_every_binary_file_is_extracted(round_trip, rel):
    assert (round_trip["out"] / rel).is_file(), f"{rel} missing after extraction"


# ---------------------------------------------------------------------------
# 2. Structured formats parse with their native engines
# ---------------------------------------------------------------------------

def test_json_parses_and_keeps_its_values(round_trip):
    parsed = json.loads((round_trip["out"] / "data/records.json").read_text(encoding="utf-8"))
    assert parsed == {"items": [1, 2, 3], "ok": True}


def test_xml_parses(round_trip):
    root = ElementTree.fromstring((round_trip["out"] / "data/feed.xml").read_text(encoding="utf-8"))
    assert root.tag == "feed"
    assert root.find("item").get("id") == "1"


def test_toml_parses(round_trip):
    data = tomllib.loads((round_trip["out"] / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["name"] == "sample"


def test_ini_and_cfg_parse(round_trip):
    parser = configparser.ConfigParser()
    parser.read_string((round_trip["out"] / "config/app.ini").read_text(encoding="utf-8"))
    assert parser["server"]["port"] == "8080"

    cfg = configparser.ConfigParser()
    cfg.read_string((round_trip["out"] / "setup.cfg").read_text(encoding="utf-8"))
    assert cfg["metadata"]["name"] == "sample"


def test_python_parses(round_trip):
    tree = ast.parse((round_trip["out"] / "src/app.py").read_text(encoding="utf-8"))
    assert any(isinstance(n, ast.FunctionDef) and n.name == "main"
               for n in ast.walk(tree))


def test_csv_parses(round_trip):
    text = (round_trip["out"] / "data/rows.csv").read_text(encoding="utf-8")
    rows = list(csv.DictReader(io.StringIO(text)))
    assert [r["name"] for r in rows] == ["alpha", "beta"]


def test_yaml_parses(round_trip):
    """Both YAML files, including the one that legitimately gains a header.

    A `#` block is valid YAML, so the header must not stop the document
    parsing — which is precisely why `.yaml` belongs on the allow-list.
    """
    yaml = pytest.importorskip("yaml")

    settings = yaml.safe_load((round_trip["out"] / "config/settings.yaml").read_text(encoding="utf-8"))
    assert settings["service"]["name"] == "bundle-tool"
    assert settings["service"]["retries"] == 3

    alt = yaml.safe_load((round_trip["out"] / "config/alt.yml").read_text(encoding="utf-8"))
    assert alt == {"enabled": True}


# ---------------------------------------------------------------------------
# 3. Byte purity where no header belongs
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("rel", sorted(EXPECT_BYTE_PURE))
def test_non_comment_formats_are_byte_identical(round_trip, rel):
    assert (round_trip["out"] / rel).read_bytes() == (round_trip["source"] / rel).read_bytes(), \
        f"{rel} was modified during the round trip"


@pytest.mark.parametrize("rel", sorted(BINARY_FILES))
def test_binaries_are_byte_identical(round_trip, rel):
    assert (round_trip["out"] / rel).read_bytes() == BINARY_FILES[rel]


# ---------------------------------------------------------------------------
# 4. Provenance where it is valid
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("rel", sorted(EXPECT_HEADER))
def test_hash_comment_formats_carry_provenance_and_keep_their_payload(round_trip, rel):
    extracted = (round_trip["out"] / rel).read_text(encoding="utf-8")

    assert extracted.startswith("#"), f"{rel} lost its provenance header"
    assert "SOURCEFILE:" in extracted
    assert _payload_after_header(extracted) == TEXT_FILES[rel], \
        f"{rel} payload was altered beneath the header"


def test_no_extracted_file_begins_with_a_stray_comment(round_trip):
    """The inverse check: nothing outside the allow-list gained a header."""
    offenders = []
    for rel in sorted(EXPECT_BYTE_PURE):
        text = (round_trip["out"] / rel).read_text(encoding="utf-8")
        if text.startswith("# ") and "SOURCEFILE:" in text[:600]:
            offenders.append(rel)
    assert not offenders, f"provenance header leaked into: {offenders}"


# ---------------------------------------------------------------------------
# 5. Governed safety policy is still in force during the round trip
# ---------------------------------------------------------------------------

def test_the_wheel_was_excluded_by_governed_deny_policy(round_trip):
    """`**/*.whl` was ratified onto the deny list in Build 107.

    It is asserted here rather than assumed: a round-trip suite that silently
    started carrying wheels would be evidence the deny list had stopped working.
    """
    assert not (round_trip["out"] / "assets/pkg-1.0-py3-none-any.whl").exists()
    assert "pkg-1.0-py3-none-any.whl" not in round_trip["bundle"].read_text(encoding="utf-8")
