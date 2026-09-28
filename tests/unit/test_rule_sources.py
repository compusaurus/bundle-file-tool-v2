# BFT_B114_RULE_SOURCES_TESTS
# ============================================================================
# SOURCEFILE: test_rule_sources.py
# RELPATH: bundle_file_tool_v2/tests/unit/test_rule_sources.py
# PROJECT: Bundle File Tool v2.2
# VERSION: 2.1.114
# LIFECYCLE: Testing
# STATUS: Build 114 - WP3 - BFT_B114_RULE_SOURCES_TESTS
# ============================================================================
"""Where rules come from, and which layer they land on.

The precedence contract is only as good as the mapping from what an operator
typed to the layer it occupies. These tests pin that mapping, and they pin the
one thing that is *not* configurable: a rule source cannot choose its own layer.
"""

from __future__ import annotations

import json

import pytest

from core.rule_sources import (
    SHIPPED_PRESETS,
    expand_bare_pattern,
    RuleSourceError,
    RuleStack,
    available_presets,
    cli_rules,
    load_rules_file,
    parse_group_specs,
    preset_rules,
    resolve_base_action,
    session_rules,
)
from core.selection import Action, Layer


# ---------------------------------------------------------------------------
# Presets
# ---------------------------------------------------------------------------

def test_every_shipped_preset_lands_on_layer_four():
    """A preset is a shipped default. It may never mint a higher-priority rule."""
    for name in SHIPPED_PRESETS:
        stack = preset_rules([name])
        assert stack.rules, f"preset {name} produced no rules"
        for rule in stack.rules:
            assert rule.layer is Layer.SHIPPED, (
                f"preset {name} produced a rule at {rule.layer.display}")


def test_an_unknown_preset_is_an_error_that_names_the_alternatives():
    """Silently applying nothing would leave the operator believing it worked."""
    with pytest.raises(RuleSourceError) as error:
        preset_rules(["pyhton-env"])
    message = str(error.value)
    assert "pyhton-env" in message
    assert "python-env" in message, "the error must list the real names"


def test_configured_presets_override_shipped_ones_by_name():
    """Ringo's standing direction: configurable to a high degree."""
    stack = preset_rules(["python-env"],
                         {"python-env": {"deny": ["**/only-this/**"]}})
    patterns = [rule.pattern for rule in stack.rules]
    assert patterns == ["**/only-this/**"]


def test_a_configured_preset_adds_a_new_name():
    catalogue = available_presets({"house-style": {"deny": ["**/*.bak"]}})
    assert "house-style" in catalogue
    assert "python-env" in catalogue, "adding must not drop the shipped set"


def test_a_malformed_configured_preset_is_rejected_with_its_name():
    with pytest.raises(RuleSourceError) as error:
        available_presets({"broken": ["not", "an", "object"]})
    assert "broken" in str(error.value)


def test_preset_digests_are_stable_and_differ_between_presets():
    first = preset_rules(["python-env"]).digests
    again = preset_rules(["python-env"]).digests
    other = preset_rules(["node"]).digests
    assert first == again, "the same preset must digest identically"
    assert first != other


def test_an_allow_list_preset_records_its_patterns_at_its_own_layer():
    stack = preset_rules(["source-only"])
    assert stack.allow_by_layer[Layer.SHIPPED]
    assert Layer.CLI_RULES not in stack.allow_by_layer


# ---------------------------------------------------------------------------
# Base action resolution - the Build 114 defect
# ---------------------------------------------------------------------------

def test_the_governed_catch_all_alone_keeps_include_by_default():
    action, _ = resolve_base_action({Layer.GOVERNED_DEFAULT: ["**/*"]})
    assert action is Action.INCLUDE


def test_a_cli_allow_list_outranks_the_governed_catch_all():
    """The defect this build found: the union of allow-lists always contains
    `**/*`, so `--include src/**` would never narrow anything."""
    action, scope = resolve_base_action({
        Layer.GOVERNED_DEFAULT: ["**/*"],
        Layer.CLI_RULES: ["src/**"],
    })
    assert action is Action.EXCLUDE
    assert scope == ["src/**"]


def test_project_rules_outrank_the_command_line_for_scope():
    """2a before 2b, per George's ruling."""
    action, scope = resolve_base_action({
        Layer.PROJECT_RULES: ["lib/**"],
        Layer.CLI_RULES: ["src/**"],
        Layer.GOVERNED_DEFAULT: ["**/*"],
    })
    assert action is Action.EXCLUDE
    assert scope == ["lib/**"]


def test_a_preset_allow_list_outranks_the_governed_default():
    action, _ = resolve_base_action({
        Layer.GOVERNED_DEFAULT: ["**/*"],
        Layer.SHIPPED: ["**/*.py"],
    })
    assert action is Action.EXCLUDE


def test_no_allow_list_anywhere_means_include_by_default():
    action, scope = resolve_base_action({})
    assert action is Action.INCLUDE and scope == []


def test_empty_patterns_do_not_count_as_an_allow_list():
    action, _ = resolve_base_action({Layer.CLI_RULES: ["", ""],
                                     Layer.GOVERNED_DEFAULT: ["**/*"]})
    assert action is Action.INCLUDE


# ---------------------------------------------------------------------------
# Rules files
# ---------------------------------------------------------------------------

def write_rules(tmp_path, payload):
    path = tmp_path / "team.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_a_rules_file_becomes_layer_two_a_rules(tmp_path):
    path = write_rules(tmp_path, {"version": 1, "deny": ["**/*.log"]})
    stack = load_rules_file(path)
    assert [r.layer for r in stack.rules] == [Layer.PROJECT_RULES]
    assert stack.rules[0].action is Action.EXCLUDE


def test_a_rules_file_may_not_mint_a_priority_zero_block(tmp_path):
    """Priority 0 belongs to the tool. A project file that could create
    non-overridable rules would bind the operator running the tool."""
    path = write_rules(tmp_path, {
        "version": 1,
        "rules": [{"action": "block", "pattern": "secret/**"}]})
    with pytest.raises(RuleSourceError) as error:
        load_rules_file(path)
    assert "block" in str(error.value)
    assert "exclude" in str(error.value), "the error must offer the way forward"


def test_a_missing_rules_file_is_an_error_not_a_shrug(tmp_path):
    with pytest.raises(RuleSourceError) as error:
        load_rules_file(tmp_path / "absent.json")
    assert "not found" in str(error.value)


def test_invalid_json_reports_the_line_and_column(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text('{"version": 1,,}', encoding="utf-8")
    with pytest.raises(RuleSourceError) as error:
        load_rules_file(path)
    message = str(error.value)
    assert "line" in message and "column" in message


def test_a_future_schema_version_is_refused(tmp_path):
    path = write_rules(tmp_path, {"version": 99, "deny": []})
    with pytest.raises(RuleSourceError) as error:
        load_rules_file(path)
    assert "99" in str(error.value)


def test_a_non_object_rules_file_is_refused(tmp_path):
    path = tmp_path / "list.json"
    path.write_text('["deny"]', encoding="utf-8")
    with pytest.raises(RuleSourceError):
        load_rules_file(path)


def test_a_rule_without_a_pattern_names_its_index(tmp_path):
    path = write_rules(tmp_path, {"version": 1, "rules": [{"action": "exclude"}]})
    with pytest.raises(RuleSourceError) as error:
        load_rules_file(path)
    assert "rules[0]" in str(error.value)


def test_a_rule_with_an_unknown_action_lists_the_valid_ones(tmp_path):
    path = write_rules(tmp_path, {
        "version": 1, "rules": [{"action": "maybe", "pattern": "x"}]})
    with pytest.raises(RuleSourceError) as error:
        load_rules_file(path)
    assert "maybe" in str(error.value) and "exclude" in str(error.value)


def test_a_non_object_rule_entry_is_refused(tmp_path):
    path = write_rules(tmp_path, {"version": 1, "rules": ["nope"]})
    with pytest.raises(RuleSourceError) as error:
        load_rules_file(path)
    assert "rules[0]" in str(error.value)


def test_allow_must_be_a_list_of_strings(tmp_path):
    path = write_rules(tmp_path, {"version": 1, "allow": [1, 2]})
    with pytest.raises(RuleSourceError) as error:
        load_rules_file(path)
    assert "allow" in str(error.value)


def test_a_single_string_is_accepted_where_a_list_is_expected(tmp_path):
    """Forgiving on shape, strict on meaning."""
    path = write_rules(tmp_path, {"version": 1, "deny": "**/*.log"})
    stack = load_rules_file(path)
    assert [r.pattern for r in stack.rules] == ["**/*.log"]


def test_a_rules_file_include_contributes_to_the_allow_list(tmp_path):
    path = write_rules(tmp_path, {"version": 1,
                                  "rules": [{"action": "include", "pattern": "src/**"}]})
    stack = load_rules_file(path)
    assert stack.allow_by_layer[Layer.PROJECT_RULES] == ["src/**"]


def test_groups_are_loaded_with_their_order(tmp_path):
    path = write_rules(tmp_path, {
        "version": 1,
        "groups": [{"id": "docs", "order": 2, "patterns": ["**/*.md"]},
                   {"id": "code", "order": 1, "patterns": ["**/*.py"]}]})
    stack = load_rules_file(path)
    assert {g.id: g.order for g in stack.groups} == {"docs": 2, "code": 1}


def test_a_group_without_an_id_is_refused(tmp_path):
    path = write_rules(tmp_path, {"version": 1, "groups": [{"patterns": ["*"]}]})
    with pytest.raises(RuleSourceError) as error:
        load_rules_file(path)
    assert "groups[0]" in str(error.value)


def test_a_disabled_rule_is_carried_but_inert(tmp_path):
    path = write_rules(tmp_path, {
        "version": 1,
        "rules": [{"action": "exclude", "pattern": "**/*", "enabled": False}]})
    stack = load_rules_file(path)
    assert stack.rules[0].enabled is False
    assert stack.rules[0].applies_to("anything.py") is False


def test_nested_preset_requests_surface_as_a_notice(tmp_path):
    path = write_rules(tmp_path, {"version": 1, "presets": ["vcs"]})
    stack = load_rules_file(path)
    assert any("vcs" in notice for notice in stack.notices)


# ---------------------------------------------------------------------------
# CLI and session layers
# ---------------------------------------------------------------------------

def test_cli_rules_land_on_layer_two_b():
    stack = cli_rules(include=["src/**"], exclude=["**/*.log"])
    assert {r.layer for r in stack.rules} == {Layer.CLI_RULES}


def test_exclude_announces_that_it_is_now_additive():
    """Paul's ruling changed the meaning of a flag people already use.
    A silent change of meaning is the worst kind."""
    stack = cli_rules(exclude=["**/*.log"])
    joined = " ".join(stack.notices)
    assert "adds to the default rules" in joined
    assert "--no-default-rules" in joined, "the notice must name the escape hatch"


def test_include_announces_that_it_narrows():
    stack = cli_rules(include=["src/**"])
    assert any("excluded" in notice for notice in stack.notices)


def test_no_flags_means_no_notices():
    assert cli_rules().notices == []


def test_session_overrides_land_on_layer_one():
    stack = session_rules(force_include=["**/*.whl"], force_exclude=["secret/**"])
    assert {r.layer for r in stack.rules} == {Layer.SESSION}
    actions = {r.pattern: r.action for r in stack.rules}
    assert actions["**/*.whl"] is Action.INCLUDE
    assert actions["secret/**"] is Action.EXCLUDE


def test_a_session_force_include_is_not_an_allow_list():
    """A force-include rescues one path; it does not redefine the bundle's
    scope. Treating it as an allow-list would drop everything else."""
    stack = session_rules(force_include=["**/*.whl"])
    assert stack.allow_by_layer == {}


# ---------------------------------------------------------------------------
# Groups from the command line
# ---------------------------------------------------------------------------

def test_group_specs_parse_in_declaration_order():
    groups = parse_group_specs(["code=**/*.py,**/*.js", "docs=**/*.md"])
    assert [g.id for g in groups] == ["code", "docs"]
    assert [g.order for g in groups] == [0, 1]
    assert groups[0].patterns == ("**/*.py", "**/*.js")


@pytest.mark.parametrize("spec", ["nodelimiter", "=**/*.py", "name=", "name=,,"])
def test_a_malformed_group_spec_is_refused(spec):
    """A group that parsed to nothing would look like it worked and order
    nothing at all."""
    with pytest.raises(RuleSourceError):
        parse_group_specs([spec])


# ---------------------------------------------------------------------------
# RuleStack mechanics
# ---------------------------------------------------------------------------

def test_merge_allow_preserves_the_originating_layer():
    target = RuleStack()
    source = RuleStack()
    source.add_allow(Layer.SHIPPED, "**/*.py")
    target.merge_allow(source)
    assert target.allow_by_layer == {Layer.SHIPPED: ["**/*.py"]}
    assert target.allow == ["**/*.py"]


# ---------------------------------------------------------------------------
# Bare patterns keep the depth behaviour operators already rely on
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("typed,anchored", [
    ("*.py", "**/*.py"),
    ("notes.log", "**/notes.log"),
    ("*", "**/*"),
])
def test_a_pattern_naming_no_directory_matches_at_any_depth(typed, anchored):
    """Regression guard for a silent narrowing.

    The engine's `*` does not cross a separator, but the command line has
    always matched `*.py` at any depth and so does every tool an operator has
    muscle memory for. Routing --include through the ladder without anchoring
    would have stopped `--include '*.py'` from matching `src/app.py`, with no
    error and no message.
    """
    assert expand_bare_pattern(typed) == anchored


@pytest.mark.parametrize("typed", ["src/**", "docs/*.md", "**/*.py", "**/x"])
def test_a_pattern_that_names_a_position_is_left_alone(typed):
    assert expand_bare_pattern(typed) == typed


def test_cli_rules_anchor_bare_patterns_but_keep_the_typed_id():
    """The rule carries the anchored pattern; its id keeps what was typed, so
    the explanation shows the operator their own words."""
    stack = cli_rules(include=["*.py"], exclude=["*.log"])
    by_id = {rule.id: rule.pattern for rule in stack.rules}
    assert by_id["cli:include:*.py"] == "**/*.py"
    assert by_id["cli:exclude:*.log"] == "**/*.log"


# ---------------------------------------------------------------------------
# Labels must not repeat the layer that already names them
# ---------------------------------------------------------------------------

def test_no_rule_label_repeats_its_own_layer_label():
    """`describe()` prefixes the layer, so a label that repeats it doubles.

    Found on the real project: an explanation read "shipped preset: shipped
    preset: logs (exclude **/*.bak)". The chain is the primary output of this
    work package - if it reads badly, the feature does not do its job.
    """
    stacks = [
        preset_rules(["logs"]),
        cli_rules(include=["*.py"], exclude=["*.log"]),
        session_rules(force_include=["**/*.whl"], force_exclude=["secret/**"]),
    ]
    for stack in stacks:
        for rule in stack.rules:
            described = rule.describe()
            prefix = f"{rule.layer.label}: "
            assert described.startswith(prefix)
            assert rule.layer.label not in described[len(prefix):], (
                f"label repeats its layer: {described}")


def test_a_command_line_rule_shows_what_was_typed():
    """`*.py` is anchored to `**/*.py`; the explanation shows both, so the
    expansion is visible rather than mysterious."""
    stack = cli_rules(include=["*.py"])
    described = stack.rules[0].describe()
    assert "*.py" in described and "**/*.py" in described
