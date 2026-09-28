# BFT_B113_SELECTION_CORE_TESTS
# ============================================================================
# SOURCEFILE: test_selection_core.py
# RELPATH: bundle_file_tool_v2/tests/unit/test_selection_core.py
# PROJECT: Bundle File Tool v2.2
# VERSION: 2.1.113
# LIFECYCLE: Testing
# STATUS: Build 113 - WP1 - BFT_B113_SELECTION_CORE_TESTS
# ============================================================================
"""WP1 exit gate: deterministic precedence across every rule layer.

`ARCH-RULING-2026-08-25-01` sets the WP1 gate as "deterministic precedence tests
pass across 100% of rule layers". These are those tests.

The two rulings that shaped this file:

* **Ringo's archives ruling.** Priority 0 holds only hazards that break the tool
  - nested bundle recursion, self-ingestion, traversal. Archives are overridable
  at Priority 5, because `**/*.whl` entered the deny list in Build 107 as hygiene
  and making it permanent would stop this project bundling its own vendored
  wheel.
* **The `--include` allow-list correction.** An allow-list is a base-action
  switch, not an ordinary include rule. Modelled as a rule it would leave every
  non-matching file included and silently broaden output.
"""

from __future__ import annotations

import json

import pytest

from core.selection import (
    CONFIRM_ON_OVERRIDE,
    HARD_SAFETY_PATTERNS,
    LADDER,
    Action,
    ChainEntry,
    Layer,
    SelectionEngine,
    SelectionGroup,
    SelectionPlan,
    SelectionRule,
    State,
    base_action_for,
    matches,
    normalise,
    rule_source_digest,
    rule_stack_digest,
    rules_from_globs,
)


def rule(rule_id, action, pattern, layer, order=0, group=""):
    return SelectionRule(id=rule_id, action=action, pattern=pattern,
                         layer=layer, order=order, group=group)


# ---------------------------------------------------------------------------
# 1. Path normalisation and matching
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("src\\core\\app.py", "src/core/app.py"),
    ("./src/app.py", "src/app.py"),
    ("src/./app.py", "src/app.py"),
    ("src/app.py", "src/app.py"),
])
def test_paths_normalise_to_posix(raw, expected):
    """R6: one canonical internal form, or glob chains break across platforms."""
    assert normalise(raw) == expected


@pytest.mark.parametrize("pattern,path,expected", [
    ("**/*.py", "app.py", True),
    ("**/*.py", "src/app.py", True),
    ("**/*.py", "src/core/deep/app.py", True),
    ("**/*.py", "src/app.txt", False),
    ("src/**", "src/a/b.py", True),
    ("src/**", "docs/a.py", False),
    ("**/__pycache__/**", "src/__pycache__/x.pyc", True),
    ("**/.venv/**", "src/.venv/lib/x.py", True),
    ("**/.venv/**", ".venv312/lib/x.py", False),
])
def test_glob_matching_spans_directories(pattern, path, expected):
    """`**` must cross separators; plain fnmatch does not do this correctly."""
    assert matches(pattern, path) is expected


def test_the_venv312_case_that_started_this(the_case=".venv312/Lib/site-packages/x.py"):
    """The screenshot, as a test. A literal name cannot catch a versioned one."""
    assert matches("**/.venv/**", the_case) is False


# ---------------------------------------------------------------------------
# 2. Precedence across every layer
# ---------------------------------------------------------------------------

def test_the_ladder_is_ordered_2a_before_2b():
    """Project rules must be refinable by the command line, not buried by it."""
    order = list(LADDER)
    assert order.index(Layer.PROJECT_RULES) < order.index(Layer.CLI_RULES)
    assert order.index(Layer.SESSION) < order.index(Layer.PROJECT_RULES)
    assert order[0] is Layer.HARD_SAFETY
    assert order[-1] is Layer.BASE_ACTION


@pytest.mark.parametrize("winning_layer", [
    Layer.SESSION, Layer.PROJECT_RULES, Layer.CLI_RULES,
    Layer.USER_PRESET, Layer.SHIPPED, Layer.GOVERNED_DEFAULT,
])
def test_every_layer_outranks_every_lower_layer(winning_layer):
    """100% layer coverage: each layer beats all layers beneath it."""
    lower = [layer for layer in LADDER
             if layer not in (Layer.HARD_SAFETY, Layer.BASE_ACTION)
             and layer > winning_layer]
    rules = [rule(f"win@{int(winning_layer)}", Action.INCLUDE, "**/*.py", winning_layer)]
    rules += [rule(f"lose@{int(layer)}", Action.EXCLUDE, "**/*.py", layer)
              for layer in lower]

    decision = SelectionEngine(rules=rules, base_action=Action.EXCLUDE).decide("src/app.py")

    assert decision.state is State.INCLUDED
    assert decision.winning_layer is winning_layer


def test_within_one_layer_the_last_matching_rule_wins():
    rules = [
        rule("first", Action.INCLUDE, "**/*.py", Layer.CLI_RULES, order=1),
        rule("second", Action.EXCLUDE, "**/*.py", Layer.CLI_RULES, order=2),
        rule("third", Action.INCLUDE, "**/*.py", Layer.CLI_RULES, order=3),
    ]
    decision = SelectionEngine(rules=rules).decide("a.py")
    assert decision.winning_rule == "third"
    assert decision.state is State.INCLUDED


def test_specificity_never_beats_priority():
    """A broad high-layer rule outranks a precise low-layer one, by design."""
    rules = [
        rule("broad-session", Action.EXCLUDE, "**/*", Layer.SESSION),
        rule("precise-governed", Action.INCLUDE, "src/core/app.py",
             Layer.GOVERNED_DEFAULT),
    ]
    decision = SelectionEngine(rules=rules).decide("src/core/app.py")
    assert decision.state is State.EXCLUDED
    assert decision.winning_layer is Layer.SESSION


def test_base_action_applies_only_when_nothing_matched():
    engine = SelectionEngine(rules=[], base_action=Action.EXCLUDE)
    decision = engine.decide("anything.txt")
    assert decision.state is State.EXCLUDED
    assert decision.winning_layer is Layer.BASE_ACTION
    assert decision.code == "BASE_ACTION_EXCLUDE"


# ---------------------------------------------------------------------------
# 3. Priority 0 - Ringo's ruling on what is truly non-overridable
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path", [
    "proj_bundle_v1.txt",
    "docs/EDSS_src_bundle_v1.txt",
    "self_build103.txt",
])
def test_recursion_hazards_are_blocked_and_cannot_be_overridden(path):
    """A session force-include must not defeat Priority 0."""
    force = rule("session:force", Action.INCLUDE, "**/*", Layer.SESSION)
    decision = SelectionEngine(rules=[force]).decide(path)

    assert decision.state is State.BLOCKED
    assert decision.code == "BLOCKED_NESTED_BUNDLE_RECURSION"
    assert decision.winning_layer is Layer.HARD_SAFETY


@pytest.mark.parametrize("path", [
    "vendor/pythermx-0.5.3-py3-none-any.whl",
    "fixtures/sample.zip",
    "data/backup.tar.gz",
    "archives/old.zip",
])
def test_archives_are_overridable_because_they_are_hygiene_not_hazard(path):
    """Ringo's ruling, and the reason for it.

    `**/*.whl` entered the deny list in Build 107 to stop self-bundles absorbing
    a vendored wheel - hygiene, not a recursion hazard. At Priority 0 this
    project could never bundle its own `vendor/*.whl`. So: overridable.
    """
    rules = [rule("session:force", Action.INCLUDE, path, Layer.SESSION)]
    rules += rules_from_globs([], list(CONFIRM_ON_OVERRIDE))

    decision = SelectionEngine(rules=rules).decide(path, size=1000)

    assert decision.state is State.INCLUDED
    assert decision.confirm_required is True, (
        "overriding an archive default is legitimate but must be deliberate"
    )


def test_an_ordinary_override_needs_no_confirmation():
    rules = [rule("session:force", Action.INCLUDE, "src/**", Layer.SESSION)]
    rules += rules_from_globs([], ["**/__pycache__/**"])
    decision = SelectionEngine(rules=rules).decide("src/app.py")
    assert decision.state is State.INCLUDED
    assert decision.confirm_required is False


def test_hard_safety_patterns_contain_no_archive_rules():
    """Guards the ruling itself against a well-meaning future edit."""
    patterns = {pattern for pattern, _ in HARD_SAFETY_PATTERNS}
    assert not (patterns & set(CONFIRM_ON_OVERRIDE))
    assert all("bundle" in p or "self_build" in p for p in patterns)


def test_governed_deny_rules_do_not_duplicate_hard_safety():
    """A blocked path shows one reason, not the same reason twice."""
    rules = rules_from_globs([], [p for p, _ in HARD_SAFETY_PATTERNS] + ["**/*.zip"])
    assert all("_bundle_" not in r.pattern for r in rules)


# ---------------------------------------------------------------------------
# 4. The --include allow-list correction
# ---------------------------------------------------------------------------

def test_an_allow_list_switches_the_base_action():
    """Otherwise `--include src/**` silently broadens output.

    Modelled as an ordinary include rule over an include-by-default base, every
    non-matching file survives - the exact behaviour spec 11 promises to avoid.
    """
    assert base_action_for(["**/*"]) is Action.INCLUDE
    assert base_action_for([]) is Action.INCLUDE
    assert base_action_for(["src/**"]) is Action.EXCLUDE


def test_include_src_drops_everything_else_as_it_does_today():
    allow = ["src/**"]
    engine = SelectionEngine(
        rules=rules_from_globs(allow, [], layer=Layer.CLI_RULES),
        base_action=base_action_for(allow))

    assert engine.decide("src/app.py").state is State.INCLUDED
    assert engine.decide("docs/readme.md").state is State.EXCLUDED
    assert engine.decide("notes.txt").state is State.EXCLUDED


# ---------------------------------------------------------------------------
# 5. Decision chains - nothing is unexplained
# ---------------------------------------------------------------------------

def test_the_chain_records_every_consulted_rule_not_only_the_winner():
    rules = [
        rule("session", Action.INCLUDE, "**/*.py", Layer.SESSION),
        rule("cli", Action.EXCLUDE, "**/*.py", Layer.CLI_RULES),
        rule("governed", Action.EXCLUDE, "**/*.py", Layer.GOVERNED_DEFAULT),
    ]
    decision = SelectionEngine(rules=rules).decide("app.py")

    assert len(decision.chain) == 3
    assert sum(1 for entry in decision.chain if entry.won) == 1
    winner = next(entry for entry in decision.chain if entry.won)
    assert winner.rule_id == "session"


def test_every_decision_carries_a_reason():
    rules = rules_from_globs(["**/*"], ["**/*.log"])
    engine = SelectionEngine(rules=rules)
    for path in ("a.py", "b.log", "proj_bundle_x.txt"):
        decision = engine.decide(path)
        assert decision.code, f"{path} has no reason code"
        assert decision.explain()[0].startswith(path)


def test_explain_renders_the_chain_highest_priority_first():
    rules = [
        rule("session", Action.INCLUDE, "**/*.py", Layer.SESSION),
        rule("governed", Action.EXCLUDE, "**/*.py", Layer.GOVERNED_DEFAULT),
    ]
    lines = SelectionEngine(rules=rules).decide("app.py").explain()
    assert "[1] session override" in lines[1]
    assert "[5] governed default" in lines[2]
    assert lines[1].lstrip().startswith("->"), "the winner is marked in the chain"


def test_unknown_state_is_reported_rather_than_guessed():
    engine = SelectionEngine(rules=[])
    decision = engine.decide("weird.py", unknown_reason="stat failed: EACCES")
    assert decision.state is State.UNKNOWN
    assert "EACCES" in decision.detail


# ---------------------------------------------------------------------------
# 6. Groups - ordering only, never inclusion
# ---------------------------------------------------------------------------

def test_group_assignment_never_changes_inclusion():
    groups = [SelectionGroup(id="manuscript", order=10, patterns=("chapters/**",))]
    rules = [rule("deny", Action.EXCLUDE, "chapters/**", Layer.GOVERNED_DEFAULT)]
    decision = SelectionEngine(rules=rules, groups=groups).decide("chapters/one.md")
    assert decision.state is State.EXCLUDED


def test_first_matching_group_by_order_becomes_primary():
    groups = [
        SelectionGroup(id="research", order=20, patterns=("**/*.md",)),
        SelectionGroup(id="manuscript", order=10, patterns=("chapters/**",)),
    ]
    engine = SelectionEngine(rules=[], groups=groups)
    assert engine.decide("chapters/one.md").group == "manuscript"
    assert engine.decide("research/notes.md").group == "research"


def test_emission_order_is_group_order_then_path():
    groups = [
        SelectionGroup(id="campaign", order=30, patterns=("marketing/**",)),
        SelectionGroup(id="manuscript", order=10, patterns=("chapters/**",)),
        SelectionGroup(id="research", order=20, patterns=("research/**",)),
    ]
    candidates = [("marketing/a.md", 1), ("research/z.md", 1),
                  ("chapters/02.md", 1), ("chapters/01.md", 1), ("loose.md", 1)]
    plan = SelectionEngine(rules=[], groups=groups).plan(candidates)

    assert plan.ordered_paths() == [
        "chapters/01.md", "chapters/02.md",     # group order 10
        "research/z.md",                        # 20
        "marketing/a.md",                       # 30
        "loose.md",                             # ungrouped last
    ]


def test_a_file_matching_two_groups_is_emitted_once():
    groups = [
        SelectionGroup(id="manuscript", order=10, patterns=("chapters/**",)),
        SelectionGroup(id="markdown", order=20, patterns=("**/*.md",)),
    ]
    plan = SelectionEngine(rules=[], groups=groups).plan([("chapters/one.md", 1)])
    assert plan.ordered_paths() == ["chapters/one.md"]
    assert plan.decisions[0].group == "manuscript"


# ---------------------------------------------------------------------------
# 7. The plan itself
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_plan():
    rules = rules_from_globs(["**/*"], ["**/__pycache__/**", "**/*.zip"])
    engine = SelectionEngine(rules=rules,
                             groups=[SelectionGroup(id="src", order=1,
                                                    patterns=("src/**",))])
    candidates = [("src/app.py", 100), ("src/util.py", 200),
                  ("src/__pycache__/x.pyc", 50), ("dist/pkg.zip", 900),
                  ("proj_bundle_v1.txt", 10), ("README.md", 30)]
    return engine.plan(candidates, pruned_roots=[".venv312"],
                       source_digests=[("governed", "a" * 64)])


def test_counts_cover_every_state(sample_plan):
    counts = sample_plan.counts()
    assert set(counts) == {s.value for s in State}
    assert counts["Included"] == 3          # app, util, README
    assert counts["Excluded"] == 2          # pycache, zip
    assert counts["Blocked"] == 1           # nested bundle


def test_a_plan_is_deterministic(sample_plan):
    rules = rules_from_globs(["**/*"], ["**/__pycache__/**", "**/*.zip"])
    engine = SelectionEngine(rules=rules,
                             groups=[SelectionGroup(id="src", order=1,
                                                    patterns=("src/**",))])
    candidates = [("src/app.py", 100), ("src/util.py", 200),
                  ("src/__pycache__/x.pyc", 50), ("dist/pkg.zip", 900),
                  ("proj_bundle_v1.txt", 10), ("README.md", 30)]
    again = engine.plan(candidates, pruned_roots=[".venv312"],
                        source_digests=[("governed", "a" * 64)])
    assert json.dumps(again.to_dict(), sort_keys=True) == \
        json.dumps(sample_plan.to_dict(), sort_keys=True)


def test_explain_finds_one_path(sample_plan):
    decision = sample_plan.explain("dist/pkg.zip")
    assert decision is not None and decision.state is State.EXCLUDED
    assert sample_plan.explain("nope.txt") is None


def test_pruned_roots_survive_into_the_plan(sample_plan):
    assert sample_plan.pruned_roots == (".venv312",)


def test_the_plan_serialises_deterministically(sample_plan):
    payload = sample_plan.to_dict()
    assert payload["counts"]["Included"] == 3
    assert payload["order"][0].startswith("src/")
    assert all("chain" in row for row in payload["decisions"])
    json.dumps(payload)                      # must be JSON-safe


# ---------------------------------------------------------------------------
# 8. S-09 payload estimation - Paul's exact formula
# ---------------------------------------------------------------------------

def test_binary_estimate_uses_exact_base64_expansion():
    """4*ceil(n/3), not a rounded 1.33x which is short by ~6 bytes per KB."""
    plan = SelectionEngine(rules=[]).plan([("image.png", 1000)])
    assert plan.estimated_payload_bytes(binary_paths=["image.png"]) == 1336
    assert plan.estimated_payload_bytes(binary_paths=["image.png"]) != round(1000 * 1.33)


def test_text_estimate_is_source_size_plus_header_overhead():
    plan = SelectionEngine(rules=[]).plan([("a.py", 500), ("b.py", 500)])
    assert plan.estimated_payload_bytes() == 1000
    assert plan.estimated_payload_bytes(header_bytes=100) == 1200


# ---------------------------------------------------------------------------
# 9. S-08 provenance digests
# ---------------------------------------------------------------------------

def test_digests_are_canonical_and_clock_free():
    first = rule_source_digest({"b": 1, "a": [3, 2, 1]})
    second = rule_source_digest({"a": [3, 2, 1], "b": 1})
    assert first == second, "key order must not change the digest"
    assert len(first) == 64
    assert rule_source_digest({"a": [1, 2, 3]}) != first, "array order must matter"


def test_the_stack_digest_depends_on_source_order():
    one = rule_stack_digest([("governed", "a" * 64), ("preset", "b" * 64)])
    two = rule_stack_digest([("preset", "b" * 64), ("governed", "a" * 64)])
    assert one != two


def test_the_plan_carries_both_per_source_and_stack_digests(sample_plan):
    assert sample_plan.source_digests == (("governed", "a" * 64),)
    assert len(sample_plan.rule_stack_digest) == 64


# ---------------------------------------------------------------------------
# 10. Layering - core stays free of adapters
# ---------------------------------------------------------------------------

def test_selection_core_imports_no_adapter():
    import ast
    from pathlib import Path

    module = Path(__file__).resolve().parents[2] / "src" / "core" / "selection.py"
    tree = ast.parse(module.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])

    for banned in ("tkinter", "pythermx", "cli_progress", "ui", "cli"):
        assert banned not in imported, f"selection.py imports {banned}"
