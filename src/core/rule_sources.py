# BFT_B114_RULE_SOURCES - where a rule stack comes from, and who wins
# ===================================================================================================
# SOURCEFILE: rule_sources.py
# RELPATH: bundle_file_tool_v2/src/core/rule_sources.py
# PROJECT: Bundle File Tool v2.2
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.114
# LIFECYCLE: Testing
# STATUS: Build 114 - WP3 - BFT_B114_RULE_SOURCES
# DESCRIPTION: Shipped presets, project rule files, and CLI/session overrides,
#              each translated into ladder rules at its own layer.
# Relative Path: src/core/rule_sources.py
# Purpose:
# independent_entry_point:
# ===================================================================================================
"""The ladder has eight layers; this module fills six of them.

`SelectionEngine` does not care where a rule came from - it evaluates whatever
it is handed. This module is the other half: it turns the things an operator
actually names (`--preset python-env`, `--rules team.json`, `--exclude '*.log'`)
into `SelectionRule` objects at the correct layer, and produces a digest for
each source so a plan can prove which inputs produced it.

Everything here is configurable, per Ringo's standing direction. The shipped
presets below are defaults, not a closed set: `selection.presets` in the
governed config adds new presets and overrides shipped ones by name, and a
project rules file can define its own. What is *not* configurable is the layer
each source lands on - that is the precedence contract, and letting a preset
declare itself Priority 1 would make the ladder decorative.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from core.exceptions import BundleFileToolError
from core.selection import (
    Action,
    Layer,
    SelectionGroup,
    SelectionRule,
    rule_source_digest,
)


class RuleSourceError(BundleFileToolError):
    """A preset name or rules file that cannot be honoured.

    Raised rather than warned. A rules file the operator named and the tool
    silently ignored is the exact failure the workspace exists to end: the
    bundle would look plausible and be wrong.
    """


# ---------------------------------------------------------------------------
# Shipped presets (Layer 4)
# ---------------------------------------------------------------------------

# Deny-oriented by default: a preset trims noise, it does not decide the shape
# of the bundle. `source-only` is the one allow-list preset, and because an
# allow-list is a base-action switch it is documented as such below.
SHIPPED_PRESETS: Dict[str, Dict[str, Any]] = {
    "bft-source": {
        "label": "BFT governed source (excludes generated working trees)",
        # Build 124: bundling BFT from its repository root used to ingest its
        # own pytest scratch trees, delivery output and prior artifacts.  On
        # the measured Build 123 tree that was 68,000+ irrelevant paths.  Keep
        # this project-specific rather than teaching the generic engine to
        # interpret .gitignore or treating every directory named ``out`` as
        # unsafe source.
        "deny": [
            "**/.git/**", "**/.governance_backups/**",
            "**/.venv/**", "**/.venv311/**", "**/.venv312/**",
            "**/.venv313/**", "**/venv/**", "**/__pycache__/**",
            "**/.pytest_cache/**", "**/.ruff_cache/**", "**/.mypy_cache/**",
            "**/backup/**", "**/build/**", "**/dist/**", "**/htmlcov/**",
            "**/logs/**", "**/out/**", "**/outputs/**", "**/sessions/**",
            "**/tmp/**", "**/updates/**", "**/*.pyc", "**/*.pyo",
            "**/.coverage", "**/.coverage.*", "**/*.log", "**/*.zip",
            "**/*_bundle_*.txt",
        ],
    },
    "python-env": {
        "label": "Python environments and caches",
        "deny": ["**/.venv/**", "**/venv/**", "**/env/**", "**/.tox/**",
                 "**/__pycache__/**", "**/*.pyc", "**/*.pyo",
                 "**/.pytest_cache/**", "**/.mypy_cache/**", "**/.ruff_cache/**",
                 "**/*.egg-info/**", "**/site-packages/**"],
    },
    "node": {
        "label": "Node modules and bundler output",
        "deny": ["**/node_modules/**", "**/.next/**", "**/.nuxt/**",
                 "**/dist/**", "**/build/**", "**/*.min.js", "**/*.map"],
    },
    "vcs": {
        "label": "Version control metadata",
        "deny": ["**/.git/**", "**/.svn/**", "**/.hg/**", "**/.gitmodules"],
    },
    "ide": {
        "label": "Editor and IDE state",
        "deny": ["**/.vscode/**", "**/.idea/**", "**/*.swp", "**/*.swo",
                 "**/.DS_Store", "**/Thumbs.db"],
    },
    "build-artifacts": {
        "label": "Compiled and packaged output",
        "deny": ["**/build/**", "**/dist/**", "**/target/**", "**/out/**",
                 "**/*.o", "**/*.obj", "**/*.so", "**/*.dll", "**/*.dylib",
                 "**/*.exe", "**/*.class"],
    },
    "media": {
        "label": "Images, audio and video",
        "deny": ["**/*.png", "**/*.jpg", "**/*.jpeg", "**/*.gif", "**/*.bmp",
                 "**/*.ico", "**/*.mp3", "**/*.mp4", "**/*.avi", "**/*.mov",
                 "**/*.pdf"],
    },
    "archives": {
        "label": "Archives and wheels",
        # Deliberately a preset and not Priority 0. Ringo's ruling of
        # 2026-08-25: an archive makes a bundle large, it does not break the
        # tool. This project must be able to bundle its own vendored wheel.
        "deny": ["**/*.zip", "**/*.tar", "**/*.tar.*", "**/*.7z", "**/*.rar",
                 "**/*.whl", "**/*.jar"],
    },
    "logs": {
        "label": "Logs and transient data",
        "deny": ["**/*.log", "**/logs/**", "**/*.tmp", "**/tmp/**",
                 "**/*.bak", "**/*.orig"],
    },
    "source-only": {
        "label": "Source files only (allow-list - narrows the bundle)",
        # An allow-list preset switches the base action to exclude. Selecting
        # this drops everything that does not match, by design.
        "allow": ["**/*.py", "**/*.js", "**/*.ts", "**/*.tsx", "**/*.jsx",
                  "**/*.java", "**/*.c", "**/*.h", "**/*.cpp", "**/*.hpp",
                  "**/*.cs", "**/*.go", "**/*.rs", "**/*.rb", "**/*.php",
                  "**/*.sh", "**/*.ps1", "**/*.sql"],
    },
    "docs": {
        "label": "Documentation and configuration only (allow-list)",
        "allow": ["**/*.md", "**/*.rst", "**/*.txt", "**/*.json", "**/*.toml",
                  "**/*.yaml", "**/*.yml", "**/*.ini", "**/*.cfg"],
    },
}


@dataclass
class RuleStack:
    """The assembled rules for one plan, plus the provenance to prove it."""

    rules: List[SelectionRule] = field(default_factory=list)
    groups: List[SelectionGroup] = field(default_factory=list)
    allow: List[str] = field(default_factory=list)
    allow_by_layer: Dict[Layer, List[str]] = field(default_factory=dict)
    digests: List[Tuple[str, str]] = field(default_factory=list)
    notices: List[str] = field(default_factory=list)
    presets_applied: List[str] = field(default_factory=list)

    def extend(self, rules: Sequence[SelectionRule]) -> None:
        self.rules.extend(rules)

    def add_allow(self, layer: Layer, pattern: str) -> None:
        """Record an allow pattern *and the layer that supplied it*.

        The layer matters because allow-lists are base-action switches, and
        only the highest-priority one may switch it. See `resolve_base_action`.
        """
        self.allow.append(pattern)
        self.allow_by_layer.setdefault(layer, []).append(pattern)

    def merge_allow(self, other: "RuleStack") -> None:
        for layer, patterns in other.allow_by_layer.items():
            self.allow_by_layer.setdefault(layer, []).extend(patterns)
        self.allow.extend(other.allow)


def resolve_base_action(allow_by_layer: Dict[Layer, List[str]]) -> Tuple[Action, List[str]]:
    """Which layer's allow-list decides the base action, and what it is.

    Defect found in Build 114 smoke testing, and worth recording because the
    naive version looks correct: taking `base_action_for()` over the *union* of
    every allow-list means the governed default `**/*` is always present, so
    `--include src/**` never narrows anything. The bundle silently keeps every
    file - exactly the failure the Build 113 correction was written to prevent,
    reappearing one level up at the composition layer.

    An allow-list is a statement about scope, and the most specific author
    wins. Layers are numerically ordered by priority, so the first layer with
    any allow-list decides and lower layers contribute ordinary rules only.
    """
    for layer in sorted(allow_by_layer, key=lambda item: item.value):
        patterns = [p for p in allow_by_layer[layer] if p]
        if not patterns:
            continue
        if all(p == "**/*" for p in patterns):
            return Action.INCLUDE, patterns
        return Action.EXCLUDE, patterns
    return Action.INCLUDE, []


def available_presets(config_presets: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
    """Shipped presets overlaid with anything the governed config defines."""
    merged = {name: dict(body) for name, body in SHIPPED_PRESETS.items()}
    for name, body in (config_presets or {}).items():
        if not isinstance(body, dict):
            raise RuleSourceError(
                f"Configured preset '{name}' must be an object with "
                f"'allow' and/or 'deny' lists, got {type(body).__name__}.")
        merged[name] = dict(body)
    return merged


def preset_rules(names: Sequence[str],
                 config_presets: Optional[Dict[str, Any]] = None,
                 layer: Layer = Layer.SHIPPED) -> RuleStack:
    """Translate named presets into Layer 4 rules.

    An unknown name is an error listing the valid ones. A typo that silently
    applied nothing would leave the operator believing a filter was active.
    """
    catalogue = available_presets(config_presets)
    stack = RuleStack()
    order = 0
    for name in names:
        body = catalogue.get(name)
        if body is None:
            known = ", ".join(sorted(catalogue))
            raise RuleSourceError(
                f"Unknown preset '{name}'. Available presets: {known}")
        for pattern in body.get("allow", ()):
            stack.add_allow(layer, pattern)
            stack.rules.append(SelectionRule(
                id=f"preset:{name}:allow:{pattern}", action=Action.INCLUDE,
                pattern=pattern, layer=layer, order=order,
                label=name, source=f"preset:{name}"))
            order += 1
        for pattern in body.get("deny", ()):
            stack.rules.append(SelectionRule(
                id=f"preset:{name}:deny:{pattern}", action=Action.EXCLUDE,
                pattern=pattern, layer=layer, order=order,
                label=name, source=f"preset:{name}"))
            order += 1
        stack.presets_applied.append(name)
        stack.digests.append((f"preset:{name}", rule_source_digest(body)))
    return stack


# ---------------------------------------------------------------------------
# Project rules files (Layer 2a)
# ---------------------------------------------------------------------------

def load_rules_file(path: Path,
                    layer: Layer = Layer.PROJECT_RULES) -> RuleStack:
    """Read a project rules file into Layer 2a rules and groups.

    Format (Paul's formal JSON Schema is pending as Revision 1.1; this loader
    accepts the shape the specification describes and reports precisely which
    element it rejected, so a schema can be bolted on without changing it):

        {
          "version": 1,
          "presets": ["python-env"],
          "allow":   ["src/**"],
          "deny":    ["**/*.log"],
          "rules":   [{"action": "exclude", "pattern": "docs/**",
                       "label": "drafts", "group": "docs"}],
          "groups":  [{"id": "docs", "order": 1, "patterns": ["**/*.md"]}]
        }
    """
    path = Path(path)
    if not path.is_file():
        raise RuleSourceError(f"Rules file not found: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise RuleSourceError(
            f"Rules file {path} is not valid JSON: line {error.lineno} "
            f"column {error.colno}: {error.msg}") from error
    if not isinstance(raw, dict):
        raise RuleSourceError(
            f"Rules file {path} must contain a JSON object, "
            f"found {type(raw).__name__}.")

    version = raw.get("version", 1)
    if version != 1:
        raise RuleSourceError(
            f"Rules file {path} declares version {version}; "
            f"this build understands version 1.")

    stack = RuleStack()
    label = f"rules:{path.name}"
    order = 0

    for pattern in _string_list(raw, "allow", path):
        stack.add_allow(layer, pattern)
        stack.rules.append(SelectionRule(
            id=f"{label}:allow:{pattern}", action=Action.INCLUDE,
            pattern=pattern, layer=layer, order=order,
            label=path.name, source=label))
        order += 1

    for pattern in _string_list(raw, "deny", path):
        stack.rules.append(SelectionRule(
            id=f"{label}:deny:{pattern}", action=Action.EXCLUDE,
            pattern=pattern, layer=layer, order=order,
            label=path.name, source=label))
        order += 1

    for index, entry in enumerate(raw.get("rules", []) or []):
        if not isinstance(entry, dict):
            raise RuleSourceError(
                f"Rules file {path}: rules[{index}] must be an object.")
        pattern = entry.get("pattern")
        if not isinstance(pattern, str) or not pattern:
            raise RuleSourceError(
                f"Rules file {path}: rules[{index}] needs a non-empty "
                f"'pattern' string.")
        action_name = str(entry.get("action", "exclude")).lower()
        try:
            action = Action(action_name)
        except ValueError:
            valid = ", ".join(a.value for a in Action)
            raise RuleSourceError(
                f"Rules file {path}: rules[{index}] action '{action_name}' "
                f"is not one of: {valid}") from None
        if action is Action.BLOCK:
            # Priority 0 is the tool's, not the project's. A rules file that
            # could mint blocks would be able to make its own decisions
            # non-overridable by the operator running the tool.
            raise RuleSourceError(
                f"Rules file {path}: rules[{index}] may not use action "
                f"'block'. Priority 0 is reserved for tool safety; use "
                f"'exclude', which the operator can still override.")
        if action is Action.INCLUDE:
            stack.add_allow(layer, pattern)
        stack.rules.append(SelectionRule(
            id=entry.get("id") or f"{label}:rule{index}",
            action=action, pattern=pattern, layer=layer, order=order,
            label=entry.get("label", "") or path.name,
            group=entry.get("group", "") or "",
            enabled=bool(entry.get("enabled", True)), source=label))
        order += 1

    for index, entry in enumerate(raw.get("groups", []) or []):
        if not isinstance(entry, dict) or not entry.get("id"):
            raise RuleSourceError(
                f"Rules file {path}: groups[{index}] needs an 'id'.")
        stack.groups.append(SelectionGroup(
            id=str(entry["id"]), label=str(entry.get("label", "") or ""),
            order=int(entry.get("order", index)),
            patterns=tuple(_string_list(entry, "patterns", path))))

    stack.digests.append((label, rule_source_digest(raw)))
    nested = [n for n in raw.get("presets", []) or []]
    if nested:
        stack.notices.append(
            f"{path.name} requests presets: {', '.join(nested)}")
    return stack


def _string_list(payload: Dict[str, Any], key: str, path: Path) -> List[str]:
    value = payload.get(key, []) or []
    if isinstance(value, str):
        return [value]
    if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
        raise RuleSourceError(
            f"Rules file {path}: '{key}' must be a list of strings.")
    return list(value)


# ---------------------------------------------------------------------------
# CLI (Layer 2b) and session overrides (Layer 1)
# ---------------------------------------------------------------------------

def expand_bare_pattern(pattern: str) -> str:
    """`*.py` means "Python files anywhere", as it always has.

    The selection engine uses strict glob semantics, where `*` does not cross a
    separator, so `*.py` matches only the top level. The command line has never
    behaved that way: the Build 113 discovery filter matched `*.py` at any
    depth, and so do gitignore, rsync and every tool an operator has muscle
    memory for.

    Routing `--include` through the ladder without this would have silently
    stopped `--include '*.py'` from matching `src/app.py` - a narrowing with no
    error and no message, in a build whose entire purpose is that selections
    stop changing behind your back. A pattern that names no directory is
    therefore anchored at any depth; one that contains a separator is already
    explicit about position and is left exactly as written.
    """
    if "/" in pattern or pattern.startswith("**"):
        return pattern
    return f"**/{pattern}"


def cli_rules(include: Sequence[str] = (),
              exclude: Sequence[str] = ()) -> RuleStack:
    """`--include` / `--exclude` as Layer 2b rules.

    `--include` also contributes to the allow-list, which the caller feeds to
    `base_action_for()`. That is the correction carried from Build 113: an
    allow-list is a base-action switch, so `--include src/**` drops everything
    else instead of merely adding a rule that nothing else consults.

    `--exclude` is *additive* to the governed defaults, per Paul's ruling. It
    used to replace them, which meant `--exclude '*.log'` quietly re-admitted
    `.git`, `node_modules` and every other default. Callers should surface
    `notices` so the change in meaning is visible, not inferred.
    """
    stack = RuleStack()
    order = 0
    for raw in include:
        pattern = expand_bare_pattern(raw)
        stack.add_allow(Layer.CLI_RULES, pattern)
        stack.rules.append(SelectionRule(
            id=f"cli:include:{raw}", action=Action.INCLUDE,
            pattern=pattern, layer=Layer.CLI_RULES, order=order,
            label=raw, source="cli"))
        order += 1
    for raw in exclude:
        pattern = expand_bare_pattern(raw)
        stack.rules.append(SelectionRule(
            id=f"cli:exclude:{raw}", action=Action.EXCLUDE,
            pattern=pattern, layer=Layer.CLI_RULES, order=order,
            label=raw, source="cli"))
        order += 1
    if exclude:
        stack.notices.append(
            "--exclude now adds to the default rules instead of replacing "
            "them. Pass --no-default-rules for the previous behaviour.")
    if include:
        stack.notices.append(
            "--include is an allow-list: files matching no --include pattern "
            "are excluded.")
    return stack


def session_rules(force_include: Sequence[str] = (),
                  force_exclude: Sequence[str] = (),
                  overrides: Sequence[Tuple[str, str]] = ()) -> RuleStack:
    """Layer 1 overrides, in the order the operator made them.

    Layer 1 outranks everything except Priority 0. A force-include carries a
    wheel through the archives preset; it cannot carry a nested bundle through
    a recursion block, and the decision records that it tried.

    **Order within the layer is the operator's action order**, which is why
    `overrides` exists alongside the two flag lists. Layer 1 is last-match-wins,
    so building it as "every include, then every exclude" made exclusion win
    every conflict regardless of what the operator did last: uncheck `docs`,
    then re-check `docs/sub`, and the second action silently did nothing. In the
    tri-state tree of WP4 that reads as a broken checkbox, which is why the
    workspace records an ordered sequence rather than two sets.

    Args:
        force_include: `--force-include` patterns, in command-line order.
        force_exclude: `--force-exclude` patterns, applied after them.
        overrides: ordered `(action, pattern)` pairs - what the desktop
            workspace appends as the operator clicks. Applied last, in order,
            so the most recent action wins.

    Raises:
        RuleSourceError: on an unknown action, or on an attempt to mint a
            Priority 0 block from a session override.
    """
    stack = RuleStack()
    sequence: List[Tuple[str, str]] = [(Action.INCLUDE.value, p) for p in force_include]
    sequence += [(Action.EXCLUDE.value, p) for p in force_exclude]
    sequence += [(str(action), pattern) for action, pattern in overrides]

    for order, (action_name, pattern) in enumerate(sequence):
        try:
            action = Action(action_name)
        except ValueError:
            raise RuleSourceError(
                f"Session override action '{action_name}' is not one of: "
                f"{', '.join(a.value for a in Action)}") from None
        if action is Action.BLOCK:
            raise RuleSourceError(
                "A session override may not use action 'block'. Priority 0 is "
                "reserved for tool safety and is never operator-minted.")
        verb = "force-include" if action is Action.INCLUDE else "force-exclude"
        stack.rules.append(SelectionRule(
            id=f"session:{verb}:{pattern}", action=action,
            pattern=pattern, layer=Layer.SESSION, order=order,
            label=f"{verb} {pattern}", source="session"))
    return stack


def parse_group_specs(specs: Sequence[str]) -> List[SelectionGroup]:
    """`--group NAME=pattern[,pattern...]` into ordered groups.

    Groups affect emission order only. They never change inclusion, so a
    malformed group is an error rather than a silent no-op that would appear
    to work while ordering nothing.
    """
    groups: List[SelectionGroup] = []
    for index, spec in enumerate(specs):
        if "=" not in spec:
            raise RuleSourceError(
                f"Group '{spec}' must be NAME=pattern[,pattern...]")
        name, _, patterns = spec.partition("=")
        name = name.strip()
        parts = tuple(p.strip() for p in patterns.split(",") if p.strip())
        if not name or not parts:
            raise RuleSourceError(
                f"Group '{spec}' needs a name and at least one pattern.")
        groups.append(SelectionGroup(id=name, label=name, order=index,
                                     patterns=parts))
    return groups
