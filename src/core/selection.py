# BFT_B113_SELECTION_CORE - SelectionPlan, precedence ladder, decision chains
# ===================================================================================================
# SOURCEFILE: selection.py
# RELPATH: bundle_file_tool_v2/src/core/selection.py
# PROJECT: Bundle File Tool v2.2
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.113
# LIFECYCLE: Testing
# STATUS: Build 113 - WP1 - BFT_B113_SELECTION_CORE
# DESCRIPTION: Deterministic selection evaluation. No renderer, no Tk, no CLI.
# Relative Path: src/core/selection.py
# Purpose:
# independent_entry_point:
# ===================================================================================================
"""Decide what goes into a bundle, and be able to say why.

WP1 of the v2.2 Selection Workspace, ratified in `ARCH-RULING-2026-08-25-01` and
amended by `ARCH-RULING-ADDENDUM-2026-08-25-01`.

The whole point is that **every decision carries its reason**. A path is never
silently dropped: it has a state, a winning rule, and the full chain of rules
that were consulted on the way. That is what turns "4,084 files and I don't know
why" into something a person can inspect.

The precedence ladder
---------------------
Higher priority wins outright, regardless of specificity or file order. Within
one layer, rules are evaluated in configured order and the **last match wins**.

    0   Hard safety            non-overridable
    1   Session force ops      GUI toggles, --force-include/--force-exclude
    2a  Project rule file      opt-in, --rules / .bft-selection.json
    2b  Ordinary CLI rules     --include / --exclude
    3   User presets           personal, outside governed config
    4   Shipped presets and detectors
    5   Governed defaults      overridable baseline policy
    6   Base action            include-by-default or exclude-by-default

What sits at Priority 0, and what does not
------------------------------------------
This was the sharpest question in review, and Ringo settled it. Priority 0 holds
only hazards that **break the tool**:

* nested bundle text, which is a genuine recursion hazard;
* self-ingestion of the bundle currently being written;
* traversal outside the source base;
* unreadable or invalid paths.

Archives - `.zip`, `.tar*`, `.whl`, `archives/**` - are **not** here. They were
proposed for Priority 0, but that rule entered the deny list in Build 107 as
hygiene, to stop self-bundles absorbing a vendored wheel; it was never a
recursion hazard. Making it permanent would have meant this project could never
bundle its own `vendor/*.whl`. They sit at Priority 5, overridable, and the plan
marks the override as one requiring confirmation.

Group assignment happens strictly **after** the inclusion decision and never
changes it.
"""

from __future__ import annotations

import hashlib
import json
import posixpath
import re
from functools import lru_cache
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from core.cancellation import CancelCheck, raise_if_cancelled
from core.progress import (
    OP_BUNDLE,
    PHASE_PLAN,
    ProgressSink,
    ThrottledReporter,
)

# ---------------------------------------------------------------------------
# Layers
# ---------------------------------------------------------------------------


class Layer(int, Enum):
    """Precedence layers. Lower value wins.

    Values are spaced rather than sequential so that 2a and 2b can be distinct
    while every layer still compares in ladder order. The first draft numbered
    them 20/25 alongside 3-6 for the others, which made PROJECT_RULES compare as
    lower priority than USER_PRESET - wrong for precedence and, less obviously,
    wrong for the confirm-on-override check that asks whether an explicit user
    action won. `display` carries the specification's own labels.
    """

    HARD_SAFETY = 0
    SESSION = 10
    PROJECT_RULES = 20          # 2a
    CLI_RULES = 25              # 2b, evaluated after project rules
    USER_PRESET = 30
    SHIPPED = 40
    GOVERNED_DEFAULT = 50
    BASE_ACTION = 60

    @property
    def label(self) -> str:
        return _LAYER_LABELS[self]

    @property
    def display(self) -> str:
        """The ladder position as the specification writes it."""
        return _LAYER_DISPLAY[self]


_LAYER_DISPLAY = {
    Layer.HARD_SAFETY: "0",
    Layer.SESSION: "1",
    Layer.PROJECT_RULES: "2a",
    Layer.CLI_RULES: "2b",
    Layer.USER_PRESET: "3",
    Layer.SHIPPED: "4",
    Layer.GOVERNED_DEFAULT: "5",
    Layer.BASE_ACTION: "6",
}

_LAYER_LABELS = {
    Layer.HARD_SAFETY: "hard safety",
    Layer.SESSION: "session override",
    Layer.PROJECT_RULES: "project rules",
    Layer.CLI_RULES: "command line",
    Layer.USER_PRESET: "user preset",
    Layer.SHIPPED: "shipped preset",
    Layer.GOVERNED_DEFAULT: "governed default",
    Layer.BASE_ACTION: "base action",
}

#: Ladder order for evaluation and display. Priority 2a precedes 2b so the
#: command line refines project policy rather than being buried beneath it.
LADDER: Tuple[Layer, ...] = (
    Layer.HARD_SAFETY, Layer.SESSION, Layer.PROJECT_RULES, Layer.CLI_RULES,
    Layer.USER_PRESET, Layer.SHIPPED, Layer.GOVERNED_DEFAULT, Layer.BASE_ACTION,
)


class Action(str, Enum):
    INCLUDE = "include"
    EXCLUDE = "exclude"
    BLOCK = "block"             # reserved to Layer 0


class State(str, Enum):
    """Decision states. `STALE` is the sixth, added per Paul's 4.2."""

    INCLUDED = "Included"
    EXCLUDED = "Excluded"
    BLOCKED = "Blocked"
    SKIPPED = "Skipped"
    UNKNOWN = "Unknown"
    STALE = "Stale"


#: Priority 0 - recursion and integrity hazards only. Ringo's ruling.
HARD_SAFETY_PATTERNS: Tuple[Tuple[str, str], ...] = (
    ("**/*_bundle_*.txt", "BLOCKED_NESTED_BUNDLE_RECURSION"),
    ("**/*_src_bundle*.txt", "BLOCKED_NESTED_BUNDLE_RECURSION"),
    ("**/self_build*.txt", "BLOCKED_NESTED_BUNDLE_RECURSION"),
)

#: Priority 5 entries that carry real weight even though they are overridable.
#: Overriding one is legitimate but should be a deliberate act, so the decision
#: records `confirm_required` and an adapter can ask before proceeding.
CONFIRM_ON_OVERRIDE: Tuple[str, ...] = (
    "**/*.zip", "**/*.tar", "**/*.tar.*", "**/*.whl", "**/archives/**",
)


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------


def normalise(path: str) -> str:
    """Canonical internal form: POSIX separators, no leading './'."""
    text = str(path).replace("\\", "/")
    while text.startswith("./"):
        text = text[2:]
    return posixpath.normpath(text) if text else text


@lru_cache(maxsize=8192)
def _compiled(pattern: str) -> "re.Pattern[str]":
    """Compile a path glob to one regex, with `**` crossing separators.

    `fnmatch` is wrong for path globs in both directions: its `*` crosses `/`,
    and it has no `**`. The first implementation worked around that by trying a
    dozen generated patterns per match, which cost twelve regex operations for
    every rule against every path. One compiled regex, cached by pattern, does
    the same job once.

    Semantics:
        `**/x`   x at any depth, including the root
        `a/**`   anything beneath a, and a itself
        `*`      one segment only
        `?`      one character, never a separator
    """
    out: list[str] = []
    index, length = 0, len(pattern)
    while index < length:
        char = pattern[index]
        if pattern.startswith("**/", index):
            out.append("(?:[^/]+/)*")
            index += 3
        elif pattern.startswith("/**", index) and index + 3 == length:
            out.append("(?:/.*)?")
            index += 3
        elif pattern.startswith("**", index):
            out.append(".*")
            index += 2
        elif char == "*":
            out.append("[^/]*")
            index += 1
        elif char == "?":
            out.append("[^/]")
            index += 1
        else:
            out.append(re.escape(char))
            index += 1
    return re.compile("^" + "".join(out) + "$")


def matches(pattern: str, path: str) -> bool:
    """Whether a path glob matches a path. `**` crosses directory separators."""
    return _compiled(normalise(pattern)).match(normalise(path)) is not None


@dataclass(frozen=True)
class SelectionRule:
    """One include/exclude/block condition."""

    id: str
    action: Action
    pattern: str
    layer: Layer
    order: int = 0
    label: str = ""
    group: str = ""
    enabled: bool = True
    code: str = ""
    source: str = ""

    def applies_to(self, path: str) -> bool:
        return self.enabled and matches(self.pattern, path)

    def describe(self) -> str:
        name = self.label or self.id
        return f"{self.layer.label}: {name} ({self.action.value} {self.pattern})"


@dataclass(frozen=True)
class ChainEntry:
    """One consulted rule, kept whether or not it won."""

    layer: Layer
    rule_id: str
    action: Action
    pattern: str
    won: bool

    def to_dict(self) -> Dict[str, object]:
        return {"layer": self.layer.display, "layer_label": self.layer.label,
                "rule": self.rule_id, "action": self.action.value,
                "pattern": self.pattern, "won": self.won}


@dataclass(frozen=True)
class SelectionDecision:
    """The complete explanation for one path."""

    path: str
    state: State
    winning_rule: str = ""
    winning_layer: Optional[Layer] = None
    chain: Tuple[ChainEntry, ...] = ()
    group: str = ""
    code: str = ""
    detail: str = ""
    confirm_required: bool = False
    size: int = 0

    @property
    def included(self) -> bool:
        return self.state is State.INCLUDED

    def explain(self) -> List[str]:
        """Human-readable chain, highest priority first."""
        lines = [f"{self.path}: {self.state.value}"]
        for entry in self.chain:
            mark = "->" if entry.won else "  "
            lines.append(f"  {mark} [{entry.layer.display}] {entry.layer.label}: "
                         f"{entry.rule_id} {entry.action.value} {entry.pattern}")
        if self.detail:
            lines.append(f"     {self.detail}")
        if self.confirm_required:
            lines.append("     override requires confirmation")
        return lines

    def to_dict(self) -> Dict[str, object]:
        return {
            "path": self.path, "state": self.state.value,
            "winning_rule": self.winning_rule,
            "winning_layer": self.winning_layer.display if self.winning_layer is not None else None,
            "group": self.group, "code": self.code, "detail": self.detail,
            "confirm_required": self.confirm_required, "size": self.size,
            "chain": [entry.to_dict() for entry in self.chain],
        }


@dataclass(frozen=True)
class SelectionGroup:
    """User-defined output partition. Never affects inclusion."""

    id: str
    label: str = ""
    order: int = 0
    patterns: Tuple[str, ...] = ()

    def claims(self, path: str) -> bool:
        return any(matches(pattern, path) for pattern in self.patterns)


# ---------------------------------------------------------------------------
# The plan
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SelectionPlan:
    """An immutable evaluation result for one source snapshot and rule stack."""

    decisions: Tuple[SelectionDecision, ...]
    groups: Tuple[SelectionGroup, ...] = ()
    pruned_roots: Tuple[str, ...] = ()
    warnings: Tuple[str, ...] = ()
    rule_stack_digest: str = ""
    source_digests: Tuple[Tuple[str, str], ...] = ()
    generation: int = 1

    # -- queries ---------------------------------------------------------

    def included(self) -> List[SelectionDecision]:
        return [d for d in self.decisions if d.state is State.INCLUDED]

    def by_state(self, state: State) -> List[SelectionDecision]:
        return [d for d in self.decisions if d.state is state]

    def explain(self, path: str) -> Optional[SelectionDecision]:
        target = normalise(path)
        for decision in self.decisions:
            if decision.path == target:
                return decision
        return None

    def counts(self) -> Dict[str, int]:
        result = {state.value: 0 for state in State}
        for decision in self.decisions:
            result[decision.state.value] += 1
        return result

    def ordered_paths(self) -> List[str]:
        """Emission order: group order, then normalised path within each group.

        Ungrouped files follow all groups. This is the only thing group
        membership controls, and it changes no inclusion decision.
        """
        order = {group.id: group.order for group in self.groups}
        return [d.path for d in sorted(
            self.included(),
            key=lambda d: (order.get(d.group, 10 ** 6) if d.group else 10 ** 6,
                           d.path))]

    def estimated_payload_bytes(self, binary_paths: Iterable[str] = (),
                                header_bytes: int = 0) -> int:
        """Estimated emitted size, per Paul's S-09 ruling.

        Binary entries are base64, so the exact expansion is `4*ceil(n/3)` -
        not a rounded 1.33x, which is short by about 6 bytes per KB. Header
        overhead is added per included entry by the caller's profile estimate.
        """
        binaries = {normalise(p) for p in binary_paths}
        total = 0
        for decision in self.included():
            size = decision.size
            total += (4 * -(-size // 3)) if decision.path in binaries else size
            total += header_bytes
        return total

    def to_dict(self) -> Dict[str, object]:
        return {
            "generation": self.generation,
            "counts": self.counts(),
            "rule_stack_digest": self.rule_stack_digest,
            "source_digests": [{"source": s, "sha256": d}
                               for s, d in self.source_digests],
            "pruned_roots": list(self.pruned_roots),
            "warnings": list(self.warnings),
            "groups": [{"id": g.id, "label": g.label or g.id, "order": g.order}
                       for g in sorted(self.groups, key=lambda g: (g.order, g.id))],
            "order": self.ordered_paths(),
            "decisions": [d.to_dict() for d in self.decisions],
        }


# ---------------------------------------------------------------------------
# Digests - S-08 provenance, in memory only (never in transport)
# ---------------------------------------------------------------------------


def rule_source_digest(payload: object) -> str:
    """SHA-256 over canonical JSON: sorted keys, preserved arrays, no clock."""
    text = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def rule_stack_digest(sources: Sequence[Tuple[str, str]]) -> str:
    """One digest over the ordered stack of contributing sources."""
    return rule_source_digest([{"source": s, "sha256": d} for s, d in sources])


# ---------------------------------------------------------------------------
# The engine
# ---------------------------------------------------------------------------


class SelectionEngine:
    """Evaluates the ladder for a set of candidate paths.

    Deliberately free of I/O. It is handed metadata - paths and sizes - and
    returns decisions. That separation is what lets a 4,000-path plan be
    recomputed on a checkbox click without touching the disk.
    """

    def __init__(self,
                 rules: Sequence[SelectionRule],
                 groups: Sequence[SelectionGroup] = (),
                 base_action: Action = Action.INCLUDE,
                 hard_safety: Sequence[Tuple[str, str]] = HARD_SAFETY_PATTERNS,
                 confirm_patterns: Sequence[str] = CONFIRM_ON_OVERRIDE) -> None:
        self.groups = tuple(sorted(groups, key=lambda g: (g.order, g.id)))
        self.base_action = base_action
        self.confirm_patterns = tuple(confirm_patterns)

        safety = [
            SelectionRule(id=f"safety:{code.lower()}", action=Action.BLOCK,
                          pattern=pattern, layer=Layer.HARD_SAFETY,
                          order=index, code=code, label="hard safety",
                          source="governed")
            for index, (pattern, code) in enumerate(hard_safety)
        ]
        self._rules = tuple(safety) + tuple(rules)

        # Bucketed once, in ladder order. The first implementation sorted the
        # whole rule list per layer per path - 32,000 sorts for a 4,000-path
        # plan, and the reason it missed its own budget by 8x.
        self._buckets: Tuple[Tuple[Layer, Tuple[SelectionRule, ...]], ...] = tuple(
            (layer, tuple(sorted((r for r in self._rules if r.layer is layer),
                                 key=lambda r: r.order)))
            for layer in LADDER if layer is not Layer.BASE_ACTION
        )
        # `decide()` normalises its target once.  The former hot path then called
        # SelectionRule.applies_to(), which routed through matches() and
        # normalised that same target again for every rule.  A real 79,826-path
        # BFT workspace performed 6.6 million posixpath.normpath calls and spent
        # tens of seconds after discovery had already reached 100%.  Compile the
        # already-normalised patterns once with the buckets and match the
        # already-normalised target directly.
        self._matcher_buckets = tuple(
            (layer, tuple((rule, _compiled(normalise(rule.pattern)))
                          for rule in rules))
            for layer, rules in self._buckets
        )

    # -- evaluation ------------------------------------------------------

    def _layer_rules(self, layer: Layer) -> List[SelectionRule]:
        """Rules in one layer, in configured order. Retained for callers/tests."""
        for bucket_layer, rules in self._buckets:
            if bucket_layer is layer:
                return list(rules)
        return []

    def decide(self, path: str, size: int = 0,
               unknown_reason: str = "") -> SelectionDecision:
        """Evaluate one path through the whole ladder."""
        target = normalise(path)
        chain: List[ChainEntry] = []
        winner: Optional[SelectionRule] = None

        for layer, layer_rules in self._matcher_buckets:
            layer_winner = None
            for rule, matcher in layer_rules:
                if rule.enabled and matcher.match(target) is not None:
                    chain.append(ChainEntry(layer, rule.id, rule.action,
                                            rule.pattern, False))
                    layer_winner = rule          # last match in layer wins
            if layer_winner is not None and winner is None:
                winner = layer_winner
                if layer is Layer.HARD_SAFETY:
                    break                        # nothing may outrank this

        # mark the winning entry
        if winner is not None:
            chain = [
                ChainEntry(e.layer, e.rule_id, e.action, e.pattern,
                           e.rule_id == winner.id and e.layer is winner.layer
                           and e.pattern == winner.pattern)
                for e in chain
            ]

        if unknown_reason:
            return SelectionDecision(
                path=target, state=State.UNKNOWN, chain=tuple(chain),
                code="UNKNOWN_METADATA", detail=unknown_reason, size=size,
                group=self._group_for(target))

        if winner is None:
            state = (State.INCLUDED if self.base_action is Action.INCLUDE
                     else State.EXCLUDED)
            return SelectionDecision(
                path=target, state=state, winning_rule="base-action",
                winning_layer=Layer.BASE_ACTION, chain=tuple(chain),
                code=f"BASE_ACTION_{self.base_action.value.upper()}",
                detail=f"no rule matched; base action is {self.base_action.value}",
                size=size, group=self._group_for(target))

        if winner.action is Action.BLOCK:
            state = State.BLOCKED
        elif winner.action is Action.INCLUDE:
            state = State.INCLUDED
        else:
            state = State.EXCLUDED

        confirm = (state is State.INCLUDED
                   and winner.layer <= Layer.CLI_RULES
                   and any(matches(p, target) for p in self.confirm_patterns))

        return SelectionDecision(
            path=target, state=state, winning_rule=winner.id,
            winning_layer=winner.layer, chain=tuple(chain),
            code=winner.code or f"{winner.layer.name}_{winner.action.value.upper()}",
            detail=winner.describe(), confirm_required=confirm, size=size,
            group=self._group_for(target) if state is State.INCLUDED else "")

    def _group_for(self, path: str) -> str:
        """First matching group by configured order becomes primary."""
        for group in self.groups:
            if group.claims(path):
                return group.id
        return ""

    def plan(self, candidates: Sequence[Tuple[str, int]],
             pruned_roots: Sequence[str] = (),
             warnings: Sequence[str] = (),
             source_digests: Sequence[Tuple[str, str]] = (),
             generation: int = 1,
             unknown: Optional[Dict[str, str]] = None,
             progress: Optional[ProgressSink] = None,
             cancel: Optional[CancelCheck] = None) -> SelectionPlan:
        """Evaluate every candidate and return an immutable plan.

        Rule evaluation is a real phase of planning.  On large workspaces it
        must report its own progress and honour cancellation instead of leaving
        a completed discovery bar on screen while unreported work continues.
        """
        unknown = unknown or {}
        total = len(candidates)
        reporter = ThrottledReporter(
            progress, OP_BUNDLE, PHASE_PLAN, "files", total=total)
        decisions = []
        for index, (path, size) in enumerate(candidates):
            if index % 128 == 0:
                raise_if_cancelled(
                    cancel, operation=OP_BUNDLE, phase=PHASE_PLAN,
                    completed=index, total=total)
            decisions.append(
                self.decide(path, size, unknown.get(normalise(path), "")))
            reporter.tick(index + 1, message=f"Evaluated {index + 1} of {total} files")
        raise_if_cancelled(
            cancel, operation=OP_BUNDLE, phase=PHASE_PLAN,
            completed=total, total=total)
        reporter.close(total, message=f"Evaluated {total} files")
        return SelectionPlan(
            decisions=tuple(decisions),
            groups=self.groups,
            pruned_roots=tuple(sorted(normalise(p) for p in pruned_roots)),
            warnings=tuple(warnings),
            source_digests=tuple(source_digests),
            rule_stack_digest=rule_stack_digest(source_digests),
            generation=generation,
        )


# ---------------------------------------------------------------------------
# Building a rule stack from existing governed configuration
# ---------------------------------------------------------------------------


def rules_from_globs(allow: Sequence[str], deny: Sequence[str],
                     layer: Layer = Layer.GOVERNED_DEFAULT,
                     source: str = "governed") -> List[SelectionRule]:
    """Translate today's allow/deny lists into ladder rules.

    Deny patterns already covered by hard safety are dropped rather than
    duplicated, so a path blocked at Priority 0 shows one reason, not two.
    """
    safety_patterns = {pattern for pattern, _ in HARD_SAFETY_PATTERNS}
    rules: List[SelectionRule] = []
    order = 0
    for pattern in allow:
        if pattern == "**/*":
            continue                     # that is the base action, not a rule
        rules.append(SelectionRule(id=f"allow:{pattern}", action=Action.INCLUDE,
                                   pattern=pattern, layer=layer, order=order,
                                   source=source))
        order += 1
    for pattern in deny:
        if pattern in safety_patterns:
            continue
        rules.append(SelectionRule(id=f"deny:{pattern}", action=Action.EXCLUDE,
                                   pattern=pattern, layer=layer, order=order,
                                   source=source))
        order += 1
    return rules


def base_action_for(allow: Sequence[str]) -> Action:
    """An allow-list narrower than everything implies exclude-by-default.

    This is the `--include` semantic I raised in BFT-DEV-RESPONSE-2026-08-25-02:
    `--include src/**` must not merely add an include rule, because every
    non-matching file would then survive on the base action and the output would
    silently broaden. An allow-list is a base-action switch.
    """
    patterns = [p for p in allow if p]
    if not patterns or any(p == "**/*" for p in patterns):
        return Action.INCLUDE
    return Action.EXCLUDE
