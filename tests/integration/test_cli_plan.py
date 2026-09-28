# BFT_B114_CLI_PLAN_TESTS
# ============================================================================
# SOURCEFILE: test_cli_plan.py
# RELPATH: bundle_file_tool_v2/tests/integration/test_cli_plan.py
# PROJECT: Bundle File Tool v2.2
# VERSION: 2.1.114
# LIFECYCLE: Testing
# STATUS: Build 114 - WP3 - BFT_B114_CLI_PLAN_TESTS
# ============================================================================
"""The `plan` command, end to end, in a real subprocess.

Run as subprocesses on purpose. Stdout purity is a property of the process, not
of a function: an in-process test capturing `sys.stdout` cannot see a stray
`print` from a library, a warning from the interpreter, or a progress bar that
picked the wrong stream. Build 107 shipped a bar that would have corrupted
piped bundles precisely because it was only ever tested in-process.

Paul's three-way stdout rule (S-10) is the exit gate for this work package:

* `plan` may write to stdout - its output *is* the artifact
* `bundle` without `--output` writes bundle text and nothing else
* `bundle` with `--output` writes nothing to stdout at all
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from core.parser import BundleParser

SRC = Path(__file__).resolve().parents[2] / "src"


def test_bundle_parser_exposes_explicit_large_plan_approval():
    from cli import build_parser

    args = build_parser().parse_args(["bundle", "source", "--allow-large"])
    assert args.allow_large is True


def run_cli(*args, cwd=None):
    """Invoke the CLI as a real process and capture raw bytes."""
    return subprocess.run(
        [sys.executable, "-m", "cli", *[str(a) for a in args]],
        capture_output=True, cwd=str(cwd or SRC))


@pytest.fixture
def project(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_bytes(b"print(1)\n")
    (tmp_path / "src" / "util.py").write_bytes(b"x = 2\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guide.md").write_bytes(b"# guide\n")
    (tmp_path / "notes.log").write_bytes(b"noise\n")

    env = tmp_path / ".venv"
    (env / "Scripts").mkdir(parents=True)
    (env / "pyvenv.cfg").write_bytes(b"home = C:\\Py\n")
    (env / "Scripts" / "python.exe").write_bytes(b"MZ")
    (env / "junk.py").write_bytes(b"pass\n")
    return tmp_path


# ---------------------------------------------------------------------------
# The command works
# ---------------------------------------------------------------------------

def test_plan_summarises_the_selection(project):
    result = run_cli("plan", project)
    assert result.returncode == 0, result.stderr.decode()
    out = result.stdout.decode()
    assert "Plan for" in out
    assert "src/app.py" in out
    assert "included" in out


def test_plan_reports_what_was_pruned_and_why(project):
    out = run_cli("plan", project).stdout.decode()
    assert "Pruned before descent" in out
    assert ".venv" in out
    assert "python-venv" in out


def test_plan_never_lists_a_file_from_a_pruned_directory(project):
    out = run_cli("plan", project).stdout.decode()
    assert ".venv/junk.py" not in out


def test_list_prints_paths_only(project):
    """The script surface. Anything else on stdout breaks a pipeline."""
    result = run_cli("plan", project, "--list")
    lines = [line for line in result.stdout.decode().splitlines() if line]
    assert lines, "nothing was listed"
    assert all(not line.startswith(" ") for line in lines)
    assert "Plan for" not in result.stdout.decode()
    for line in lines:
        assert (project / line).exists(), f"{line} is not a real path"


def test_json_format_is_machine_readable(project):
    result = run_cli("plan", project, "--format", "json")
    payload = json.loads(result.stdout.decode())
    assert payload["file_count"] >= 1
    assert "rule_stack_digest" in payload


def test_explain_shows_the_rule_chain_for_one_path(project):
    result = run_cli("plan", project, "--explain", "notes.log")
    out = result.stdout.decode()
    assert "notes.log" in out and "Excluded" in out


def test_explain_without_a_path_covers_everything(project):
    out = run_cli("plan", project, "--explain").stdout.decode()
    assert "src/app.py" in out and "notes.log" in out


def test_explain_as_json_is_parseable(project):
    result = run_cli("plan", project, "--explain", "src/app.py",
                     "--format", "json")
    payload = json.loads(result.stdout.decode())
    assert payload["path"] == "src/app.py"


def test_a_report_is_written_and_validates_as_json(project, tmp_path):
    report = tmp_path / "report.json"
    result = run_cli("plan", project, "--report", report)
    assert result.returncode == 0
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["decisions"] and payload["rule_stack_digest"]
    assert "detectors" in payload


def test_the_report_path_is_announced_on_stderr_not_stdout(project, tmp_path):
    report = tmp_path / "r.json"
    result = run_cli("plan", project, "--report", report, "--list")
    assert b"Selection report written" in result.stderr
    assert b"Selection report written" not in result.stdout


def test_limit_truncates_and_says_how_many_remain(project):
    out = run_cli("plan", project, "--limit", "1").stdout.decode()
    assert "more (--limit 0 to show all)" in out


def test_list_presets_names_the_shipped_set(project):
    out = run_cli("plan", "--list-presets").stdout.decode()
    assert "python-env" in out and "archives" in out


# ---------------------------------------------------------------------------
# Selection flags through the CLI
# ---------------------------------------------------------------------------

def test_include_narrows_the_plan(project):
    out = run_cli("plan", project, "--include", "src/**", "--list").stdout.decode()
    listed = set(out.split())
    assert listed == {"src/app.py", "src/util.py"}


def test_exclude_is_additive_and_says_so_on_stderr(project):
    result = run_cli("plan", project, "--exclude", "docs/**", "--list")
    listed = set(result.stdout.decode().split())
    assert "docs/guide.md" not in listed
    assert not any(p.startswith(".venv/") for p in listed)
    assert b"--no-default-rules" in result.stderr, (
        "a flag that changed meaning must announce it")


def test_a_preset_applies_from_the_command_line(project):
    listed = run_cli("plan", project, "--preset", "logs",
                     "--list").stdout.decode().split()
    assert "notes.log" not in listed


def test_an_unknown_preset_exits_one_and_names_the_alternatives(project):
    result = run_cli("plan", project, "--preset", "pyhton-env")
    assert result.returncode == 1
    assert b"python-env" in result.stderr


def test_a_rules_file_is_honoured(project, tmp_path):
    rules = tmp_path / "team.json"
    rules.write_text(json.dumps({"version": 1, "deny": ["docs/**"]}),
                     encoding="utf-8")
    listed = run_cli("plan", project, "--rules", rules,
                     "--list").stdout.decode().split()
    assert "docs/guide.md" not in listed


def test_a_broken_rules_file_exits_one_with_a_readable_reason(project, tmp_path):
    rules = tmp_path / "bad.json"
    rules.write_text("{not json", encoding="utf-8")
    result = run_cli("plan", project, "--rules", rules)
    assert result.returncode == 1
    assert b"line" in result.stderr


def test_include_root_reaches_into_a_pruned_directory(project):
    listed = run_cli("plan", project, "--include-root", ".venv",
                     "--no-default-rules", "--list").stdout.decode().split()
    assert ".venv/junk.py" in listed


def test_force_include_overrides_a_preset(project):
    listed = run_cli("plan", project, "--preset", "logs",
                     "--force-include", "**/*.log",
                     "--list").stdout.decode().split()
    assert "notes.log" in listed


def test_groups_control_emission_order(project):
    docs_first = run_cli("plan", project, "--group", "d=docs/**",
                         "--group", "c=src/**", "--list").stdout.decode().split()
    code_first = run_cli("plan", project, "--group", "c=src/**",
                         "--group", "d=docs/**", "--list").stdout.decode().split()
    assert set(docs_first) == set(code_first)
    assert docs_first.index("docs/guide.md") < docs_first.index("src/app.py")
    assert code_first.index("src/app.py") < code_first.index("docs/guide.md")


def test_a_malformed_group_exits_one(project):
    result = run_cli("plan", project, "--group", "nodelimiter")
    assert result.returncode == 1


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

def test_a_missing_source_exits_one(tmp_path):
    result = run_cli("plan", tmp_path / "nope")
    assert result.returncode == 1
    assert b"not found" in result.stderr.lower() or b"ERROR" in result.stderr


def test_no_source_exits_one(project):
    result = run_cli("plan")
    assert result.returncode == 1


def test_explaining_an_unplanned_path_points_at_include_root(project):
    result = run_cli("plan", project, "--explain", ".venv/junk.py")
    assert result.returncode == 1
    assert b"--include-root" in result.stderr


# ---------------------------------------------------------------------------
# Stdout purity - the WP3 exit gate
# ---------------------------------------------------------------------------

def test_bundle_with_output_writes_nothing_at_all_to_stdout(project, tmp_path):
    out = tmp_path / "bundle.txt"
    result = run_cli("bundle", project, "--output", out,
                     "--preset", "logs", "--progress", "bar")
    assert result.returncode == 0, result.stderr.decode()
    assert result.stdout == b"", (
        f"stdout must be empty, saw {result.stdout[:120]!r}")
    assert out.exists() and out.stat().st_size > 0


def test_bundle_without_output_writes_only_the_bundle(project):
    """Notices, warnings and the bar all belong on stderr; a redirected
    bundle must parse."""
    result = run_cli("bundle", project, "--preset", "logs", "--progress", "bar")
    assert result.returncode == 0, result.stderr.decode()
    text = result.stdout.decode("utf-8")
    assert text.strip(), "no bundle was produced"
    assert "note:" not in text
    assert "Selection report" not in text
    assert "Plan for" not in text


def test_a_redirected_planned_bundle_round_trips(project, tmp_path):
    """The end-to-end claim: what plan showed is what the bundle contains."""
    listed = set(run_cli("plan", project, "--preset", "logs",
                         "--list").stdout.decode().split())
    bundled = run_cli("bundle", project, "--preset", "logs").stdout.decode()
    for path in listed:
        assert path in bundled, f"{path} was planned but is not in the bundle"
    assert "notes.log" not in bundled


def test_default_bundle_manifest_equals_the_default_plan(project):
    """P0: no flag may switch ``bundle`` onto a second selection engine."""
    planned = run_cli("plan", project, "--list")
    bundled = run_cli("bundle", project, "--profile", "plain_marker")

    assert planned.returncode == 0, planned.stderr.decode()
    assert bundled.returncode == 0, bundled.stderr.decode()

    expected = planned.stdout.decode().splitlines()
    manifest = BundleParser().parse(
        bundled.stdout.decode("utf-8"), profile_name="plain_marker")
    actual = [entry.path.replace("\\", "/") for entry in manifest.entries]

    assert actual == expected
    assert not any(path.startswith(".venv/") for path in actual)


def test_the_plan_report_from_bundle_goes_to_a_file_not_stdout(project, tmp_path):
    report = tmp_path / "plan.json"
    result = run_cli("bundle", project, "--output", tmp_path / "b.txt",
                     "--plan-report", report)
    assert result.returncode == 0, result.stderr.decode()
    assert result.stdout == b""
    assert json.loads(report.read_text(encoding="utf-8"))["decisions"]


def test_plan_writes_no_bare_carriage_return_to_stdout(project):
    """Build 108's lesson: `text=True` normalises newlines, so a test that
    decodes before asserting cannot see a progress bar's redraws at all."""
    raw = run_cli("plan", project, "--progress", "bar").stdout
    bare_cr = raw.count(b"\r") - raw.count(b"\r\n")
    assert bare_cr == 0, f"{bare_cr} bare CR(s) reached stdout"


def test_a_bundle_with_no_matching_files_exits_one(project):
    result = run_cli("bundle", project, "--include", "nothing/**")
    assert result.returncode == 1
    assert b"No files found" in result.stderr


# ---------------------------------------------------------------------------
# plan and bundle must agree
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("flags", [
    ["--preset", "logs"],
    ["--include", "src/**"],
    ["--exclude", "docs/**"],
    ["--force-include", "**/*.log"],
    ["--preset", "logs", "--force-include", "**/*.log"],
])
def test_plan_and_bundle_select_identically(project, tmp_path, flags):
    """The exit gate: a preview that does not match the artifact is a lie.

    Every selection flag is exercised through both commands and the file sets
    compared, so a flag that is threaded into one path and dropped from the
    other cannot pass - which is exactly how Build 107's `--progress` shipped
    doing nothing on `unbundle`.
    """
    planned = set(run_cli("plan", project, *flags, "--list").stdout.decode().split())
    output = tmp_path / "b.txt"
    result = run_cli("bundle", project, *flags, "--output", output)
    assert result.returncode == 0, result.stderr.decode()

    text = output.read_text(encoding="utf-8")
    for path in planned:
        assert path in text, f"planned {path} missing from the bundle ({flags})"
