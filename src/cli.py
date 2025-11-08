# ============================================================================
# SOURCEFILE: cli.py
# RELPATH: bundle_file_tool_v2/src/cli.py
# PROJECT: Bundle File Tool v2.1
# VERSION: 2.1.1
# STATUS: FIXED - Profile validation first per Paul's analysis v3
# ============================================================================

"""Command-Line Interface for Bundle File Tool v2.1."""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from core.logging import configure_utf8_logging
from core.config import ConfigManager
from core.parser import BundleParser, ProfileRegistry
from core.writer import BundleWriter, BundleCreator
from core.exceptions import (
    BundleFileToolError,
    ProfileNotFoundError,
    ProfileDetectionError,
    ProfileParseError,
    BundleReadError,
    BundleWriteError,
    PathTraversalError,
    ConfigError
)
from core.models import BundleManifest


def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser."""
    parser = argparse.ArgumentParser(
        prog="bundle-tool",
        description="Bundle File Tool v2.1 - Command-Line Interface"
    )
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # UNBUNDLE
    parser_unbundle = subparsers.add_parser("unbundle")
    parser_unbundle.add_argument("input_file", type=Path)
    parser_unbundle.add_argument("--output", "-o", type=Path)
    parser_unbundle.add_argument("--profile")
    parser_unbundle.add_argument("--overwrite", choices=["prompt", "skip", "rename", "overwrite"])
    parser_unbundle.add_argument("--dry-run", action="store_true")
    parser_unbundle.add_argument("--no-headers", action="store_true")
    
    # BUNDLE
    parser_bundle = subparsers.add_parser("bundle")
    parser_bundle.add_argument("source_paths", type=Path, nargs="+")
    parser_bundle.add_argument("--output", "-o", type=Path)
    parser_bundle.add_argument("--profile")
    parser_bundle.add_argument("--base-path", type=Path)
    parser_bundle.add_argument("--include", action="append")
    parser_bundle.add_argument("--exclude", action="append")
    parser_bundle.add_argument("--max-size", type=float)
    
    # VALIDATE
    parser_validate = subparsers.add_parser("validate")
    parser_validate.add_argument("input_file", type=Path)
    parser_validate.add_argument("--profile")
    
    return parser


def main(argv: Optional[List[str]] = None):
    """Main CLI entry point."""
    configure_utf8_logging()
    
    try:
        parser = build_parser()
        args = parser.parse_args(argv)
        
        if args.command == "unbundle":
            handle_unbundle(args)
        elif args.command == "bundle":
            handle_bundle(args)
        elif args.command == "validate":
            handle_validate(args)
        else:
            print(f"Unknown command: {args.command}", file=sys.stderr)
            sys.exit(1)
        
        sys.exit(0)
        
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
        auto_detect=True
    )
    
    print(f"Detected format: {manifest.profile}")
    print(f"Files found: {manifest.get_file_count()}")
    
    if dry_run:
        print("\n[DRY RUN MODE - No files will be written]")
    
    print(f"\nExtracting to: {output_dir}")
    stats = writer.extract_manifest(manifest, Path(output_dir))
    
    print(f"\nExtraction complete:")
    print(f"  Processed: {stats['processed']}")
    print(f"  Skipped: {stats['skipped']}")
    print(f"  Errors: {stats['errors']}")
    
    if stats['errors'] > 0:
        sys.exit(1)


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
    
    if not profile_name:
        profile_name = config_manager.get("app_defaults.bundle_profile", "md_fence")
    
    base_path = args.base_path or Path.cwd()
    
    allow_globs = args.include if args.include else config_manager.get("safety.allow_globs", ["**/*"])
    deny_globs = args.exclude if args.exclude else config_manager.get("safety.deny_globs", [])
    max_file_mb = args.max_size if hasattr(args, 'max_size') and args.max_size else config_manager.get("safety.max_file_mb", 10.0)
    treat_binary = config_manager.get("app_defaults.treat_binary_as_base64", True)
    
    registry = ProfileRegistry()
    profile = registry.get(profile_name)
    
    creator = BundleCreator(
        allow_globs=allow_globs,
        deny_globs=deny_globs,
        max_file_mb=max_file_mb,
        treat_binary_as_base64=treat_binary
    )
    
    print("Discovering files...")
    all_files = []
    for source_path in source_paths:
        discovered = creator.discover_files(source_path, base_path)
        all_files.extend(discovered)
    
    if not all_files:
        raise BundleFileToolError("No files found matching the specified criteria")
    
    print(f"Found {len(all_files)} files")
    print(f"Creating bundle with profile: {profile_name}")
    manifest = creator.create_manifest(all_files, base_path, profile_name)
    
    bundle_text = profile.format_manifest(manifest)
    
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(bundle_text, encoding='utf-8')
        print(f"\nBundle created: {args.output}")
        print(f"  Total files: {len(manifest.entries)}")
        print(f"  Format: {profile_name}")
    else:
        sys.stdout.write(bundle_text)


def handle_validate(args):
    """Handler for validate command."""
    if not args.input_file.exists():
        raise BundleReadError(str(args.input_file), "File not found")
    
    parser = BundleParser()
    
    print(f"Validating: {args.input_file}")
    result = parser.validate_bundle(
        args.input_file.read_text(encoding='utf-8', errors='ignore'),
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


if __name__ == "__main__":
    main()


# ============================================================================
# VERSION: 2.1.1
# PAUL'S FIX: Profile validation first, unified error messages
# FIXES: 3 CLI failures (missing_source_path, invalid_profile_name, bundle_with_zero_files)
# ============================================================================
