"""Build 111 acceptance gates — PyThermX reporting for the Open Bundle path.

Before Build 111, `BundleParser.parse_file()` took no progress sink and
`parser.py` contained no progress plumbing at all. Opening a large bundle
blocked the Tk main thread with a single log line and no observable state; a
~78 MB bundle projects to roughly three seconds of frozen UI.

Pinned here:

  read phase   determinate byte progress from stat(), reported during a
               chunked read rather than one blocking read_text().
  parse phase  determinate line progress, since splitlines() gives the total
               before either profile's loop begins.
  purity       a sink must not change what is parsed.
  throttling   a million-line bundle must not produce a million events - the
               Build 110 lesson applied in the opposite direction.
"""

import time
from pathlib import Path

import pytest

from core.models import BundleEntry, BundleManifest
from core.parser import BundleParser, ProfileRegistry
from core.profiles.plain_marker import PlainMarkerProfile
from core.progress import (
    MODE_DETERMINATE, OP_EXTRACT, PHASE_PARSE, PHASE_READ,
    OperationProgress, ThrottledReporter,
)
from core.writer import BundleCreator


def _bundle_text(tmp_path: Path, file_count: int, lines_each: int = 40) -> str:
    """A real bundle, produced by the real writer, so the grammar is genuine."""
    src = tmp_path / "src"
    src.mkdir(parents=True, exist_ok=True)
    for i in range(file_count):
        body = "\n".join(f"# line {j} of module {i}" for j in range(lines_each))
        (src / f"mod_{i}.py").write_bytes((body + "\n").encode("utf-8"))
    creator = BundleCreator(allow_globs=["**/*"], deny_globs=[], max_file_mb=10)
    files = creator.discover_files(src)
    manifest = creator.create_manifest(files, src, "plain_marker")
    return ProfileRegistry().get("plain_marker").format_manifest(manifest)


@pytest.fixture()
def bundle_file(tmp_path: Path) -> Path:
    text = _bundle_text(tmp_path, file_count=60)
    p = tmp_path / "probe.txt"
    p.write_bytes(text.encode("utf-8"))
    return p


# ---------------------------------------------------------------------------
# Purity — a sink must not change the result
# ---------------------------------------------------------------------------

def test_parse_file_with_sink_matches_parse_file_without(bundle_file):
    """Observing an operation must not alter it.

    parse_file() takes a different read path when a sink is supplied - chunked
    rather than read_text() - so equivalence is a real claim, not a tautology.
    """
    parser = BundleParser()
    baseline = parser.parse_file(bundle_file)
    observed = parser.parse_file(bundle_file, progress=lambda e: None)

    assert [e.path for e in observed.entries] == [e.path for e in baseline.entries]
    assert [e.content for e in observed.entries] == [e.content for e in baseline.entries]
    assert observed.profile == baseline.profile


def test_chunked_read_reproduces_direct_byte_decode_exactly(bundle_file):
    """The chunked reader must preserve the same decoded transport bytes."""
    parser = BundleParser()
    direct = bundle_file.read_bytes().decode("utf-8")
    chunked = parser._read_text_reporting(bundle_file, lambda e: None)
    assert chunked == direct


# ---------------------------------------------------------------------------
# Read phase
# ---------------------------------------------------------------------------

def test_read_phase_reports_determinate_byte_progress(bundle_file):
    events = []
    BundleParser().parse_file(bundle_file, progress=events.append)

    read = [e for e in events if e.phase == PHASE_READ]
    assert read, "no read-phase events emitted"
    assert all(e.operation == OP_EXTRACT for e in read)
    assert all(e.unit == "bytes" for e in read)
    assert all(e.mode == MODE_DETERMINATE for e in read), "read total is known from stat()"

    size = bundle_file.stat().st_size
    assert all(e.total == size for e in read)
    assert read[-1].current == size, "read must close at the full size"
    assert [e.current for e in read] == sorted(e.current for e in read)


# ---------------------------------------------------------------------------
# Parse phase
# ---------------------------------------------------------------------------

def test_parse_phase_reports_determinate_line_progress(bundle_file):
    """Line count is known before the loop, so the bar shows a real percentage."""
    events = []
    manifest = BundleParser().parse_file(bundle_file, progress=events.append)

    parse = [e for e in events if e.phase == PHASE_PARSE]
    assert parse, "no parse-phase events emitted"
    assert all(e.unit == "lines" for e in parse)
    assert all(e.mode == MODE_DETERMINATE for e in parse)

    expected_lines = len(
        bundle_file.read_bytes().decode("utf-8").splitlines(keepends=True))
    assert parse[-1].total == expected_lines
    assert parse[-1].current == expected_lines, "parse must close at the last line"
    assert [e.current for e in parse] == sorted(e.current for e in parse)
    assert str(len(manifest.entries)) in parse[-1].message


def test_parse_progress_carries_the_recovered_file_count(bundle_file):
    """Lines are what the bar can measure; files are what the reader wants."""
    events = []
    BundleParser().parse_file(bundle_file, progress=events.append)
    parse = [e for e in events if e.phase == PHASE_PARSE and e.message]
    assert any("files recovered" in e.message for e in parse) or \
           any("Parsed" in e.message for e in parse), \
           f"no dual-counter message; saw {[e.message for e in parse][:3]}"


def test_markdown_fence_profile_also_reports(tmp_path):
    """Both shipped profiles honour the contract, not just the default one."""
    from core.profiles.markdown_fence import MarkdownFenceProfile

    entry = BundleEntry(path="a.py", content="x = 1\n")
    profile = MarkdownFenceProfile()
    text = profile.format_manifest(BundleManifest(entries=[entry], profile="markdown_fence"))

    events = []
    manifest = profile.parse_stream(text, progress=events.append)
    assert len(manifest.entries) == 1
    assert [e.phase for e in events] == [PHASE_PARSE] * len(events)
    assert events, "markdown_fence emitted nothing"


# ---------------------------------------------------------------------------
# Throttling — the Build 110 lesson, inverted
# ---------------------------------------------------------------------------

def test_parse_does_not_emit_per_line(tmp_path):
    """A large bundle must not produce one event per line.

    emit() delivers synchronously, so per-line reporting on a bundle of any
    size saturates the consumer. Build 110 fixed starvation; this pins the
    opposite failure.
    """
    text = _bundle_text(tmp_path, file_count=120, lines_each=60)
    p = tmp_path / "big.txt"
    p.write_bytes(text.encode("utf-8"))

    line_count = len(text.splitlines(keepends=True))
    assert line_count > 5000, "fixture too small to prove throttling"

    events = []
    BundleParser().parse_file(p, progress=events.append)
    parse = [e for e in events if e.phase == PHASE_PARSE]

    assert len(parse) < line_count / 10, (
        f"{len(parse)} events for {line_count} lines - throttling is not applied")


def test_throttled_reporter_first_tick_always_reports():
    """A loop finishing inside one interval must still be observed.

    Priming the clock by subtracting the interval from monotonic() loses this
    to float rounding - t - (t - 0.10) evaluates below 0.10 - which is how the
    Build 110 discovery reporter first shipped silent.
    """
    seen = []
    r = ThrottledReporter(seen.append, OP_EXTRACT, PHASE_PARSE, "lines", total=10)
    r.tick(1, message="first")
    assert len(seen) == 1, "first tick must always report"

    r.tick(2, message="immediately after")
    assert len(seen) == 1, "second tick inside the interval must be suppressed"

    r.close(10, message="done")
    assert len(seen) == 2
    assert seen[-1].current == 10 and seen[-1].total == 10


def test_throttled_reporter_without_sink_is_inert():
    r = ThrottledReporter(None, OP_EXTRACT, PHASE_PARSE, "lines", total=5)
    r.tick(1)
    r.close(5)
    assert r.emitted == 0


# ---------------------------------------------------------------------------
# Contract tolerance
# ---------------------------------------------------------------------------

def test_profile_without_progress_support_still_parses(bundle_file, monkeypatch):
    """A profile written against the pre-111 contract must keep working.

    Acceptance is decided by signature inspection, never by catching TypeError
    from the call - a genuine TypeError inside parsing would otherwise be
    swallowed and silently retried without a sink.

    Patched on the CLASS: ProfileRegistry.get() constructs a fresh instance per
    call, so an instance-level patch never reaches the object the parser
    actually uses and the test passes without exercising anything.
    """
    original = PlainMarkerProfile.parse_stream

    def legacy_parse_stream(self, text):     # no progress parameter at all
        return original(self, text)

    monkeypatch.setattr(PlainMarkerProfile, "parse_stream", legacy_parse_stream)
    assert BundleParser._accepts_progress(PlainMarkerProfile().parse_stream) is False

    events = []
    manifest = BundleParser().parse_file(bundle_file, progress=events.append)
    assert manifest.entries, "legacy profile failed to parse under a sink"
    # The read phase still reports; only the parse phase goes quiet.
    assert any(e.phase == PHASE_READ for e in events)
    assert not any(e.phase == PHASE_PARSE for e in events)


def test_accepts_progress_detects_the_signature():
    assert BundleParser._accepts_progress(PlainMarkerProfile().parse_stream) is True
    assert BundleParser._accepts_progress(lambda text: None) is False
    assert BundleParser._accepts_progress(lambda text, **kw: None) is True


def test_type_error_inside_parsing_is_not_swallowed(bundle_file, monkeypatch):
    """A real TypeError must surface, not be retried as a missing-sink case.

    Patched on the CLASS for the same reason as the test above.
    """
    from core.exceptions import ProfileParseError

    def exploding(self, text, *, progress=None):
        raise TypeError("genuine defect inside the parser")

    monkeypatch.setattr(PlainMarkerProfile, "parse_stream", exploding)
    with pytest.raises((TypeError, ProfileParseError)) as excinfo:
        BundleParser().parse_file(bundle_file, progress=lambda e: None)
    assert "genuine defect" in str(excinfo.value)
