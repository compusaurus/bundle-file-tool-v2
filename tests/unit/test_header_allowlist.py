# BFT_B109_HEADER_ALLOWLIST_TESTS
# ============================================================================
# SOURCEFILE: test_header_allowlist.py
# RELPATH: bundle_file_tool_v2/tests/unit/test_header_allowlist.py
# PROJECT: Bundle File Tool v2.1
# VERSION: 2.1.109
# LIFECYCLE: Testing
# STATUS: Build 109 - BFT_B109_HEADER_ALLOWLIST_TESTS
# ============================================================================
"""F-01 / Option B+: provenance headers only where `#` is a comment.

`BundleWriter.write_entry()` prepended a `#`-comment provenance block to every
text entry with no file-type check, and `add_headers` defaults to True. Any
format where `#` is not a line comment came out of an extraction unparseable —
JSON, XML, HTML, CSS, JavaScript, SQL.

George's ruling (`ARCH-RULING-2026-08-23-02` §2, F-01) adopts **Option B+**: a
governed allow-list of `#`-comment-compatible extensions and exact filenames,
case-normalised. Everything else is extracted byte-pure. `add_headers=True`
remains the shipped default, because with the allow-list in place it now injects
headers only where they are syntactically harmless.

The first test here reproduces the defect and is the one that failed before the
fix landed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.models import BundleEntry, BundleManifest
from core.writer import (
    HASH_COMMENT_EXTENSIONS,
    HASH_COMMENT_FILENAMES,
    BundleWriter,
    insert_provenance_header,
)


def _extract_one(tmp_path, path: str, content: str, add_headers: bool = True) -> str:
    """Extract a single entry with the DEFAULT header setting and return the file."""
    manifest = BundleManifest(
        entries=[BundleEntry(path=path, content=content)],
        profile="plain_marker",
    )
    out = tmp_path / "out"
    writer = BundleWriter(base_path=out, overwrite_policy="overwrite",
                          add_headers=add_headers)
    writer.extract_manifest(manifest, out)
    return (out / path).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. The defect, reproduced
# ---------------------------------------------------------------------------

def test_json_survives_extraction_under_the_default_setting(tmp_path):
    """The reproduction case. Failed before Option B+; passes after.

    Deliberately uses the default `add_headers=True`, because the whole defect
    was that the shipped default was the broken configuration and the historical
    round-trip suite only ever exercised the other one.
    """
    payload = '{\n  "version": "2.1.109",\n  "safety": {"allow_globs": ["**/*"]}\n}\n'
    extracted = _extract_one(tmp_path, "bundle_config.json", payload)

    parsed = json.loads(extracted)          # this raised before the fix
    assert parsed["version"] == "2.1.109"
    assert extracted == payload, "a non-comment format must be byte-pure"


@pytest.mark.parametrize("path,content", [
    ("data.json", '{"a": 1}\n'),
    ("page.html", "<!doctype html>\n<html></html>\n"),
    ("style.css", "body { color: #333; }\n"),
    ("app.js", "export const x = 1;\n"),
    ("query.sql", "SELECT 1;\n"),
    ("doc.xml", "<?xml version=\"1.0\"?>\n<root/>\n"),
    ("notes.md", "# Heading\n\nText.\n"),
    ("plain.txt", "just text\n"),
    ("main.c", "int main(void) { return 0; }\n"),
    ("LICENSE", "MIT License\n"),
])
def test_non_comment_formats_are_extracted_byte_pure(tmp_path, path, content):
    """No header, not one byte changed, at the default setting."""
    assert _extract_one(tmp_path, path, content) == content


# ---------------------------------------------------------------------------
# 2. Headers still land where they are valid
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path", [
    "module.py", "script.sh", "conf.yaml", "conf.yml", "pyproject.toml",
    "setup.cfg", "settings.ini", "task.ps1", "Dockerfile", "Makefile",
    ".env",
])
def test_hash_comment_formats_still_receive_the_provenance_block(tmp_path, path):
    """Team Directive v4 provenance is preserved wherever `#` is a comment."""
    extracted = _extract_one(tmp_path, path, "original content\n")

    assert extracted.startswith("# "), f"{path} lost its provenance header"
    assert "SOURCEFILE:" in extracted
    assert extracted.endswith("original content\n"), "payload was altered"
    assert all(line.startswith("#") or not line.strip()
               for line in extracted.split("original content")[0].splitlines()), \
        "header contained a non-comment line"


def test_dotfiles_named_after_an_allowed_extension_are_recognised(tmp_path):
    """`.env` is a name, not a suffix — `Path('.env').suffix` is empty.

    George's ruling lists `.env` among the extensions. Matching on suffix alone
    would silently miss it and leave `.env` files without provenance, so the
    lookup also treats a leading-dot filename as its own extension.
    """
    extracted = _extract_one(tmp_path, ".env", "TOKEN=abc\n")
    assert extracted.startswith("# ")
    assert extracted.endswith("TOKEN=abc\n")


# ---------------------------------------------------------------------------
# 2b. A shebang must stay on line 1
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path,shebang", [
    ("run.sh", "#!/usr/bin/env bash"),
    ("tool.py", "#!/usr/bin/env python3"),
    ("script.pl", "#!/usr/bin/perl"),
    ("task.rb", "#!/usr/bin/env ruby"),
])
def test_a_shebang_survives_header_injection(tmp_path, path, shebang):
    """Found while building the multi-format matrix, and worth stating plainly.

    Option B+ decides *whether* a `#` header is valid for a format; it does not
    decide *where* it goes. A shebang is a comment, so the allow-list is
    satisfied either way — but `#!` is only honoured by the kernel at byte 0.
    Prepending the block left valid syntax and an unexecutable script, which is
    the same class of harm F-01 was raised for.
    """
    body = f"{shebang}\necho ok\n" if path.endswith(".sh") else f"{shebang}\nx = 1\n"
    extracted = _extract_one(tmp_path, path, body)

    assert extracted.startswith(shebang + "\n"), "the shebang was displaced"
    assert "SOURCEFILE:" in extracted, "provenance was lost"
    assert extracted.rstrip().endswith(body.rstrip().splitlines()[-1])


def test_header_placement_helper_handles_the_edge_cases():
    header = "# HEADER\n"

    # ordinary file: header first
    assert insert_provenance_header("x = 1\n", header) == header + "x = 1\n"

    # shebang: header second, shebang untouched
    assert insert_provenance_header("#!/bin/sh\nx\n", header) == "#!/bin/sh\n" + header + "x\n"

    # a shebang with no trailing newline must not lose its line break
    assert insert_provenance_header("#!/bin/sh", header) == "#!/bin/sh\n" + header

    # a comment that is not a shebang is ordinary content
    assert insert_provenance_header("# note\n", header) == header + "# note\n"

    # empty content still receives provenance
    assert insert_provenance_header("", header) == header


# ---------------------------------------------------------------------------
# 3. Case normalisation and exact-filename rules
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path", ["MODULE.PY", "Script.SH", "Conf.YAML", "SETUP.CFG"])
def test_extension_matching_is_case_insensitive(tmp_path, path):
    assert _extract_one(tmp_path, path, "x\n").startswith("# ")


@pytest.mark.parametrize("path", ["dockerfile", "DOCKERFILE", "Makefile", "makefile",
                                  "Gemfile", "Vagrantfile", "inventory"])
def test_exact_filenames_are_matched_case_insensitively(tmp_path, path):
    assert _extract_one(tmp_path, path, "x\n").startswith("# ")


@pytest.mark.parametrize("path", ["DATA.JSON", "Page.HTML", "STYLE.CSS"])
def test_non_comment_extensions_are_skipped_case_insensitively(tmp_path, path):
    assert _extract_one(tmp_path, path, "x\n") == "x\n"


def test_a_nested_path_is_judged_by_its_own_name(tmp_path):
    """The decision is per file, not per directory."""
    assert _extract_one(tmp_path, "src/core/thing.py", "x\n").startswith("# ")
    assert _extract_one(tmp_path, "src/core/thing.json", "x\n") == "x\n"


# ---------------------------------------------------------------------------
# 4. The governed lists themselves
# ---------------------------------------------------------------------------

def test_the_allow_lists_match_the_ratified_sets():
    """Bound to ARCH-RULING-2026-08-23-02 §2 so a silent edit fails a test."""
    assert HASH_COMMENT_EXTENSIONS == frozenset({
        ".py", ".pyw", ".sh", ".bash", ".zsh", ".ksh", ".csh",
        ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
        ".r", ".rb", ".pl", ".pm", ".tcl", ".dockerfile",
        ".env", ".properties", ".ps1", ".psm1",
    })
    assert HASH_COMMENT_FILENAMES == frozenset({
        "dockerfile", "makefile", "gemfile", "vagrantfile", "inventory",
    })


def test_the_governed_lists_are_stored_normalised():
    """Lookup lowercases the candidate, so the sets must be lowercase too."""
    assert all(e == e.lower() for e in HASH_COMMENT_EXTENSIONS)
    assert all(n == n.lower() for n in HASH_COMMENT_FILENAMES)
    assert all(e.startswith(".") for e in HASH_COMMENT_EXTENSIONS)


def test_no_structured_format_leaked_into_the_allow_list():
    """A guard against a future well-meaning addition that breaks parsing."""
    forbidden = {".json", ".xml", ".html", ".htm", ".css", ".js", ".ts",
                 ".sql", ".c", ".cpp", ".h", ".java", ".csv", ".md"}
    assert not (HASH_COMMENT_EXTENSIONS & forbidden)


# ---------------------------------------------------------------------------
# 5. Binary and opt-out paths are unchanged
# ---------------------------------------------------------------------------

def test_binary_entries_are_untouched(tmp_path):
    import base64

    raw = bytes(range(256))
    manifest = BundleManifest(
        entries=[BundleEntry(path="blob.png",
                             content=base64.b64encode(raw).decode("ascii"),
                             is_binary=True)],
        profile="plain_marker",
    )
    out = tmp_path / "out"
    BundleWriter(base_path=out, overwrite_policy="overwrite",
                 add_headers=True).extract_manifest(manifest, out)

    assert (out / "blob.png").read_bytes() == raw


def test_add_headers_false_still_suppresses_everything(tmp_path):
    """The opt-out keeps working for callers that require byte-for-byte output."""
    assert _extract_one(tmp_path, "module.py", "x\n", add_headers=False) == "x\n"
