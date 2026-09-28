# BFT_B114_CLI_PLAN_RENDERING_TESTS
# ============================================================================
# SOURCEFILE: test_cli_plan_rendering.py
# RELPATH: bundle_file_tool_v2/tests/unit/test_cli_plan_rendering.py
# PROJECT: Bundle File Tool v2.2
# VERSION: 2.1.114
# LIFECYCLE: Testing
# STATUS: Build 114 - WP3 - BFT_B114_CLI_PLAN_RENDERING_TESTS
# ============================================================================
"""The plan renderer, in-process, through the real argument parser.

`test_cli_plan.py` runs the command as a subprocess because stdout purity is a
property of the process. That is the right test for the contract and the wrong
one for the rendering: a subprocess is invisible to the line tracer, so the
renderer would sit at 19% measured coverage while being thoroughly exercised.

These tests drive the same handler in-process, so the branches inside it are
both executed and *seen*. Parsing goes through `build_parser()` rather than a
hand-built namespace, which means a flag renamed in one place and not the other
fails here rather than in the field.
"""

from __future__ import annotations

import json

import pytest

from cli import build_parser
from cli_plan import _human_bytes, _limited, handle_plan
from core.exceptions import BundleFileToolError


@pytest.fixture
def project(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_bytes(b"print(1)\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guide.md").write_bytes(b"# guide\n")
    (tmp_path / "notes.log").write_bytes(b"noise\n")

    env = tmp_path / ".venv"
    (env / "Scripts").mkdir(parents=True)
    (env / "pyvenv.cfg").write_bytes(b"home = C:\\Py\n")
    (env / "Scripts" / "python.exe").write_bytes(b"MZ")
    (env / "junk.py").write_bytes(b"pass\n")

    tools = tmp_path / "tools" / "bin"
    tools.mkdir(parents=True)
    (tools / "activate").write_bytes(b"# shim\n")
    return tmp_path


def plan(*argv):
    """Parse a real command line, so the parser and handler stay in step."""
    return build_parser().parse_args(["plan", *[str(a) for a in argv]])


def run(capsys, *argv):
    handle_plan(plan(*argv))
    return capsys.readouterr()


# ---------------------------------------------------------------------------
# The default view
# ---------------------------------------------------------------------------

def test_the_summary_leads_with_the_decision_not_the_file_list(capsys, project):
    """Build 110 measured formatting a 4,000-entry listing at ~1.1 s. An
    operator judging whether the selection is right should not wait on a list
    they may not need, so the counts come first."""
    out = run(capsys, project).out
    lines = [line for line in out.splitlines() if line.strip()]
    counts_at = next(i for i, line in enumerate(lines) if "included" in line)
    files_at = next(i for i, line in enumerate(lines) if "Files to bundle" in line)
    assert counts_at < files_at


def test_the_summary_names_the_base_action_and_digest(capsys, project):
    out = run(capsys, project).out
    assert "base action" in out
    assert "rule digest" in out


def test_pruned_directories_are_shown_with_family_and_evidence_code(capsys, project):
    out = run(capsys, project).out
    assert "Pruned before descent" in out
    assert "python-venv" in out


def test_ambiguous_directories_are_reported_as_kept(capsys, project):
    """The lone `bin/activate` case: reported, not silently pruned."""
    out = run(capsys, project).out
    assert "Ambiguous, traversed and kept" in out
    assert "tools" in out


def test_a_confirmable_override_is_called_out(capsys, project):
    (project / "vendor.whl").write_bytes(b"PK\x03\x04")
    out = run(capsys, project, "--preset", "archives",
              "--force-include", "**/*.whl").out
    assert "normally be confirmed" in out
    assert "vendor.whl" in out


def test_blocked_paths_are_counted_separately(capsys, project):
    (project / "old_src_bundle.txt").write_bytes(b"nested\n")
    out = run(capsys, project, "--force-include", "**/*").out
    assert "not overridable" in out


def test_the_limit_reports_how_many_were_hidden(capsys, project):
    out = run(capsys, project, "--limit", "1").out
    assert "more (--limit 0 to show all)" in out


def test_notices_and_warnings_go_to_stderr(capsys, project):
    captured = run(capsys, project, "--exclude", "docs/**")
    assert "--no-default-rules" in captured.err
    assert "note:" not in captured.out


# ---------------------------------------------------------------------------
# Alternative surfaces
# ---------------------------------------------------------------------------

def test_list_emits_paths_and_nothing_else(capsys, project):
    out = run(capsys, project, "--list").out
    assert all((project / line).exists() for line in out.split())
    assert "Plan for" not in out


def test_json_output_parses(capsys, project):
    payload = json.loads(run(capsys, project, "--format", "json").out)
    assert payload["file_count"] >= 1
    assert payload["counts"]


def test_explain_one_path_as_text(capsys, project):
    out = run(capsys, project, "--explain", "notes.log").out
    assert "notes.log" in out


def test_explain_one_path_as_json(capsys, project):
    payload = json.loads(
        run(capsys, project, "--explain", "src/app.py", "--format", "json").out)
    assert payload["path"] == "src/app.py"


def test_explain_everything_covers_each_decision(capsys, project):
    out = run(capsys, project, "--explain").out
    assert "src/app.py" in out and "notes.log" in out


def test_a_report_is_written_and_announced_on_stderr(capsys, project, tmp_path):
    report = tmp_path / "nested" / "report.json"
    captured = run(capsys, project, "--report", report)
    assert report.exists(), "the report directory must be created"
    assert "Selection report written" in captured.err
    assert "Selection report written" not in captured.out
    assert json.loads(report.read_text(encoding="utf-8"))["decisions"]


def test_presets_are_listed_as_text(capsys):
    out = run(capsys, "--list-presets").out
    assert "python-env" in out and "exclusions" in out
    assert "source-only" in out and "allow-list" in out


def test_presets_are_listed_as_json(capsys):
    payload = json.loads(run(capsys, "--list-presets", "--format", "json").out)
    assert "python-env" in payload


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

def test_no_sources_raises_with_the_expected_wording(capsys):
    with pytest.raises(BundleFileToolError) as error:
        handle_plan(plan())
    assert "empty" in str(error.value)


def test_a_missing_source_names_the_path(capsys, tmp_path):
    with pytest.raises(BundleFileToolError) as error:
        handle_plan(plan(tmp_path / "absent"))
    assert "absent" in str(error.value)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("count,expected", [
    (0, "0 B"), (512, "512 B"), (2048, "2.0 KB"),
    (5 * 1024 * 1024, "5.0 MB"), (3 * 1024 ** 3, "3.0 GB"),
])
def test_byte_counts_read_naturally(count, expected):
    assert _human_bytes(count) == expected


def test_a_petabyte_still_renders_rather_than_looping():
    assert _human_bytes(1024 ** 5).endswith("GB")


@pytest.mark.parametrize("limit,expected", [(0, 3), (2, 2), (-1, 3), (99, 3)])
def test_limits_clamp_rather_than_surprise(limit, expected):
    assert len(_limited(["a", "b", "c"], limit)) == expected
