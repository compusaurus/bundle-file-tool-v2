# BFT_B107_PYTHERMX_INTEGRATION_TESTS
# ============================================================================
# SOURCEFILE: test_pythermx_integration.py
# RELPATH: bundle_file_tool_v2/tests/unit/test_pythermx_integration.py
# PROJECT: Bundle File Tool v2.1
# VERSION: 2.1.107
# LIFECYCLE: Testing
# STATUS: Build 107 - BFT_B107_PYTHERMX_INTEGRATION_TESTS
# ============================================================================
"""PyThermX as Bundle File Tool's CLI progress renderer.

Paul's ratified sequencing, step 5: "BFT CLI integration with therm as its own
governed build." Build 106 produced the event stream; this build draws it.

Four properties are load-bearing and each has a test that fails if it breaks:

1. **stdout stays pure.** `bundle` without --output writes the artifact to
   stdout. A progress bar on that stream would corrupt every piped bundle.
2. **PyThermX is optional.** BFT must run without it installed.
3. **Core stays renderer-free.** The whole point of the Build 106 DTO is that
   one event stream feeds CLI, Tkinter and Web. Core importing a CLI renderer
   would collapse that.
4. **Discovery promotes rather than restarting.** The rising indeterminate
   count becomes a real percentage on the same handle.
"""

from __future__ import annotations

import ast
import io
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

import pytest
from packaging.version import Version

import cli_progress
from cli_progress import PYTHERMX_AVAILABLE, PyThermXReporter, build_reporter
from core.progress import (
    OP_BUNDLE,
    OP_EXTRACT,
    PHASE_COMPLETE,
    PHASE_DISCOVER,
    PHASE_READ,
    PHASE_WRITE,
    OperationProgress,
    ProgressRecorder,
)

pythermx = pytest.importorskip("pythermx")

SRC = Path(__file__).resolve().parents[2] / "src"


class FakeTTY(io.StringIO):
    """A stream that claims to be interactive, so `auto` engages."""

    def isatty(self) -> bool:
        return True


def _unthrottled_style():
    """PyThermX throttles redraws by default; tests need every frame."""
    return pythermx.CLIThermometerStyle(
        non_tty_min_interval_s=0.0,
        min_redraw_interval_s=0.0,
        show_count=True,
    )


def _reporter(stream):
    return PyThermXReporter(stream=stream, style=_unthrottled_style())


# ---------------------------------------------------------------------------
# 1. The discovery handoff - the reason this integration exists
# ---------------------------------------------------------------------------

def test_indeterminate_discovery_promotes_on_the_same_thermometer():
    """The rising count and the final percentage are one continuous widget.

    Discovery cannot know its total until it finishes. PyThermX 0.2.0 added
    `promote()` (R-THM-01) precisely so that learning the total does not mean
    tearing down one widget and starting another.
    """
    stream = FakeTTY()
    reporter = _reporter(stream)

    for count in (0, 1, 2, 3):
        reporter(OperationProgress(operation=OP_BUNDLE, phase=PHASE_DISCOVER,
                                   current=count, total=None, unit="files"))

    model = reporter._model
    assert model.total is None, "still indeterminate before the closing event"
    assert model.percent is None, "an unknown total must not read as 0%"

    reporter(OperationProgress(operation=OP_BUNDLE, phase=PHASE_DISCOVER,
                               current=3, total=3, unit="files"))

    assert reporter._model is model, "promotion must reuse the same handle"
    assert model.total == 3
    assert model.promoted_from == 3, "the indeterminate count is preserved"
    assert model.percent == 100.0


def test_a_new_phase_starts_a_new_thermometer():
    stream = FakeTTY()
    reporter = _reporter(stream)

    reporter(OperationProgress(operation=OP_BUNDLE, phase=PHASE_DISCOVER,
                               current=2, total=2, unit="files"))
    first = reporter._model

    reporter(OperationProgress(operation=OP_BUNDLE, phase=PHASE_READ,
                               current=1, total=2, unit="files"))

    assert reporter._model is not first
    assert reporter._model.phase == PHASE_READ


def test_complete_event_closes_the_bar():
    stream = FakeTTY()
    reporter = _reporter(stream)

    reporter(OperationProgress(operation=OP_EXTRACT, phase=PHASE_WRITE,
                               current=1, total=1, unit="files"))
    reporter(OperationProgress(operation=OP_EXTRACT, phase=PHASE_COMPLETE,
                               current=1, total=1, unit="files",
                               message="Extracted 1 of 1 files"))

    assert reporter._bar is None
    assert reporter._model is None


def test_event_messages_reach_the_real_cli_renderer():
    """The adapter must not silently discard the DTO's human detail."""
    stream = FakeTTY()
    reporter = _reporter(stream)

    reporter(OperationProgress(
        operation=OP_BUNDLE, phase=PHASE_READ,
        current=1, total=2, unit="files", message="Reading src/app.py",
    ))

    assert "Reading src/app.py" in stream.getvalue()


def test_failed_work_has_a_distinct_cli_terminal_outcome():
    stream = FakeTTY()
    reporter = _reporter(stream)
    reporter(OperationProgress(
        operation=OP_BUNDLE, phase=PHASE_READ,
        current=1, total=2, unit="files",
    ))

    reporter.failed("read failed")

    assert "FAIL | read failed" in stream.getvalue()


def test_close_is_idempotent():
    """`close()` runs in a finally block, including paths that never drew."""
    reporter = _reporter(FakeTTY())
    reporter.close()
    reporter.close()
    assert reporter._bar is None


def test_cancellation_scope_completes_the_worker_owned_protocol(monkeypatch):
    """BFT may poll a callable, but the adapter still owes PyThermX its states."""
    from core.cancellation import OperationCancelled

    sources = []
    real_source = cli_progress.CancellationSource

    def capture_source():
        source = real_source()
        sources.append(source)
        return source

    monkeypatch.setattr(cli_progress, "CancellationSource", capture_source)

    with pytest.raises(OperationCancelled):
        with cli_progress.cancellation_scope() as cancel:
            sources[0].request()
            assert cancel() is True
            raise OperationCancelled(
                operation="bundle", phase="read", completed=1, total=2)

    assert sources[0].state is pythermx.CancellationState.CANCELLED


def test_plan_cancellation_is_not_closed_as_success(monkeypatch):
    """The plan path previously skipped the dedicated CANCELLED outcome."""
    from core.cancellation import OperationCancelled
    import cli_plan

    outcomes = []

    class Reporter:
        def cancelled(self, message="Cancelled"):
            outcomes.append(("cancelled", message))

        def failed(self, message=""):
            outcomes.append(("failed", message))

        def close(self):
            outcomes.append(("closed", ""))

    @contextmanager
    def scope():
        yield lambda: False

    class Service:
        def plan_bundle(self, **kwargs):
            raise OperationCancelled(
                operation="bundle", phase="discover", completed=3)

    args = type("Args", (), {
        "source_paths": [Path(".")], "progress": "bar",
        "base_path": None, "preset": None, "rules": None,
        "include": None, "exclude": None, "force_include": None,
        "force_exclude": None, "group": None, "include_root": None,
        "no_default_rules": False, "max_size": None,
    })()
    reporter = Reporter()
    monkeypatch.setattr(cli_plan, "build_reporter", lambda mode: reporter)
    monkeypatch.setattr(cli_plan, "cancellation_scope", scope)

    with pytest.raises(OperationCancelled):
        cli_plan._run_plan(Service(), args)

    assert outcomes == [("cancelled", "Cancelled")]


def test_plan_failure_is_not_closed_as_success(monkeypatch):
    import cli_plan

    outcomes = []

    class Reporter:
        def cancelled(self, message="Cancelled"):
            outcomes.append(("cancelled", message))

        def failed(self, message=""):
            outcomes.append(("failed", message))

        def close(self):
            outcomes.append(("closed", ""))

    @contextmanager
    def scope():
        yield lambda: False

    class Service:
        def plan_bundle(self, **kwargs):
            raise ValueError("bad plan")

    args = type("Args", (), {
        "source_paths": [Path(".")], "progress": "bar",
        "base_path": None, "preset": None, "rules": None,
        "include": None, "exclude": None, "force_include": None,
        "force_exclude": None, "group": None, "include_root": None,
        "no_default_rules": False, "max_size": None,
    })()
    reporter = Reporter()
    monkeypatch.setattr(cli_plan, "build_reporter", lambda mode: reporter)
    monkeypatch.setattr(cli_plan, "cancellation_scope", scope)

    with pytest.raises(ValueError, match="bad plan"):
        cli_plan._run_plan(Service(), args)

    assert outcomes == [("failed", "bad plan")]


# ---------------------------------------------------------------------------
# 2. build_reporter resolution
# ---------------------------------------------------------------------------

def test_none_mode_never_builds_a_reporter():
    assert build_reporter("none", stream=FakeTTY()) is None


def test_auto_declines_when_the_stream_is_not_interactive():
    """This is what keeps redirected output identical to Build 106.

    Under pytest, and under any shell redirect, stderr is not a tty - so `auto`
    resolves to no bar and the plain status lines stand alone.
    """
    assert build_reporter("auto", stream=io.StringIO()) is None


def test_auto_engages_on_an_interactive_stream():
    assert isinstance(build_reporter("auto", stream=FakeTTY()), PyThermXReporter)


def test_bar_mode_overrides_the_tty_check():
    """Forcing the bar is what makes it observable in CI logs and demos."""
    assert isinstance(build_reporter("bar", stream=io.StringIO()), PyThermXReporter)


def test_build_reporter_defaults_to_stderr(monkeypatch):
    """stdout is reserved for the artifact, so the default target is stderr."""
    monkeypatch.setattr(sys, "stderr", FakeTTY())
    reporter = build_reporter("auto")
    assert reporter is not None
    assert reporter._stream is sys.stderr


# ---------------------------------------------------------------------------
# 3. PyThermX is optional
# ---------------------------------------------------------------------------

def test_missing_pythermx_yields_no_reporter_rather_than_an_error(monkeypatch):
    """BFT must run when PyThermX is not installed.

    A returned None is not an error state - every call site already treats a
    missing sink as 'no progress', which is the same path --progress none takes.
    """
    monkeypatch.setattr(cli_progress, "PYTHERMX_AVAILABLE", False)
    assert build_reporter("auto", stream=FakeTTY()) is None
    assert build_reporter("bar", stream=FakeTTY()) is None
    assert cli_progress.pythermx_version() is None


def test_direct_construction_without_pythermx_fails_loudly(monkeypatch):
    """build_reporter() degrades quietly; the class itself does not.

    Quiet degradation is right at the call site, which has a no-progress path.
    It would be wrong here, where the caller has explicitly asked for a
    renderer and silently getting a broken one would be worse than an error.
    """
    monkeypatch.setattr(cli_progress, "PYTHERMX_AVAILABLE", False)
    with pytest.raises(RuntimeError, match="not installed"):
        PyThermXReporter(stream=FakeTTY())


def test_reported_version_matches_the_installed_package():
    assert cli_progress.pythermx_version() == pythermx.__version__


def test_pythermx_is_declared_optional():
    """BFT must be installable and runnable without PyThermX."""
    import tomllib

    pyproject = tomllib.loads((SRC.parent / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["project"]["dependencies"] == [], (
        "PyThermX must stay optional - BFT has to run without it"
    )
    assert "pythermx" in " ".join(
        pyproject["project"]["optional-dependencies"]["progress"])


def test_installed_pythermx_satisfies_the_declared_pin():
    """The installed version must satisfy the specifier we ship.

    Written this way because the obvious version of this test was useless.
    Build 107 asserted a *floor* (`>=0.2.0`) and that the installed version was
    at least 0.2 - both of which 0.3.1 satisfies. Meanwhile the shipped pin said
    `<0.3`, so the environment actually violated the declared dependency and
    nothing failed. A floor check cannot catch an upper-bound breach; only
    evaluating the real specifier can.
    """
    import tomllib

    from packaging.requirements import Requirement
    from packaging.version import Version

    pyproject = tomllib.loads((SRC.parent / "pyproject.toml").read_text(encoding="utf-8"))
    specs = [
        Requirement(spec)
        for spec in pyproject["project"]["optional-dependencies"]["progress"]
        if Requirement(spec).name == "pythermx"
    ]
    assert specs, "no pythermx requirement declared in the progress extra"

    installed = Version(pythermx.__version__)
    for requirement in specs:
        assert requirement.specifier.contains(installed, prereleases=True), (
            f"installed pythermx {installed} violates the declared pin "
            f"{requirement.specifier}"
        )


def test_pythermx_floor_covers_the_features_this_build_uses():
    """0.5.3 is the dependency floor for the next governed BFT baseline.

    Earlier steps remain load-bearing for features that shipped:
    promote() (R-THM-01, 0.2.0) drives the discovery handoff; stderr as the
    default stream (R-THM-02) keeps piped bundles clean; `pythermx.tk` (0.3.0)
    is the Tkinter adapter; 0.3.1 fixed non-finite work values; and 0.4.0 added
    the cooperative cancellation protocol Build 112 is built on. Version 0.5.3
    repairs the initial no-cancel Tk layout used by open and validation.
    """
    assert Version(pythermx.__version__) >= Version("0.5.3"), pythermx.__version__
    assert hasattr(pythermx.ThermometerCore, "promote")

    import importlib
    assert importlib.import_module("pythermx.tk") is not None

    # 0.4.0 cancellation surface, named individually so a partial upgrade fails
    # here rather than at the first cancel a user attempts.
    for name in ("CancellationSource", "CancellationToken", "CancellationState",
                 "CancellationRequested", "TerminalOutcome"):
        assert hasattr(pythermx, name), f"PyThermX is missing {name}"
    assert hasattr(pythermx.CLIThermometer, "finish_cancelled")
    assert hasattr(importlib.import_module("pythermx.tk").TkThermometer,
                   "finish_cancelled")


# ---------------------------------------------------------------------------
# 4. Layering - core must not know a renderer exists
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("module", sorted((SRC / "core").rglob("*.py")),
                         ids=lambda p: p.name)
def test_core_imports_neither_pythermx_nor_the_cli_adapter(module):
    """Core emits events; it never draws them.

    If this fails, the service has grown a dependency on one presentation
    layer and the Tkinter and Web adapters can no longer share it.
    """
    tree = ast.parse(module.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])

    assert "pythermx" not in imported, f"{module.name} imports a CLI renderer"
    assert "cli_progress" not in imported, f"{module.name} imports the CLI adapter"


def test_the_adapter_is_not_inside_the_core_package():
    assert (SRC / "cli_progress.py").is_file()
    assert not (SRC / "core" / "cli_progress.py").exists()


# ---------------------------------------------------------------------------
# 5. The extract path emits progress (Build 107 addition)
# ---------------------------------------------------------------------------

def test_extract_emits_determinate_write_events_and_a_complete_event(tmp_path):
    """Extraction knows its size up front, so nothing here is indeterminate."""
    from core.parser import BundleParser
    from core.writer import BundleCreator, BundleWriter

    source = tmp_path / "src_tree"
    source.mkdir()
    for name in ("a.txt", "b.txt", "c.txt"):
        (source / name).write_text(f"contents of {name}\n", encoding="utf-8")

    creator = BundleCreator(allow_globs=["**/*"], deny_globs=[])
    manifest = creator.create_manifest(
        creator.discover_files(source, source), source, "plain_marker")

    bundle_file = tmp_path / "bundle.txt"
    from core.parser import ProfileRegistry
    bundle_file.write_text(
        ProfileRegistry().get("plain_marker").format_manifest(manifest),
        encoding="utf-8")

    parsed = BundleParser().parse_file(bundle_file, auto_detect=True)

    recorder = ProgressRecorder()
    out = tmp_path / "out"
    writer = BundleWriter(base_path=out, overwrite_policy="overwrite")
    writer.extract_manifest(parsed, out, progress=recorder)

    writes = [e for e in recorder.events if e.phase == PHASE_WRITE]
    assert writes, "extraction reported no progress at all"
    assert all(e.operation == OP_EXTRACT for e in writes)
    assert all(e.total == len(parsed.entries) for e in writes)
    assert all(e.percent is not None for e in writes), "extraction size is known"
    assert [e.current for e in writes] == list(range(1, len(parsed.entries) + 1))

    assert recorder.events[-1].phase == PHASE_COMPLETE


def test_a_failing_sink_cannot_break_an_extraction(tmp_path):
    """Progress is an observation, never a step of the work."""
    from core.models import BundleEntry, BundleManifest
    from core.writer import BundleWriter

    manifest = BundleManifest(
        entries=[BundleEntry(path="only.txt", content="hello\n")],
        profile="plain_marker",
    )

    def hostile_sink(event):
        raise RuntimeError("the renderer exploded")

    out = tmp_path / "out"
    writer = BundleWriter(base_path=out, overwrite_policy="overwrite")
    stats = writer.extract_manifest(manifest, out, progress=hostile_sink)

    assert stats["processed"] == 1
    assert (out / "only.txt").is_file()


# ---------------------------------------------------------------------------
# 6. stdout purity, end to end, with the bar forced on
# ---------------------------------------------------------------------------

def test_forced_bar_writes_nothing_to_stdout(tmp_path):
    """The Build 105 rule, re-verified with a renderer attached.

    Two things about how this is written are deliberate.

    It runs as a **subprocess**, because in-process capture would not prove that
    a real redirected stdout stays clean.

    It captures **bytes**, not text. `text=True` applies universal-newline
    translation, which silently rewrites any carriage return before the
    assertion sees it - so a text-mode check for "\\r" can never fail and proves
    nothing. The real signal is a *bare* CR: PyThermX redraws with one, while
    Windows text-mode output legitimately ends every artifact line with CRLF.
    """
    source = tmp_path / "tree"
    source.mkdir()
    for index in range(5):
        (source / f"f{index}.txt").write_text(f"line {index}\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "cli", "bundle", str(source),
         "--base-path", str(source), "--profile", "plain_marker",
         "--progress", "bar"],
        cwd=str(SRC), capture_output=True,
        env={**__import__("os").environ, "PYTHONPATH": str(SRC)},
    )

    stdout, stderr = result.stdout, result.stderr
    assert result.returncode == 0, stderr.decode("utf-8", "replace")

    bare_cr = stdout.count(b"\r") - stdout.count(b"\r\n")
    assert bare_cr == 0, f"{bare_cr} redraw carriage return(s) reached stdout"

    # nothing that only a progress bar would emit
    assert b"####" not in stdout
    assert b"%" not in stdout

    assert stdout.lstrip().startswith(b"#"), stdout[:200]
    for index in range(5):
        assert f"FILE: f{index}.txt".encode() in stdout

    # and the bar really did draw - on stderr, where it belongs
    text_err = stderr.decode("utf-8", "replace")
    assert "discover" in text_err
    assert "%" in text_err
    # A real TTY may redraw in place with a bare carriage return. Captured
    # subprocess streams are not terminals, and PyThermX may deliberately use
    # line-oriented records there (notably on macOS). Both presentations obey
    # BFT's contract when the phase and percentage remain meaningful.
    stderr_bare_cr = stderr.count(b"\r") - stderr.count(b"\r\n")
    line_oriented_progress = any(
        b"%" in line and b"discover" in line.lower()
        for line in stderr.splitlines())
    assert stderr_bare_cr > 0 or line_oriented_progress, (
        "stderr carried neither an in-place redraw nor a line-oriented "
        "discovery progress record")


def test_progress_none_suppresses_the_bar_entirely(tmp_path):
    source = tmp_path / "tree"
    source.mkdir()
    (source / "one.txt").write_text("x\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "cli", "bundle", str(source),
         "--base-path", str(source), "--profile", "plain_marker",
         "--progress", "none"],
        cwd=str(SRC), capture_output=True, text=True,
        env={**__import__("os").environ, "PYTHONPATH": str(SRC)},
    )

    assert result.returncode == 0, result.stderr
    assert "%" not in result.stderr
    # the plain Build 105 status lines take over
    assert "Discovering files..." in result.stderr
    assert "Found 1 files" in result.stderr


def test_cli_unbundle_renders_progress(tmp_path):
    """`unbundle --progress bar` must actually draw a bar.

    This test exists because Build 107 shipped without it and the defect went
    out: the flag was parsed and the writer emitted events, but the CLI never
    handed the sink to `extract_manifest`, so nothing was drawn.

    Nothing failed, for a reason worth remembering. `emit()` swallows sink
    failures by design - correct for a diagnostic that must never break the
    operation it observes - which also means "no sink" and "working sink" look
    identical from the inside. Only rendered output tells them apart, and the
    Build 107 tests called `extract_manifest(progress=...)` directly, never
    through the command.
    """
    source = tmp_path / "tree"
    source.mkdir()
    for index in range(4):
        (source / f"f{index}.txt").write_text(f"line {index}\n", encoding="utf-8")

    bundle = tmp_path / "b.txt"
    env = {**__import__("os").environ, "PYTHONPATH": str(SRC)}

    made = subprocess.run(
        [sys.executable, "-m", "cli", "bundle", str(source),
         "--base-path", str(source), "--profile", "plain_marker",
         "-o", str(bundle), "--progress", "none"],
        cwd=str(SRC), capture_output=True, text=True, env=env)
    assert made.returncode == 0, made.stderr

    out = tmp_path / "out"
    result = subprocess.run(
        [sys.executable, "-m", "cli", "unbundle", str(bundle),
         "-o", str(out), "--overwrite", "overwrite", "--progress", "bar"],
        cwd=str(SRC), capture_output=True, text=True, env=env)

    assert result.returncode == 0, result.stderr
    assert "write" in result.stderr, (
        "the extract phase drew no thermometer; the sink is not reaching "
        f"extract_manifest. stderr was: {result.stderr!r}"
    )
    assert "%" in result.stderr
    assert (out / "f0.txt").is_file()


def test_cli_unbundle_progress_none_stays_silent(tmp_path):
    """The off switch must still be honoured on the extract path."""
    source = tmp_path / "tree"
    source.mkdir()
    (source / "only.txt").write_text("x\n", encoding="utf-8")

    bundle = tmp_path / "b.txt"
    env = {**__import__("os").environ, "PYTHONPATH": str(SRC)}
    subprocess.run(
        [sys.executable, "-m", "cli", "bundle", str(source),
         "--base-path", str(source), "--profile", "plain_marker",
         "-o", str(bundle), "--progress", "none"],
        cwd=str(SRC), capture_output=True, text=True, env=env, check=True)

    result = subprocess.run(
        [sys.executable, "-m", "cli", "unbundle", str(bundle),
         "-o", str(tmp_path / "out"), "--overwrite", "overwrite",
         "--progress", "none"],
        cwd=str(SRC), capture_output=True, text=True, env=env)

    assert result.returncode == 0, result.stderr
    assert "%" not in result.stderr


def test_progress_flag_defaults_to_auto():
    from cli import build_parser

    parser = build_parser()
    args = parser.parse_args(["bundle", "somewhere"])
    assert args.progress == "auto"

    args = parser.parse_args(["unbundle", "some_bundle.txt"])
    assert args.progress == "auto"
