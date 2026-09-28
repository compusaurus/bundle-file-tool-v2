# BFT_B115_WORKSPACE_MODEL - the Selection Workspace, without a toolkit
# ===================================================================================================
# SOURCEFILE: workspace_model.py
# RELPATH: bundle_file_tool_v2/src/ui/workspace_model.py
# PROJECT: Bundle File Tool v2.2
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.115
# LIFECYCLE: Testing
# STATUS: Build 115 - WP4 - BFT_B115_WORKSPACE_MODEL
# DESCRIPTION: View-model for the desktop Selection Workspace. Pure Python;
#              imports no toolkit, so every rule of the UI is testable headless.
# Relative Path: src/ui/workspace_model.py
# Purpose:
# independent_entry_point:
# ===================================================================================================
"""Everything the workspace does, expressed without a widget.

`BFT_SELECTION_WORKSPACE_DESIGN_SPEC` §7 describes a window with a tri-state
folder tree, a filtered decision list, an inspector and a rules panel. Almost
all of that is *logic*: which node is partially checked, what a bulk action
would affect, what one checkbox does to the plan, what the counts are.

That logic lives here rather than in the Tk frame, for a reason with history.
`src/ui/bundle_frame.py` and its siblings are excluded from the coverage gate
because they need a display, and everything inside them is therefore unmeasured.
Build 108 put `tk_progress.py` back under the gate by keeping the widget thin
and testing it against a real Tk root; this module goes further - it has no
toolkit at all, so the entire behaviour of the workspace can be asserted in a
headless test run.

**It reimplements no precedence.** SEL-X-002 forbids that, and it would be a
slow disaster besides: every question about inclusion is answered by
`BundleToolService`, and this module only arranges the answers. A checkbox
becomes one ordered session override and a `replan()`; it never edits a
decision directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.selection import (
    CONFIRM_ON_OVERRIDE,
    Action,
    Layer,
    SelectionRule,
    State,
    matches,
    normalise,
)
from core.service import BundleToolService, PlanResult


# ---------------------------------------------------------------------------
# Value types
# ---------------------------------------------------------------------------

class TriState(str, Enum):
    """A folder checkbox has three states, and the third one is the point."""

    CHECKED = "checked"
    UNCHECKED = "unchecked"
    PARTIAL = "partial"


#: Badge text by detector family. Text, never colour alone - §7.2 is explicit
#: that colour may not be the only carrier of meaning, and a screen reader has
#: to be able to say why a folder is excluded.
FAMILY_BADGES: Dict[str, str] = {
    "python-venv": "Python env",
    "conda-env": "Conda env",
    "node-modules": "Node modules",
}

#: Preset sources whose exclusions are about bulk rather than hygiene.
BULK_PRESETS = ("preset:media", "preset:archives")


@dataclass(frozen=True)
class TreeNode:
    """One row of the folders-and-groups pane."""

    path: str
    label: str
    depth: int
    is_dir: bool
    state: TriState
    included: int = 0
    total: int = 0
    badge: str = ""
    badge_code: str = ""
    pruned: bool = False
    enumerated: bool = True
    overridden: bool = False

    @property
    def count_text(self) -> str:
        """What the count column shows.

        A pruned root reports "not enumerated" rather than a number. §7.4 is
        explicit: BFT must not imply it inspected files it intentionally did
        not walk, and "0" would be exactly that implication.
        """
        if not self.enumerated:
            return "not enumerated"
        if not self.is_dir:
            return ""
        return str(self.total)

    def accessible_text(self) -> str:
        """One spoken line carrying state, reason and scale."""
        parts = [self.label, self.state.value]
        if self.badge:
            parts.append(self.badge)
        if self.is_dir and self.enumerated:
            parts.append(f"{self.included} of {self.total} included")
        elif not self.enumerated:
            parts.append("contents not enumerated")
        return ", ".join(parts)


@dataclass(frozen=True)
class DecisionRow:
    """One row of the decision list."""

    path: str
    state: str
    included: bool
    rule_label: str
    layer: str
    group: str
    reason: str
    overridden: bool = False
    confirm_required: bool = False
    size: int = 0

    def accessible_text(self) -> str:
        return f"{self.path}, {self.state}, {self.reason}"


@dataclass(frozen=True)
class RuleRow:
    """One entry in the rules-in-effect panel."""

    label: str
    layer: str
    layer_label: str
    action: str
    patterns: Tuple[str, ...]
    source: str
    enabled: bool = True
    locked: bool = False

    @property
    def pattern_text(self) -> str:
        return " · ".join(self.patterns)


@dataclass(frozen=True)
class Summary:
    """The summary band. Every number comes from the plan, none is derived."""

    included: int
    excluded: int
    blocked: int
    unknown: int
    estimated_bytes: int
    overrides: int
    groups: int
    generation: int
    pruned_roots: int = 0

    def headline(self) -> str:
        parts = [f"{self.included} included", f"{self.excluded} excluded"]
        if self.blocked:
            parts.append(f"{self.blocked} blocked")
        if self.pruned_roots:
            # The render shows "3,898 excluded" because its mock enumerated the
            # environment. We do not walk it, so a file count would be an
            # invention - S7.4 forbids implying we inspected what we skipped.
            # The honest equivalent names the roots instead.
            noun = "root" if self.pruned_roots == 1 else "roots"
            parts.append(f"{self.pruned_roots} pruned {noun}")
        parts.append(f"{human_bytes(self.estimated_bytes)} estimated")
        if self.overrides:
            noun = "override" if self.overrides == 1 else "overrides"
            parts.append(f"{self.overrides} explicit {noun}")
        if self.groups:
            parts.append(f"{self.groups} user-defined groups")
        return "   ".join(parts)


@dataclass(frozen=True)
class Inspector:
    """The explanation panel for one selected path."""

    path: str
    state: str
    headline: str
    chain: Tuple[str, ...]
    group: str = ""
    can_override: bool = True
    override_action: str = "Override for session"
    confirm_required: bool = False


@dataclass
class BulkScope:
    """What a bulk action would do, stated before it is done."""

    action: str
    count: int
    paths: Tuple[str, ...] = ()

    def describe(self) -> str:
        noun = "file" if self.count == 1 else "files"
        return f"{self.action} {self.count} visible {noun}"


def human_bytes(count: int) -> str:
    size = float(count)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


# ---------------------------------------------------------------------------
# The model
# ---------------------------------------------------------------------------

VIEW_ALL = "all"
VIEW_INCLUDED = "included"
VIEW_EXCLUDED = "excluded"
VIEW_BLOCKED = "blocked"
VIEWS = (VIEW_ALL, VIEW_INCLUDED, VIEW_EXCLUDED, VIEW_BLOCKED)


class WorkspaceModel:
    """Holds one plan and turns operator actions into the next one."""

    def __init__(self, service: BundleToolService, result: PlanResult) -> None:
        self.service = service
        self.result = result
        #: Ordered (action, pattern) pairs. The order is load-bearing: Layer 1
        #: is last-match-wins, so this list *is* the operator's action history.
        self._overrides: List[Tuple[str, str]] = [
            (str(a), str(p)) for a, p in result.inputs.get("overrides", [])
        ]
        self._history: List[List[Tuple[str, str]]] = [list(self._overrides)]
        self._cursor = 0
        self._children_cache = None
        self._indexed_scan = result.scan
        self._reindex()

    # -- indexing --------------------------------------------------------

    def _reindex(self) -> None:
        """Aggregate per-directory counts once per plan, not once per query.

        A 4,000-path tree is re-rendered on every checkbox, so the counts have
        to be a lookup rather than a walk. One pass up each path's ancestry
        gives every directory its included/total pair.
        """
        included: Dict[str, int] = {}
        total: Dict[str, int] = {}
        state_totals: Dict[State, Dict[str, int]] = {
            state: {} for state in State
        }
        self._decisions = {d.path: d for d in self.result.plan.decisions}
        self._longest_decision_name = ""

        for decision in self.result.plan.decisions:
            is_in = decision.state is State.INCLUDED
            name = decision.path.rsplit("/", 1)[-1]
            if len(name) > len(self._longest_decision_name):
                self._longest_decision_name = name
            for parent in _ancestors(decision.path):
                total[parent] = total.get(parent, 0) + 1
                if is_in:
                    included[parent] = included.get(parent, 0) + 1
                by_state = state_totals[decision.state]
                by_state[parent] = by_state.get(parent, 0) + 1
        self._dir_included = included
        self._dir_total = total
        self._dir_state_total = state_totals

        self._pruned: Dict[str, str] = {}
        for row in self.result.scan.ledger.to_report():
            if row.get("result") == "detected":
                self._pruned[str(row["path"])] = str(row.get("family", ""))

    # -- summary ---------------------------------------------------------

    def summary(self) -> Summary:
        counts = self.result.plan.counts()
        return Summary(
            included=counts.get(State.INCLUDED.value, 0),
            excluded=counts.get(State.EXCLUDED.value, 0),
            blocked=counts.get(State.BLOCKED.value, 0),
            unknown=counts.get(State.UNKNOWN.value, 0),
            estimated_bytes=self.result.estimated_bytes(),
            overrides=len(self._overrides),
            groups=len(self.result.plan.groups),
            generation=self.result.plan.generation,
            pruned_roots=len(self.result.plan.pruned_roots),
        )

    def status_text(self) -> str:
        """The footer. Says what actually happened, and nothing more.

        WP5 will add preview-cache figures here. Until it exists this reports
        only what this build can honestly claim - the same discipline §7.4
        applies to pruned directory counts.
        """
        return "Ready — selection plan computed without reading content"

    # -- the folder tree -------------------------------------------------

    def tree(self, expanded: Optional[Iterable[str]] = None) -> List[TreeNode]:
        """Visible tree rows, honouring which folders are expanded.

        Only children of expanded folders are produced, so a 4,000-file tree
        costs one screen of rows rather than 4,000.
        """
        open_dirs = {normalise(p) for p in (expanded or ())}
        open_dirs.add("")

        children = self._children_index()
        rows: List[TreeNode] = []

        def walk(parent: str, depth: int) -> None:
            for name, path, is_dir in children.get(parent, ()):
                rows.append(self._node(path, name, depth, is_dir))
                if is_dir and path in open_dirs:
                    walk(path, depth + 1)

        walk("", 0)
        return rows

    def has_children(self, path: str) -> bool:
        """Whether a folder can be expanded without enumerating pruned roots."""

        return bool(self._children_index().get(normalise(path)))

    def _children_index(self) -> Dict[str, List[Tuple[str, str, bool]]]:
        """parent -> [(name, path, is_dir)], directories first, then by name."""
        if getattr(self, "_children_cache", None) is not None:
            return self._children_cache

        index: Dict[str, Dict[str, bool]] = {}
        paths = list(self._decisions) + list(self._pruned)
        for path in paths:
            parts = path.split("/")
            for depth in range(len(parts)):
                parent = "/".join(parts[:depth])
                child = "/".join(parts[:depth + 1])
                is_dir = depth < len(parts) - 1 or child in self._pruned
                index.setdefault(parent, {})
                index[parent][child] = index[parent].get(child, False) or is_dir

        built: Dict[str, List[Tuple[str, str, bool]]] = {}
        for parent, kids in index.items():
            rows = [(child.rsplit("/", 1)[-1], child, is_dir)
                    for child, is_dir in kids.items()]
            rows.sort(key=lambda row: (not row[2], row[0].lower()))
            built[parent] = rows
        self._children_cache = built
        return built

    def _node(self, path: str, name: str, depth: int, is_dir: bool) -> TreeNode:
        overridden = any(_covers(pattern, path) for _, pattern in self._overrides)

        if path in self._pruned:
            family = self._pruned[path]
            return TreeNode(
                path=path, label=name, depth=depth, is_dir=True,
                state=TriState.UNCHECKED, included=0, total=0,
                badge=FAMILY_BADGES.get(family, "Detector"),
                badge_code=family, pruned=True, enumerated=False,
                overridden=overridden)

        if not is_dir:
            decision = self._decisions.get(path)
            state = (TriState.CHECKED
                     if decision is not None and decision.state is State.INCLUDED
                     else TriState.UNCHECKED)
            return TreeNode(
                path=path, label=name, depth=depth, is_dir=False, state=state,
                included=1 if state is TriState.CHECKED else 0, total=1,
                badge=self._badge_for(path), badge_code="",
                overridden=overridden)

        total = self._dir_total.get(path, 0)
        included = self._dir_included.get(path, 0)
        if total and included == total:
            state = TriState.CHECKED
        elif included == 0:
            state = TriState.UNCHECKED
        else:
            state = TriState.PARTIAL
        return TreeNode(
            path=path, label=name, depth=depth, is_dir=True, state=state,
            included=included, total=total,
            badge="" if included else self._badge_for_dir(path),
            overridden=overridden)

    def _badge_for(self, path: str) -> str:
        decision = self._decisions.get(path)
        if decision is None:
            return ""
        if decision.state is State.BLOCKED:
            return "Blocked"
        if decision.state is not State.EXCLUDED:
            return ""
        rule = self._winning_rule(decision.winning_rule)
        if rule is not None and rule.source.startswith(BULK_PRESETS):
            return "Large media"
        return "Rule"

    def _badge_for_dir(self, path: str) -> str:
        """A wholly excluded directory borrows the badge of its first child."""
        for candidate, decision in self._decisions.items():
            if candidate.startswith(path + "/"):
                return self._badge_for(candidate)
        return ""

    def _winning_rule(self, rule_id: str) -> Optional[SelectionRule]:
        for rule in self.result.rules:
            if rule.id == rule_id:
                return rule
        return None

    # -- the decision list -----------------------------------------------

    def rows(self, view: str = VIEW_ALL, search: str = "",
             limit: int = 0, hide_blocked: bool = False) -> List[DecisionRow]:
        """Filtered decisions, in emission order for included files.

        Search matches the path *or* the reason, which is what the render's
        "Filter paths or reasons" promises: an operator who wants to see
        everything the Python-environment rule touched can type its name.
        """
        if view not in VIEWS:
            raise ValueError(f"Unknown view '{view}'. Use one of: {', '.join(VIEWS)}")
        needle = search.strip().lower()
        wanted = {
            VIEW_INCLUDED: State.INCLUDED,
            VIEW_EXCLUDED: State.EXCLUDED,
            VIEW_BLOCKED: State.BLOCKED,
        }.get(view)

        order = {path: index for index, path
                 in enumerate(self.result.plan.ordered_paths())}
        selected = []
        for decision in self.result.plan.decisions:
            if wanted is not None and decision.state is not wanted:
                continue
            # Blocked paths cannot be included and are not actionable, so a
            # tree full of them is noise on a project that has many. Hiding is
            # a view filter only: the counts still report them, because
            # pretending they are not there would be the same dishonesty as
            # inventing a descendant count for a pruned directory.
            if (hide_blocked and view != VIEW_BLOCKED
                    and decision.state is State.BLOCKED):
                continue
            row = self._row(decision)
            if needle and needle not in row.path.lower() \
                    and needle not in row.reason.lower():
                continue
            selected.append(row)

        selected.sort(key=lambda r: (order.get(r.path, 10 ** 9), r.path))
        return selected[:limit] if limit else selected

    def decision_count(self, view: str = VIEW_ALL,
                       hide_blocked: bool = False) -> int:
        """Count a non-search decision view without constructing its rows."""

        if view not in VIEWS:
            raise ValueError(f"Unknown view '{view}'. Use one of: {', '.join(VIEWS)}")
        count = self.counts_for_views()[view]
        if hide_blocked and view == VIEW_ALL:
            count -= self.counts_for_views()[VIEW_BLOCKED]
        return count

    def decision_children(self, parent: str = "", view: str = VIEW_ALL,
                          hide_blocked: bool = False
                          ) -> List[Tuple[str, bool]]:
        """Immediate filtered children for the native UI's virtual tree.

        The hierarchy is the same immutable scan topology used by the folder
        pane. Reusing it prevents a large decision plan from being re-indexed a
        second time after every I/O-free override.
        """

        if view not in VIEWS:
            raise ValueError(f"Unknown view '{view}'. Use one of: {', '.join(VIEWS)}")
        parent = normalise(parent) if parent else ""
        selected: List[Tuple[str, bool]] = []
        for _name, path, is_dir in self._children_index().get(parent, ()):
            if is_dir:
                if self._decision_descendant_count(path, view, hide_blocked):
                    selected.append((path, True))
                continue
            decision = self._decisions.get(path)
            if decision is not None and self._decision_matches_view(
                    decision, view, hide_blocked):
                selected.append((path, False))
        return selected

    def decision_row(self, path: str) -> DecisionRow:
        """Create one visible row, rather than every collapsed descendant."""

        decision = self._decisions.get(normalise(path))
        if decision is None:
            raise KeyError(path)
        return self._row(decision)

    def decision_width_hints(self) -> Dict[str, str]:
        """Representative values for bounded native column measurement."""

        return {
            "#0": f"[x] {self._longest_decision_name}",
            "state": max((state.value for state in State), key=len),
            "reason": "Default selection rule or session override",
        }

    def _decision_descendant_count(self, path: str, view: str,
                                   hide_blocked: bool) -> int:
        if view == VIEW_ALL:
            count = self._dir_total.get(path, 0)
            if hide_blocked:
                count -= self._dir_state_total[State.BLOCKED].get(path, 0)
            return count
        state = {
            VIEW_INCLUDED: State.INCLUDED,
            VIEW_EXCLUDED: State.EXCLUDED,
            VIEW_BLOCKED: State.BLOCKED,
        }[view]
        return self._dir_state_total[state].get(path, 0)

    @staticmethod
    def _decision_matches_view(decision, view: str,
                               hide_blocked: bool) -> bool:
        wanted = {
            VIEW_INCLUDED: State.INCLUDED,
            VIEW_EXCLUDED: State.EXCLUDED,
            VIEW_BLOCKED: State.BLOCKED,
        }.get(view)
        if wanted is not None and decision.state is not wanted:
            return False
        return not (
            hide_blocked and view != VIEW_BLOCKED
            and decision.state is State.BLOCKED
        )

    def _row(self, decision) -> DecisionRow:
        rule = self._winning_rule(decision.winning_rule)
        label = rule.label if rule is not None and rule.label else decision.winning_rule
        layer = decision.winning_layer.display if decision.winning_layer else ""
        overridden = decision.winning_layer is Layer.SESSION
        return DecisionRow(
            path=decision.path,
            state=decision.state.value,
            included=decision.state is State.INCLUDED,
            rule_label=label or "base action",
            layer=layer,
            group=decision.group,
            reason=self._reason(decision, rule),
            overridden=overridden,
            confirm_required=decision.confirm_required,
            size=decision.size,
        )

    def _reason(self, decision, rule: Optional[SelectionRule]) -> str:
        """A short human phrase, not a rule id."""
        if decision.winning_layer is None:
            return f"base action ({self.result.base_action})"
        if decision.winning_layer is Layer.SESSION:
            return "Session override"
        if decision.winning_layer is Layer.HARD_SAFETY:
            return "Recursion hazard"
        if rule is not None and rule.label:
            return rule.label
        return decision.winning_layer.label

    def counts_for_views(self) -> Dict[str, int]:
        """Counts per filter tab, reconciled with the plan (SEL-F-004)."""
        counts = self.result.plan.counts()
        return {
            VIEW_ALL: len(self.result.plan.decisions),
            VIEW_INCLUDED: counts.get(State.INCLUDED.value, 0),
            VIEW_EXCLUDED: counts.get(State.EXCLUDED.value, 0),
            VIEW_BLOCKED: counts.get(State.BLOCKED.value, 0),
        }

    # -- inspector -------------------------------------------------------

    def inspector(self, path: str) -> Optional[Inspector]:
        """Explain one path - including a folder, which has no decision.

        A pruned environment root is the case that matters. Its files were
        never walked, so none of them is in the plan and none can be selected;
        the folder itself is what the operator clicks, and it has to be able to
        say why it is excluded and what it would cost to descend. Explaining
        only files would leave the single most important row in the tree mute.
        """
        target = normalise(path)
        decision = self.result.plan.explain(target)
        if decision is None:
            node = self.node_for(target)
            return self._directory_inspector(node) if node is not None else None
        rule = self._winning_rule(decision.winning_rule)
        blocked = decision.state is State.BLOCKED
        return Inspector(
            path=decision.path,
            state=decision.state.value,
            headline=self._headline(decision, rule),
            chain=tuple(decision.explain()[1:]),
            group=decision.group,
            can_override=not blocked,
            override_action=("Cannot be overridden" if blocked
                             else "Restore rule result"
                             if decision.winning_layer is Layer.SESSION
                             else "Override for session"),
            confirm_required=decision.confirm_required,
        )

    def _directory_inspector(self, node: TreeNode) -> Inspector:
        """The explanation for a folder row."""
        if node.pruned:
            family = FAMILY_BADGES.get(node.badge_code, node.badge_code)
            evidence = self._evidence_for(node.path)
            return Inspector(
                path=node.path,
                state="Excluded",
                headline=(f"Excluded because {node.path} is a {family} "
                          f"({evidence}). Its contents were never enumerated, "
                          f"so nothing inside it was read or listed. This works "
                          f"regardless of folder name."),
                chain=(f"[4] detector: {node.badge_code}",),
                can_override=True,
                override_action="Scan this folder anyway",
            )
        return Inspector(
            path=node.path,
            state=node.state.value,
            headline=(f"{node.included} of {node.total} files included."
                      if node.total else "No files under this folder."),
            chain=(),
            can_override=True,
            override_action=("Exclude this folder"
                             if node.state is not TriState.UNCHECKED
                             else "Include this folder"),
        )

    def _headline(self, decision, rule: Optional[SelectionRule]) -> str:
        """The sentence under the path in the inspector.

        Modelled on the render: "Excluded by 'Python environments' because
        .venv312 contains pyvenv.cfg. This works regardless of environment
        folder name."
        """
        if decision.state is State.BLOCKED:
            return (f"Blocked at priority 0 as a recursion hazard. "
                    f"This cannot be overridden.")
        for root, family in self._pruned.items():
            if decision.path == root or decision.path.startswith(root + "/"):
                evidence = self._evidence_for(root)
                return (f"Excluded because {root} is a "
                        f"{FAMILY_BADGES.get(family, family)} "
                        f"({evidence}). This works regardless of folder name.")
        if decision.winning_layer is None:
            return f"No rule matched; the base action is {self.result.base_action}."
        verb = "Included" if decision.state is State.INCLUDED else "Excluded"
        name = rule.label if rule is not None and rule.label else decision.winning_rule
        return (f"{verb} by “{name}” at priority "
                f"{decision.winning_layer.display} "
                f"({decision.winning_layer.label}).")

    def _evidence_for(self, root: str) -> str:
        for row in self.result.scan.ledger.to_report():
            if row.get("path") == root:
                return ", ".join(str(e) for e in row.get("evidence", ())) or "signature match"
        return "signature match"

    # -- rules in effect -------------------------------------------------

    def rules_in_effect(self) -> List[RuleRow]:
        """Active rules grouped by their source, highest priority first.

        Governed policy is rendered `locked`. §7.3: the rule editor must never
        write `bundle_config.json`, so the layer that comes from it is shown
        and never offered for edit.
        """
        buckets: Dict[Tuple[str, str, str], List[str]] = {}
        meta: Dict[Tuple[str, str, str], SelectionRule] = {}
        for rule in self.result.rules:
            if not rule.enabled:
                continue
            key = (rule.source, rule.action.value, rule.label or rule.source)
            buckets.setdefault(key, []).append(rule.pattern)
            meta.setdefault(key, rule)

        rows = []
        for key, patterns in buckets.items():
            rule = meta[key]
            source, action, label = key
            rows.append(RuleRow(
                label=label,
                layer=rule.layer.display,
                layer_label=rule.layer.label,
                action=action,
                patterns=tuple(patterns),
                source=source,
                locked=rule.layer is Layer.GOVERNED_DEFAULT
                or rule.layer is Layer.HARD_SAFETY,
            ))
        rows.sort(key=lambda r: (Layer(_layer_value(r.layer)).value, r.label.lower()))
        return rows

    # -- commands --------------------------------------------------------

    def set_folder(self, path: str, include: bool) -> PlanResult:
        """Check or uncheck a folder: exactly one scoped override (SEL-F-003).

        The override is `path/**`, not one entry per descendant. That is what
        keeps a 300-file folder a single reversible decision the operator can
        read, rather than 300 mutations they cannot.
        """
        return self._apply(_scope_of(normalise(path)), include)

    def set_file(self, path: str, include: bool) -> PlanResult:
        return self._apply(normalise(path), include)

    def toggle(self, path: str) -> PlanResult:
        """Space on the focused row. Partial folders resolve to fully checked."""
        node = self.node_for(path)
        if node is None:
            raise KeyError(path)
        include = node.state is not TriState.CHECKED
        return (self.set_folder(path, include) if node.is_dir
                else self.set_file(path, include))

    def desired_state(self, path: str) -> bool:
        """Would acting on this row include it? True for include.

        Files and folders answer through one rule - "not currently fully
        checked" - because the widget asking must not have to know which it is
        holding. The frame previously compared an inspector's state string
        against "Included", which is a *decision* state; a folder reports a
        *tri-state*, so every folder override came out as include.
        """
        node = self.node_for(path)
        if node is None:
            raise KeyError(path)
        return node.state is not TriState.CHECKED

    def needs_confirmation(self, path: str, include: bool) -> bool:
        """Would including this path override a rule worth confirming?

        Asked of the *proposed* action, not the current decision.
        `confirm_required` on a decision is only ever set once an override has
        already won, so consulting it beforehand always answered False and the
        confirmation never appeared.
        """
        if not include:
            return False
        target = normalise(path)
        scope = target[:-3] if target.endswith("/**") else target
        candidates = [d.path for d in self.result.plan.decisions
                      if d.path == scope or d.path.startswith(scope + "/")]
        return any(any(matches(pattern, candidate)
                       for pattern in CONFIRM_ON_OVERRIDE)
                   for candidate in candidates)

    def node_for(self, path: str) -> Optional[TreeNode]:
        target = normalise(path)
        name = target.rsplit("/", 1)[-1]
        if target in self._pruned:
            return self._node(target, name, 0, True)
        if target in self._decisions:
            return self._node(target, name, 0, False)
        if self._dir_total.get(target):
            return self._node(target, name, 0, True)
        return None

    def _apply(self, pattern: str, include: bool) -> PlanResult:
        action = Action.INCLUDE.value if include else Action.EXCLUDE.value
        overrides = [(a, p) for a, p in self._overrides if p != pattern]
        overrides.append((action, pattern))
        return self._commit(overrides)

    def clear_override(self, pattern: str) -> PlanResult:
        """Remove an override so the underlying rule result returns.

        §7.2: clearing restores the rule result; it does not blindly invert the
        prior action. Removing the entry is exactly that - the ladder decides
        again with nothing at Layer 1 for this pattern.
        """
        target = normalise(pattern)
        return self._commit([(a, p) for a, p in self._overrides if p != target])

    def clear_all_overrides(self) -> PlanResult:
        return self._commit([])

    def bulk_scope(self, action: str, view: str = VIEW_ALL,
                   search: str = "") -> BulkScope:
        """What a bulk action would affect - stated before it runs (§7.2)."""
        rows = self.rows(view=view, search=search)
        return BulkScope(action=action, count=len(rows),
                         paths=tuple(row.path for row in rows))

    def apply_bulk(self, include: bool, view: str = VIEW_ALL,
                   search: str = "") -> PlanResult:
        """Include or exclude the visible set, as one override per path."""
        action = Action.INCLUDE.value if include else Action.EXCLUDE.value
        rows = self.rows(view=view, search=search)
        targets = [row.path for row in rows]
        overrides = [(a, p) for a, p in self._overrides if p not in set(targets)]
        overrides.extend((action, path) for path in targets)
        return self._commit(overrides)

    def set_presets(self, names: Sequence[str]) -> PlanResult:
        """Changing the preset recomputes the plan without reading content."""
        result = self.service.replan(self.result, preset=list(names))
        return self.adopt_result(result)

    def adopt_result(self, result: PlanResult) -> PlanResult:
        """Publish a completed service result and rebuild UI indexes.

        Long replans can be computed on a worker thread without mutating this
        deliberately UI-owned model.  The Tk adapter calls this method only
        after the worker has returned, on the UI thread.
        """
        self.result = result
        self._invalidate()
        return self.result

    def set_groups(self, specs: Sequence[str]) -> PlanResult:
        self.result = self.service.replan(self.result, groups=list(specs))
        self._invalidate()
        return self.result

    def include_root(self, root: str) -> PlanResult:
        """Descend into a pruned directory. A deliberate, costed re-scan."""
        roots = list(self.result.inputs.get("include_roots", []))
        target = normalise(root)
        if target not in roots:
            roots.append(target)
        self.result = self.service.replan(self.result, include_roots=roots)
        self._overrides = [(str(a), str(p))
                           for a, p in self.result.inputs.get("overrides", [])]
        self._record(list(self._overrides))
        self._invalidate()
        return self.result

    def _commit(self, overrides: List[Tuple[str, str]]) -> PlanResult:
        self.result = self.service.replan(self.result, overrides=overrides)
        self._overrides = list(overrides)
        self._record(list(overrides))
        self._invalidate()
        return self.result

    def _invalidate(self) -> None:
        # Overrides, presets and group order change decisions but not the scan
        # topology. Only include_root performs another walk and replaces the
        # ScanResult, so keep the large parent/child index across ordinary UI
        # interactions.
        if self.result.scan is not self._indexed_scan:
            self._children_cache = None
            self._indexed_scan = self.result.scan
        self._reindex()

    # -- undo / redo -----------------------------------------------------

    def _record(self, snapshot: List[Tuple[str, str]]) -> None:
        del self._history[self._cursor + 1:]
        self._history.append(snapshot)
        self._cursor = len(self._history) - 1

    @property
    def can_undo(self) -> bool:
        return self._cursor > 0

    @property
    def can_redo(self) -> bool:
        return self._cursor < len(self._history) - 1

    def undo(self) -> PlanResult:
        """Ctrl+Z operates on the override history, not on tree selection."""
        if not self.can_undo:
            return self.result
        self._cursor -= 1
        return self._restore(self._history[self._cursor])

    def redo(self) -> PlanResult:
        if not self.can_redo:
            return self.result
        self._cursor += 1
        return self._restore(self._history[self._cursor])

    def _restore(self, snapshot: List[Tuple[str, str]]) -> PlanResult:
        self.result = self.service.replan(self.result, overrides=list(snapshot))
        self._overrides = list(snapshot)
        self._invalidate()
        return self.result

    @property
    def overrides(self) -> List[Tuple[str, str]]:
        return list(self._overrides)

    # -- review ----------------------------------------------------------

    def blocked_paths(self) -> List[str]:
        """Paths held at Priority 0. They are already out of the bundle."""
        return [d.path for d in self.result.plan.by_state(State.BLOCKED)]

    def unacknowledged_blocked(self) -> List[str]:
        """Blocked paths the operator has not yet explicitly set aside."""
        acknowledged = {pattern for action, pattern in self._overrides
                        if action == Action.EXCLUDE.value}
        return [path for path in self.blocked_paths() if path not in acknowledged]

    def acknowledge_blocked(self) -> PlanResult:
        """Record blocked paths as deliberately excluded, and move on.

        Blocked paths cannot be included - Priority 0 is not overridable - so
        they were never going into the bundle. But the review had no way to say
        "yes, I know, leave them out", which meant the same warning appeared on
        every single Create Bundle with no way to settle it.

        Writing an explicit exclude for each is honest: it changes no decision,
        it records the operator's acknowledgement, and it shows up in the
        selection report as a deliberate choice rather than an unread warning.
        """
        blocked = set(self.unacknowledged_blocked())
        if not blocked:
            return self.result
        overrides = [(a, p) for a, p in self._overrides if p not in blocked]
        overrides.extend((Action.EXCLUDE.value, path) for path in sorted(blocked))
        return self._commit(overrides)

    def needs_review(self) -> List[str]:
        """Reasons Create Bundle should stop for a final review (§7.2)."""
        reasons: List[str] = []
        counts = self.result.plan.counts()
        blocked = len(self.unacknowledged_blocked())
        if blocked:
            reasons.append(
                f"{blocked} path(s) blocked as recursion hazards - these "
                f"cannot be included and will be left out")
        confirm = [d.path for d in self.result.plan.included() if d.confirm_required]
        if confirm:
            reasons.append(
                f"{len(confirm)} safety override(s) awaiting confirmation")
        if self.result.plan.warnings:
            reasons.append(f"{len(self.result.plan.warnings)} scan warning(s)")
        unknown = counts.get(State.UNKNOWN.value, 0)
        if unknown:
            reasons.append(f"{unknown} path(s) in an unknown state")
        return reasons


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ancestors(path: str) -> List[str]:
    """Every directory containing `path`, nearest last. Excludes the file."""
    parts = path.split("/")[:-1]
    return ["/".join(parts[:i + 1]) for i in range(len(parts))]


def _scope_of(path: str) -> str:
    return f"{path}/**" if not path.endswith("/**") else path


def _covers(pattern: str, path: str) -> bool:
    if pattern == path:
        return True
    if pattern.endswith("/**"):
        root = pattern[:-3]
        return path == root or path.startswith(root + "/")
    return False


def _layer_value(display: str) -> int:
    for layer in Layer:
        if layer.display == display:
            return layer.value
    return Layer.BASE_ACTION.value
