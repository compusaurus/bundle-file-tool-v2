# BFT_B114_CLI_PLAN - the `plan` command, and the selection flags
# ===================================================================================================
# SOURCEFILE: cli_plan.py
# RELPATH: bundle_file_tool_v2/src/cli_plan.py
# PROJECT: Bundle File Tool v2.2
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.114
# LIFECYCLE: Testing
# STATUS: Build 114 - WP3 - BFT_B114_CLI_PLAN
# DESCRIPTION: CLI adapter over BundleToolService.plan_bundle - renders plans,
#              explanations and reports. Owns no selection logic.
# Relative Path: src/cli_plan.py
# Purpose:
# independent_entry_point:
# ===================================================================================================
"""Show the decision before making it.

This module renders; it decides nothing. Every question about what is included
is answered by `BundleToolService.plan_bundle`, and this file turns the answer
into text. That split is the D-002 rule, and it is what will let the WP4
desktop workspace show the identical tree without reimplementing a single rule.

**Stdout purity**, per Paul's S-10 three-way ruling:

===========================  ================================================
`plan`                       *may* write to stdout - the plan is its artifact
`bundle` without `--output`  bundle text only; nothing else on stdout
`bundle` with `--output`     stdout stays empty; the file is the artifact
===========================  ================================================

Notices, warnings and progress go to stderr in every case, so `bundle-tool plan
--list | xargs ...` is safe and so is redirecting a bundle.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.exceptions import BundleFileToolError
from core.cancellation import OperationCancelled
from core.selection import State
from core.service import BundleToolService
from cli_progress import build_reporter, cancellation_scope


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def add_selection_flags(sub) -> None:
    """The selection flags shared by `plan` and `bundle`.

    Shared deliberately: if `plan` accepted a flag `bundle` did not, the
    previewed selection could not be executed, and the preview would be a
    demonstration rather than a contract.
    """
    sub.add_argument("--preset", action="append", metavar="NAME",
                     help="apply a named preset (repeatable); --list-presets to see them")
    sub.add_argument("--rules", type=Path, metavar="FILE",
                     help="project rules file (JSON) evaluated at priority 2a")
    sub.add_argument("--force-include", action="append", metavar="GLOB",
                     help="priority 1 override: include even if a rule excludes it")
    sub.add_argument("--force-exclude", action="append", metavar="GLOB",
                     help="priority 1 override: exclude regardless of other rules")
    sub.add_argument("--group", action="append", metavar="NAME=GLOB[,GLOB]",
                     help="emit matching files together (affects order only)")
    sub.add_argument("--include-root", action="append", metavar="DIR",
                     help="descend into a directory that detectors would prune")
    sub.add_argument("--no-default-rules", action="store_true",
                     help="ignore the governed deny list (priority 0 still applies)")


def add_plan_parser(subparsers, add_progress_flag) -> None:
    """Register `bundle-tool plan`."""
    parser = subparsers.add_parser(
        "plan",
        help="show what would be bundled, and why, without reading any file")
    parser.add_argument("source_paths", type=Path, nargs="*")
    parser.add_argument("--base-path", type=Path)
    parser.add_argument("--include", action="append", metavar="GLOB",
                        help="allow-list: files matching no --include are excluded")
    parser.add_argument("--exclude", action="append", metavar="GLOB",
                        help="add an exclusion to the default rules")
    parser.add_argument("--max-size", type=float, metavar="MB",
                        help="mark files larger than MB as skipped in the plan")
    add_selection_flags(parser)
    parser.add_argument("--explain", nargs="?", const="", metavar="PATH",
                        help="show the rule chain for PATH, or for every path")
    parser.add_argument("--report", type=Path, metavar="FILE",
                        help="write the full selection report as JSON")
    parser.add_argument("--format", dest="fmt", choices=["text", "json"],
                        default="text", help="stdout format (default: text)")
    parser.add_argument("--list", action="store_true",
                        help="print included paths only, one per line")
    parser.add_argument("--limit", type=int, default=0, metavar="N",
                        help="show at most N paths (0 = all)")
    parser.add_argument("--list-presets", action="store_true",
                        help="list available presets and exit")
    add_progress_flag(parser)


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

def handle_plan(args) -> None:
    """Render a selection plan. Diagnostics to stderr, plan to stdout."""
    service = BundleToolService()

    if getattr(args, "list_presets", False):
        _render_presets(service, getattr(args, "fmt", "text"))
        return

    if not args.source_paths:
        raise BundleFileToolError(
            "No files to bundle: source path list is empty "
            "(not found / does not exist)")
    for candidate in args.source_paths:
        if not Path(candidate).exists():
            raise BundleFileToolError(
                f"Source path not found: {candidate} (does not exist)")

    result = _run_plan(service, args)

    for notice in result.notices:
        print(f"note: {notice}", file=sys.stderr)
    for warning in result.plan.warnings:
        print(f"warning: {warning}", file=sys.stderr)

    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(result.to_dict(), indent=2, sort_keys=False) + "\n",
            encoding="utf-8")
        print(f"Selection report written: {report_path}", file=sys.stderr)

    explain = getattr(args, "explain", None)
    if explain is not None:
        target = explain or None
        rendered = service.explain_selection(
            result, target, fmt="json" if args.fmt == "json" else "text")
        sys.stdout.write(
            json.dumps(rendered, indent=2) + "\n" if args.fmt == "json"
            else str(rendered) + "\n")
        return

    if args.list:
        # Script surface: paths only, nothing else, so it pipes cleanly.
        for path in _limited(result.plan.ordered_paths(), args.limit):
            sys.stdout.write(path + "\n")
        return

    preview = service.preview_bundle(result, limit=args.limit)
    if args.fmt == "json":
        sys.stdout.write(json.dumps(preview, indent=2) + "\n")
        return
    sys.stdout.write(_render_text(result, preview, args.limit))


def _run_plan(service: BundleToolService, args):
    """Plan with a progress bar and a cancellation scope, like any operation."""
    reporter = build_reporter(getattr(args, "progress", "auto"))
    try:
        with cancellation_scope() as cancel:
            return service.plan_bundle(
                sources=list(args.source_paths),
                base_path=getattr(args, "base_path", None),
                preset=getattr(args, "preset", None),
                rules=getattr(args, "rules", None),
                include=getattr(args, "include", None),
                exclude=getattr(args, "exclude", None),
                force_include=getattr(args, "force_include", None),
                force_exclude=getattr(args, "force_exclude", None),
                groups=getattr(args, "group", None),
                include_roots=getattr(args, "include_root", None),
                no_default_rules=getattr(args, "no_default_rules", False),
                max_file_mb=getattr(args, "max_size", None),
                progress=reporter,
                cancel=cancel,
            )
    except OperationCancelled:
        if reporter is not None:
            reporter.cancelled()
            reporter = None
        raise
    except BaseException as error:  # preserve the operation error
        if reporter is not None:
            reporter.failed(str(error) or type(error).__name__)
            reporter = None
        raise
    finally:
        if reporter is not None:
            reporter.close()


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def _limited(paths: List[str], limit: int) -> List[str]:
    return paths[:limit] if limit and limit > 0 else paths


def _render_presets(service: BundleToolService, fmt: str) -> None:
    catalogue = service.presets()
    if fmt == "json":
        sys.stdout.write(json.dumps(catalogue, indent=2, sort_keys=True) + "\n")
        return
    width = max((len(name) for name in catalogue), default=0)
    for name in sorted(catalogue):
        body = catalogue[name]
        kind = "allow-list" if body.get("allow") else "exclusions"
        count = len(body.get("allow") or body.get("deny") or ())
        label = body.get("label", "")
        sys.stdout.write(
            f"{name.ljust(width)}  {label}  ({count} {kind})\n")


def _render_text(result, preview: Dict[str, Any], limit: int) -> str:
    """The human view: the decision first, the file list second.

    Decision-first because Build 110 measured formatting a 4,000-entry listing
    at ~1.1 s. An operator deciding whether the selection is right should not
    wait on a list they may not need.
    """
    counts = preview["counts"]
    lines: List[str] = []
    lines.append(f"Plan for {result.base_path}")
    lines.append(f"  scanned        {result.scan.scanned} file(s)")
    lines.append(f"  included       {counts.get(State.INCLUDED.value, 0)}")
    lines.append(f"  excluded       {counts.get(State.EXCLUDED.value, 0)}")
    blocked = counts.get(State.BLOCKED.value, 0)
    if blocked:
        lines.append(f"  blocked        {blocked} (priority 0 - not overridable)")
    unknown = counts.get(State.UNKNOWN.value, 0)
    if unknown:
        lines.append(f"  unknown        {unknown}")
    lines.append(f"  base action    {preview['base_action']}")
    if preview["presets_applied"]:
        lines.append(f"  presets        {', '.join(preview['presets_applied'])}")
    lines.append(f"  estimated      {_human_bytes(preview['estimated_bytes'])}")
    capacity = preview.get("capacity_estimate", {})
    if capacity:
        lines.append(
            f"  output upper   {_human_bytes(capacity['output_bytes'])}")
        lines.append(
            f"  temporary      {_human_bytes(capacity['temporary_bytes'])}")
        if capacity.get("requires_confirmation"):
            lines.append(
                f"  preflight      {capacity['level']} - explicit approval required")
    lines.append(f"  rule digest    {preview['rule_stack_digest'][:16]}")

    if preview["pruned_roots"]:
        lines.append("")
        lines.append(f"  Pruned before descent ({len(preview['pruned_roots'])}):")
        for row in result.scan.ledger.to_report():
            if row["result"] != "detected":
                continue
            lines.append(f"    {row['path']}  [{row['family']}] {row['code']}")

    ambiguous = result.scan.ledger.ambiguous
    if ambiguous:
        lines.append("")
        lines.append(f"  Ambiguous, traversed and kept ({len(ambiguous)}):")
        for path in sorted(ambiguous):
            lines.append(f"    {path}  {ambiguous[path].code}")

    if preview["confirm_required"]:
        lines.append("")
        lines.append("  Overrides that would normally be confirmed:")
        for path in preview["confirm_required"]:
            lines.append(f"    {path}")

    paths = preview["paths"]
    lines.append("")
    lines.append(f"  Files to bundle ({counts.get(State.INCLUDED.value, 0)}):")
    for path in paths:
        lines.append(f"    {path}")
    if preview["truncated"]:
        remaining = counts.get(State.INCLUDED.value, 0) - len(paths)
        lines.append(f"    ... {remaining} more (--limit 0 to show all)")
    lines.append("")
    return "\n".join(lines)


def _human_bytes(count: int) -> str:
    size = float(count)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"
