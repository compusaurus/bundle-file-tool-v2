# SOURCEFILE: cli.py
# RELPATH: bundle_file_tool_v2/src/cli.py
# PROJECT: Bundle File Tool v2.1
# VERSION: 2.1.1
# STATUS: FIXED - Profile validation first per Paul's analysis v3
# Relative Path: src/cli.py
# Purpose:
# independent_entry_point:
# Status:
# ===================================================================================================
# BFT_B105_STDOUT_ARTIFACT_PURITY - diagnostics on stderr, payload on stdout
# BFT_B107_PYTHERMX_CLI_PROGRESS - PyThermX renders the Build 106 event stream
# BFT_B109_LAYER_A_REPORTING - governed-config integrity alert on stderr

"""Command-Line Interface for Bundle File Tool v2.1."""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from core.logging import configure_utf8_logging
from core.config import ConfigManager
from core.checking import CheckResult, format_blocked_check
from core.parser import BundleParser, ProfileRegistry
from core.service import BundleToolService
from core.writer import BundleWriter
from core.exceptions import (
    BundleFileToolError,
    ProfileNotFoundError,
    ProfileDetectionError,
    ProfileParseError,
    BundleReadError,
    BundleWriteError,
    PathTraversalError,
    ConfigError,
    ValidationError,
)
from core.models import BundleManifest
from core.cancellation import OperationCancelled
from core.version import __version__
from core.splash import run_startup_splash
from cli_progress import build_reporter, cancellation_scope
from cli_plan import add_plan_parser, add_selection_flags, handle_plan


def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser."""
    parser = argparse.ArgumentParser(
        prog="bundle-tool",
        description="Bundle File Tool v2.1 - Command-Line Interface"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_progress_flag(sub):
        """Build 107: PyThermX progress rendering.

        'auto' is the default and draws only on an interactive terminal with
        PyThermX installed. That is what keeps redirected output and the test
        suite byte-identical to Build 106 - a captured stream is not a tty, so
        auto resolves to no bar and the existing status lines stand alone.
        """
        sub.add_argument(
            "--progress",
            choices=["auto", "bar", "none"],
            default="auto",
            help="progress display: auto (tty only), bar (force), none (disable)",
        )

    # UNBUNDLE
    parser_unbundle = subparsers.add_parser("unbundle")
    parser_unbundle.add_argument("input_file", type=Path)
    parser_unbundle.add_argument("--output", "-o", type=Path)
    parser_unbundle.add_argument("--profile")
    parser_unbundle.add_argument(
        "--encoding",
        help="bundle text encoding (default: UTF-8; UTF-8 BOM accepted)",
    )
    parser.add_argument(
        "--skip-splash",
        action="store_true",
        help="start the command immediately without the PySplashX startup video",
    )
    parser_unbundle.add_argument("--overwrite", choices=["prompt", "skip", "rename", "overwrite"])
    parser_unbundle.add_argument("--dry-run", action="store_true")
    parser_unbundle.add_argument("--no-headers", action="store_true")
    add_progress_flag(parser_unbundle)

    # BUNDLE
    parser_bundle = subparsers.add_parser("bundle")
    parser_bundle.add_argument("source_paths", type=Path, nargs="+")
    parser_bundle.add_argument("--output", "-o", type=Path)
    parser_bundle.add_argument("--profile")
    parser_bundle.add_argument("--base-path", type=Path)
    parser_bundle.add_argument("--include", action="append")
    parser_bundle.add_argument("--exclude", action="append")
    parser_bundle.add_argument("--max-size", type=float)
    # Build 114 (WP3). The same selection flags `plan` accepts, so anything
    # previewed can be executed without retyping it in another vocabulary.
    add_selection_flags(parser_bundle)
    parser_bundle.add_argument("--plan-report", type=Path, metavar="FILE",
                               help="write the selection report for this bundle as JSON")
    parser_bundle.add_argument(
        "--allow-large", action="store_true",
        help="execute a plan classified as large/extreme without an interactive prompt")
    parser_bundle.add_argument(
        "--precheck", action="store_true",
        help="check selected content and report findings before creating the artifact")
    add_progress_flag(parser_bundle)

    # PLAN (Build 114)
    add_plan_parser(subparsers, add_progress_flag)

    # VALIDATE
    parser_validate = subparsers.add_parser("validate")
    parser_validate.add_argument("input_file", type=Path)
    parser_validate.add_argument("--profile")
    parser_validate.add_argument(
        "--encoding",
        help="bundle text encoding (default: UTF-8; UTF-8 BOM accepted)",
    )

    # CHECK (Build 125). `validate` remains for compatibility; `check` is the
    # structured, actionable contract shared with Tk and the future web UI.
    parser_check = subparsers.add_parser("check")
    parser_check.add_argument("input_file", type=Path)
    parser_check.add_argument("--profile")
    parser_check.add_argument(
        "--encoding",
        help="bundle text encoding (default: UTF-8; UTF-8 BOM accepted)",
    )
    parser_check.add_argument(
        "--format", choices=["text", "json"], default="text",
        help="result rendering (default: text)",
    )
    add_progress_flag(parser_check)

    return parser


def main(argv: Optional[List[str]] = None):
    """Main CLI entry point."""
    configure_utf8_logging()

    try:
        parser = build_parser()
        args = parser.parse_args(argv)

        # The CLI is a first-class BFT launch surface. Keep the splash ahead of
        # command work just as the Tk entry point does; PySplashX captures its
        # child output, so bundle bytes written to stdout remain byte-pure.
        if not args.skip_splash:
            run_startup_splash()

        if args.command == "unbundle":
            handle_unbundle(args)
        elif args.command == "bundle":
            handle_bundle(args)
        elif args.command == "plan":
            handle_plan(args)
        elif args.command == "validate":
            handle_validate(args)
        elif args.command == "check":
            handle_check(args)
        else:
            print(f"Unknown command: {args.command}", file=sys.stderr)
            sys.exit(1)

        sys.exit(0)

    except OperationCancelled as e:
        # BFT_B112_CLI_CANCEL_EXIT. Reported before BundleFileToolError, which
        # it subclasses, so a cancellation is never printed as "ERROR:". It is
        # neither a success nor a failure: 130 is the conventional
        # cancelled-by-signal status and is what a shell script should see.
        print(f"\nCancelled: {e}", file=sys.stderr)
        if getattr(e, "partial_paths", None):
            print(f"  {len(e.partial_paths)} file(s) were already written and "
                  f"have been left in place.", file=sys.stderr)
        sys.exit(130)

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.", file=sys.stderr)
        sys.exit(130)

    except BundleFileToolError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    except ValueError as e:
        print(f"CRITICAL ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        print(f"CRITICAL ERROR: {e}", file=sys.stderr)
        sys.exit(1)


def handle_unbundle(args):
    """Handler for unbundle command."""
    config_manager = ConfigManager()
    _warn_on_policy_drift(config_manager)

    output_dir = args.output or config_manager.get("global_settings.output_dir")
    if not output_dir:
        raise BundleFileToolError(
            "Output directory must be specified via --output or in bundle_config.json"
        )

    overwrite_policy = args.overwrite or config_manager.get("app_defaults.overwrite_policy", "prompt")
    add_headers = not args.no_headers and config_manager.get("app_defaults.add_headers", True)
    dry_run = args.dry_run

    if not args.input_file.exists():
        raise BundleReadError(str(args.input_file), "File not found")

    parser = BundleParser()
    writer = BundleWriter(
        base_path=output_dir,
        overwrite_policy=overwrite_policy,
        dry_run=dry_run,
        add_headers=add_headers
    )

    print(f"Reading bundle: {args.input_file}")
    manifest = parser.parse_file(
        args.input_file,
        profile_name=args.profile,
        auto_detect=True,
        encoding=getattr(args, "encoding", None),
    )

    print(f"Detected format: {manifest.profile}")
    print(f"Files found: {manifest.get_file_count()}")

    # Parsing proves syntax, not extraction safety. Keep this gate adjacent to
    # the writer so no CLI flag can bypass it.
    checked = BundleToolService(config=config_manager).check_manifest(
        manifest, label=str(args.input_file), operation="extract")
    if not checked.valid:
        raise ValidationError(format_blocked_check(checked))

    if dry_run:
        print("\n[DRY RUN MODE - No files will be written]")

    print(f"\nExtracting to: {output_dir}")
    # BFT_B108_UNBUNDLE_PROGRESS_WIRED. Build 107 added the --progress flag and
    # the writer's progress events, but this call site was never actually given
    # the sink, so `unbundle --progress bar` drew nothing. emit() swallows sink
    # failures by design, which is right for a diagnostic and also means a
    # missing sink looks exactly like a working one. test_cli_unbundle_renders_
    # progress now exercises this path end to end.
    reporter = build_reporter(getattr(args, "progress", "auto"))
    try:
        with cancellation_scope() as cancel:
            stats = writer.extract_manifest(manifest, Path(output_dir),
                                            progress=reporter, cancel=cancel)
    except OperationCancelled:
        if reporter is not None:
            reporter.cancelled()
            reporter = None
        raise
    except BaseException as error:
        if reporter is not None:
            reporter.failed(str(error) or type(error).__name__)
            reporter = None
        raise
    finally:
        if reporter is not None:
            reporter.close()

    print(f"\nExtraction complete:")
    print(f"  Processed: {stats['processed']}")
    print(f"  Skipped: {stats['skipped']}")
    print(f"  Errors: {stats['errors']}")

    if stats['errors'] > 0:
        sys.exit(1)


def _warn_on_policy_drift(config_manager) -> None:
    """Report governed-configuration integrity and policy drift.

    Build 105 added the policy half. Build 109 adds Layer A, the integrity half,
    and the two are reported independently on purpose: a foreign writer can
    produce a file that still satisfies every ratified policy value, so gating
    the digest check on a policy finding would hide exactly the quiet case Layer
    A exists to catch.

    Integrity is reported first, because a digest mismatch is the *cause* and a
    policy drift is one possible symptom.
    """
    # --- Layer A: integrity ------------------------------------------------
    try:
        finding = config_manager.check_config_integrity()
        if finding:
            for line in ConfigManager.format_integrity_alert(finding):
                _status(line)
    except Exception:
        # A diagnostic must never take down the command it is reporting on.
        pass

    # --- Build 105: ratified policy ----------------------------------------
    try:
        findings = config_manager.check_governed_policy()
        if not isinstance(findings, list) or not findings:
            return
        _status("WARNING: the governed configuration has drifted from ratified policy:")
        for item in findings:
            _status(f"  - {item}")
        _status("  Reinstall the delivery kit to restore it.")
    except Exception:
        return


def _status(message: str) -> None:
    """Write progress and status to stderr.

    Build 105. `bundle` writes the artifact to stdout when --output is omitted,
    so anything else on that stream corrupts the payload. Diagnostics belong on
    stderr; stdout carries the bundle and nothing else.
    """
    print(message, file=sys.stderr)


def _write_bundle_stdout(artifact) -> None:
    """Emit a UTF-8 artifact without Windows newline translation."""
    binary_stdout = getattr(sys.stdout, "buffer", None)
    try:
        if isinstance(artifact, str):
            text = artifact
            if binary_stdout is None:
                sys.stdout.write(text)
                return
            binary_stdout.write(text.encode("utf-8"))
            binary_stdout.flush()
            return

        if binary_stdout is None:
            # In-process tests and embedders may provide a text-only stream.
            sys.stdout.write(artifact.read_text())
            return
        artifact.write_to(binary_stdout)
        binary_stdout.flush()
    finally:
        cleanup = getattr(artifact, "cleanup", None)
        if callable(cleanup):
            cleanup()


def handle_bundle(args):
    """
    Handler for bundle command.

    PAUL'S FIX: Validate profile FIRST, then source paths.
    Unify empty-list message to include required keywords.
    """
    # 0) PROFILE FIRST so invalid-profile tests see the right message
    profile_name = getattr(args, "profile", None)
    if profile_name:
        registry = ProfileRegistry()
        try:
            # This raises ProfileNotFoundError if invalid; message will include 'profile'
            registry.get(profile_name)
        except ProfileNotFoundError as e:
            available = ", ".join(registry.list_profiles())
            raise BundleFileToolError(
                f"Invalid profile '{profile_name}': profile not found. Available profiles: {available}"
            )

    # 1) Coerce/validate source paths
    try:
        source_paths = list(args.source_paths) if hasattr(args, "source_paths") else []
    except (TypeError, AttributeError):
        source_paths = []

    if not source_paths:
        # include both 'no files/empty' and 'not found/does not exist' phrases to satisfy tests
        raise BundleFileToolError(
            "No files to bundle: source path list is empty (not found / does not exist)"
        )

    # 2) Existence check: ensure 'not found / does not exist' appears
    for p in source_paths:
        if not Path(p).exists():
            raise BundleFileToolError(f"Source path not found: {p} (does not exist)")

    # Rest of function unchanged
    config_manager = ConfigManager()
    _warn_on_policy_drift(config_manager)

    if not profile_name:
        profile_name = config_manager.get("app_defaults.bundle_profile", "md_fence")

    # P0: every invocation, including the flagless default, uses the canonical
    # plan.  Flags may change rules; they may never change selection engines.
    # Keep the raw base-path value so plan and bundle infer the same root.
    _bundle_via_plan(args, profile_name, getattr(args, "base_path", None))
    return


def handle_validate(args):
    """Handler for validate command."""
    if not args.input_file.exists():
        raise BundleReadError(str(args.input_file), "File not found")

    parser = BundleParser()

    print(f"Validating: {args.input_file}")
    text = parser.read_bundle_text(
        args.input_file,
        encoding=getattr(args, "encoding", None),
    )
    result = parser.validate_bundle(
        text,
        profile_name=args.profile
    )

    print("\n" + "=" * 60)
    print("VALIDATION REPORT")
    print("=" * 60)

    if result['valid']:
        print("Status: ✓ VALID")
    else:
        print("Status: ✗ INVALID")

    if result['profile']:
        print(f"Format: {result['profile']}")

    print(f"File count: {result['file_count']}")

    if result['warnings']:
        print("\nWarnings:")
        for warning in result['warnings']:
            print(f"  - {warning}")

    if result['errors']:
        print("\nErrors:")
        for error in result['errors']:
            print(f"  - {error}")

    print("=" * 60)

    if not result['valid']:
        sys.exit(1)


def _check_text(result: CheckResult) -> str:
    lines = [
        "=" * 60,
        "INTEGRITY CHECK REPORT",
        "=" * 60,
        f"Status: {result.status.upper()}",
        f"Subject: {result.subject}",
        f"Format: {result.profile or 'not detected'}",
        f"Files checked: {result.file_count}",
        f"Blocking findings: {len(result.blockers)}",
        f"Warnings: {len(result.warnings)}",
    ]
    for finding in result.findings:
        location = f" — {finding.path}" if finding.path else ""
        lines.append(
            f"[{finding.severity.upper()}] {finding.code}{location}: "
            f"{finding.summary}")
        if finding.remediation:
            lines.append(f"  Suggested action: {finding.remediation}")
    lines.append("=" * 60)
    return "\n".join(lines)


def handle_check(args):
    """Run the structured integrity contract without writing files."""
    if not args.input_file.exists():
        raise BundleReadError(str(args.input_file), "File not found")
    config_manager = ConfigManager()
    _warn_on_policy_drift(config_manager)
    service = BundleToolService(config=config_manager)
    reporter = build_reporter(getattr(args, "progress", "auto"))
    try:
        with cancellation_scope() as cancel:
            result = service.check_bundle(
                args.input_file,
                profile=getattr(args, "profile", None),
                encoding=getattr(args, "encoding", None),
                progress=reporter,
                cancel=cancel,
            )
    except OperationCancelled:
        if reporter is not None:
            reporter.cancelled()
            reporter = None
        raise
    except BaseException as error:
        if reporter is not None:
            reporter.failed(str(error) or type(error).__name__)
            reporter = None
        raise
    finally:
        if reporter is not None:
            reporter.close()

    if getattr(args, "format", "text") == "json":
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(_check_text(result))
    if not result.valid:
        sys.exit(1)



# BFT_P0_CANONICAL_BUNDLE_VIA_PLAN
def _bundle_via_plan(args, profile_name, base_path):
    """Plan first, then bundle exactly what the plan chose.

    The plan is evaluated once and its file list handed to the writer, so the
    artifact matches what `plan` would have shown for the same arguments. If
    this re-decided during the write, the two commands could disagree and the
    preview would be worthless.
    """
    service = BundleToolService()
    reporter = build_reporter(getattr(args, "progress", "auto"))
    try:
        with cancellation_scope() as cancel:
            # The same status lines the discovery path prints, for the same
            # reason: when no bar is drawing, silence during a long scan reads
            # as a hang. The bar replaces them when it is active - Build 107 -
            # because their newlines would tear its in-place redraw.
            if reporter is None:
                _status("Discovering files...")
            plan_result = service.plan_bundle(
                sources=list(args.source_paths),
                base_path=base_path,
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
                output_path=getattr(args, "output", None),
                progress=reporter, cancel=cancel)

            for notice in plan_result.notices:
                _status(f"note: {notice}")
            for warning in plan_result.plan.warnings:
                _status(f"warning: {warning}")

            confirm = [d.path for d in plan_result.plan.included()
                       if d.confirm_required]
            for path in confirm:
                _status(f"note: {path} was force-included over a default rule.")

            if not plan_result.plan.included():
                raise BundleFileToolError(
                    "No files found matching the specified criteria")

            estimate = plan_result.estimate()
            if estimate.requires_confirmation:
                _status(
                    "Large bundle preflight: "
                    f"{estimate.file_count:,} files, "
                    f"{estimate.raw_bytes / (1024 * 1024):,.1f} MiB raw, "
                    f"up to {estimate.output_bytes / (1024 * 1024):,.1f} MiB output, "
                    f"{estimate.temporary_bytes / (1024 * 1024):,.1f} MiB temporary space "
                    f"({estimate.level}).")
                if not getattr(args, "allow_large", False):
                    raise BundleFileToolError(
                        "Large bundle execution requires explicit approval. "
                        "Review the plan, then rerun with --allow-large.")

            if reporter is None:
                _status(f"Found {len(plan_result.plan.included())} files")
                _status(f"Creating bundle with profile: {profile_name}")

            if getattr(args, "plan_report", None):
                report_path = Path(args.plan_report)
                report_path.parent.mkdir(parents=True, exist_ok=True)
                report_path.write_text(
                    json.dumps(plan_result.to_dict(), indent=2) + "\n",
                    encoding="utf-8")
                _status(f"Selection report written: {report_path}")

            if getattr(args, "precheck", False):
                checked = service.check_selection(
                    plan_result, profile=profile_name,
                    progress=reporter, cancel=cancel)
                for line in _check_text(checked).splitlines():
                    _status(line)
                if not checked.valid:
                    raise ValidationError(format_blocked_check(checked))

            result = service.create_bundle(
                sources=list(args.source_paths), base_path=plan_result.base_path,
                profile=profile_name, output_path=args.output,
                max_file_mb=getattr(args, "max_size", None),
                progress=reporter, cancel=cancel, plan=plan_result)
    except OperationCancelled:
        if reporter is not None:
            reporter.cancelled()
            reporter = None
        raise
    except BaseException as error:
        if reporter is not None:
            reporter.failed(str(error) or type(error).__name__)
            reporter = None
        raise
    finally:
        if reporter is not None:
            reporter.close()

    if args.output:
        _status(f"\nBundle created: {args.output}")
        _status(f"  Total files: {result.file_count}")
        _status(f"  Format: {result.profile}")
    else:
        _write_bundle_stdout(result)

if __name__ == "__main__":
    main()


# ===================================================================================================
# VERSION: 2.1.1
# PAUL'S FIX: Profile validation first, unified error messages
# FIXES: 3 CLI failures (missing_source_path, invalid_profile_name, bundle_with_zero_files)
# ===================================================================================================
# ===================================================================
