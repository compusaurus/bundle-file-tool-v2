# BFT_B115_RULE_EDITOR_TESTS
# ============================================================================
# SOURCEFILE: test_rule_editor.py
# RELPATH: bundle_file_tool_v2/tests/unit/test_rule_editor.py
# PROJECT: Bundle File Tool v2.2
# VERSION: 2.1.115
# LIFECYCLE: Testing
# STATUS: Build 115 - WP4 - BFT_B115_RULE_EDITOR_TESTS
# ============================================================================
"""The §7.3 preview arithmetic and the §7.4 review surface, headless.

Both pieces were deliberately kept out of the dialog classes so they could be
tested without a display. The preview is the part most worth pinning: "matches
N / changes M" are different numbers, and conflating them would let a rule that
does nothing look decisive.
"""

from __future__ import annotations

import json

import pytest

from core.selection import State
from core.service import BundleToolService
from ui.rule_editor import RuleEditorPreview, render_review
from ui.workspace_model import WorkspaceModel


@pytest.fixture
def project(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_bytes(b"print(1)\n")
    (tmp_path / "src" / "util.py").write_bytes(b"x = 2\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guide.md").write_bytes(b"# guide\n")
    (tmp_path / "notes.log").write_bytes(b"noise\n")
    (tmp_path / "old_src_bundle.txt").write_bytes(b"nested\n")
    env = tmp_path / ".venv"
    (env / "Scripts").mkdir(parents=True)
    (env / "pyvenv.cfg").write_bytes(b"home = C\n")
    (env / "Scripts" / "python.exe").write_bytes(b"MZ")
    (env / "junk.py").write_bytes(b"pass\n")
    return tmp_path


@pytest.fixture
def model(project):
    service = BundleToolService()
    return WorkspaceModel(service, service.plan_bundle([project]))


@pytest.fixture
def previewer(model):
    return RuleEditorPreview(model)


# ---------------------------------------------------------------------------
# Preview arithmetic (§7.3)
# ---------------------------------------------------------------------------

def test_matches_and_changes_are_different_numbers(previewer):
    """The distinction the readout exists to make.

    `src/**` matches two already-included files, so excluding them changes two
    decisions - but *including* them changes none, because they are already in.
    A readout showing only "matches 2" would make both look identical.
    """
    excluding = previewer.preview("src/**", include=False)
    including = previewer.preview("src/**", include=True)
    assert excluding.matched == including.matched == 2
    assert excluding.changed == 2
    assert including.changed == 0


def test_a_rule_that_changes_nothing_says_so(previewer):
    preview = previewer.preview("src/**", include=True)
    assert "changes 0 decisions" in preview.describe()


def test_the_readout_is_singular_for_one_path(previewer):
    preview = previewer.preview("src/app.py", include=False)
    assert preview.describe() == "matches 1 path / changes 1 decision"


def test_a_pattern_matching_nothing_reports_zero(previewer):
    preview = previewer.preview("nowhere/**", include=False)
    assert preview.matched == 0 and preview.changed == 0


def test_an_empty_pattern_is_invalid_and_explains_what_to_type(previewer):
    preview = previewer.preview("   ", include=False)
    assert preview.valid is False
    assert "docs/**" in preview.describe()


def test_a_blocked_path_is_matched_but_never_counted_as_changed(previewer):
    """Priority 0 cannot be moved, so a rule over it changes nothing.

    Counting it as a change would promise the operator an effect the ladder
    will refuse to deliver.
    """
    preview = previewer.preview("**/*_src_bundle*.txt", include=True)
    assert preview.matched >= 1
    assert preview.changed == 0


def test_the_preview_reflects_overrides_already_applied(model, previewer):
    before = previewer.preview("docs/**", include=False).changed
    model.set_folder("docs", include=False)
    after = RuleEditorPreview(model).preview("docs/**", include=False).changed
    assert before == 1 and after == 0


def test_previewing_reads_no_file(previewer, project):
    import builtins

    real_open = builtins.open
    opened = []
    builtins.open = lambda f, *a, **k: (opened.append(str(f)),
                                        real_open(f, *a, **k))[1]
    try:
        previewer.preview("**/*.py", include=False)
    finally:
        builtins.open = real_open
    assert [p for p in opened if str(project) in p] == []


# ---------------------------------------------------------------------------
# The review surface (§7.4)
# ---------------------------------------------------------------------------

def test_the_review_reports_counts_by_state(model):
    report = render_review(model)
    assert "COUNTS BY STATE" in report
    for state in (State.INCLUDED.value, State.EXCLUDED.value):
        assert state in report


def test_the_review_names_pruned_directories_with_their_evidence(model):
    report = render_review(model)
    assert "PRUNED DIRECTORIES" in report
    assert ".venv" in report
    assert "python-venv" in report
    assert "evidence:" in report


def test_the_review_never_claims_a_descendant_count_it_did_not_take(model):
    """§7.4 in one assertion."""
    report = render_review(model)
    assert "descendants: not enumerated (never walked)" in report


def test_the_review_lists_blocked_paths(model):
    assert "old_src_bundle.txt" in render_review(model)


def test_the_review_lists_manual_overrides(model):
    model.set_folder("docs", include=False)
    report = render_review(model)
    assert "MANUAL OVERRIDES (1)" in report
    assert "docs/**" in report


def test_the_review_says_none_rather_than_leaving_a_section_blank(model):
    report = render_review(model)
    assert "MANUAL OVERRIDES (0)" in report
    assert report.count("  none") >= 2


def test_the_review_records_the_emission_order(model):
    report = render_review(model)
    index = report.index("EMISSION ORDER")
    listed = [line.strip() for line in report[index:].splitlines()[1:] if line.strip()]
    assert listed == model.result.plan.ordered_paths()


def test_the_review_reconciles_with_the_json_report(model):
    """SEL-F-006: the text and JSON reports must agree with each other."""
    text = render_review(model)
    payload = model.result.to_dict()
    for state, count in payload["counts"].items():
        assert f"{state:10} {count}" in text
    assert payload["rule_stack_digest"][:16] in text


def test_the_review_is_deterministic(model):
    assert render_review(model) == render_review(model)


def test_the_review_carries_the_generation(model):
    assert "Generation     1" in render_review(model)
    model.set_folder("docs", include=False)
    assert "Generation     2" in render_review(model)


def test_the_json_export_is_valid_json(model):
    assert json.loads(json.dumps(model.result.to_dict()))["decisions"]


# ---------------------------------------------------------------------------
# Layering
# ---------------------------------------------------------------------------

def test_the_preview_and_review_need_no_toolkit():
    """Both are imported above without a display; this states the intent."""
    import inspect

    import ui.rule_editor as module

    source = inspect.getsource(module.RuleEditorPreview)
    assert "tk." not in source and "ttk." not in source
