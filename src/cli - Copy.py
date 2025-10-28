# ============================================================================
# SOURCEFILE: cli.py
# RELPATH: bundle_file_tool_v2/src/cli.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.0
# LIFECYCLE: Proposed
# DESCRIPTION: Command-line interface - thin controller over headless core
# ARCHITECT: George (Phase 3 guidance document)
# ============================================================================

"""
Command-Line Interface for Bundle File Tool v2.1.

Provides scriptable access to bundle/unbundle/validate operations.
Thin controller layer that orchestrates core modules per George's
architectural guidance.

Usage:
    python cli.py unbundle <bundle_file> [options]
    python cli.py bundle <source_paths...> [options]
    python cli.py validate <bundle_file>
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

# Import core components (headless core modules)
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


def main():
    """
    Main entry point for the CLI.
    
    Parses command-line arguments and routes to appropriate handler.
    All business logic delegated to core modules per architectural guidance.
    """
    configure_utf8_logging()
    parser = argparse.ArgumentParser(
        prog="bundle-tool",
        description="Bundle File Tool v2.1 - Command-Line Interface",
        epilog="For detailed help on a command, use: bundle-tool <command> --help"
    )
    
    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
        help="Available commands"
    )
    
    # ===== UNBUNDLE COMMAND =====
    parser_unbundle = subparsers.add_parser(
        "unbundle",
        help="Extract files from a bundle",
        description="Extracts all files from a bundle file to the specified output directory."
    )
    parser_unbundle.add_argument(
        "input_file",
        type=Path,
        help="Path to the bundle file to extract"
    )
    parser_unbundle.add_argument(
        "--output",
        type=Path,
        help="Output directory (overrides config file setting)"
    )
    parser_unbundle.add_argument(
        "--profile",
        help="Force a specific profile for parsing (plain_marker, md_fence, jsonl). Auto-detects if not specified."
    )
    parser_unbundle.add_argument(
        "--overwrite",
        choices=["prompt", "skip", "rename", "overwrite"],
        help="Overwrite policy for existing files (overrides config)"
    )
    parser_unbundle.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview operations without writing files"
    )
    parser_unbundle.add_argument(
        "--no-headers",
        action="store_true",
        help="Do not add file headers when extracting"
    )
    
    # ===== BUNDLE COMMAND =====
    parser_bundle = subparsers.add_parser(
        "bundle",
        help="Create a bundle from source files",
        description="Creates a bundle file from source files or directories."
    )
    parser_bundle.add_argument(
        "source_paths",
        type=Path,
        nargs="+",
        help="Source files or directories to bundle"
    )
    parser_bundle.add_argument(
        "--output",
        type=Path,
        help="Output file path (writes to stdout if not specified)"
    )
    parser_bundle.add_argument(
        "--profile",
        help="Bundle profile to use: plain_marker, md_fence, jsonl (overrides config, default: md_fence)"
    )
    parser_bundle.add_argument(
        "--base-path",
        type=Path,
        help="Base path to make file paths relative to"
    )
    parser_bundle.add_argument(
        "--include",
        action="append",
        help="Glob pattern for files to include (can be specified multiple times)"
    )
    parser_bundle.add_argument(
        "--exclude",
        action="append",
        help="Glob pattern for files to exclude (can be specified multiple times)"
    )
    parser_bundle.add_argument(
        "--max-size",
        type=float,
        help="Maximum file size in MB (overrides config)"
    )
    
    # ===== VALIDATE COMMAND =====
    parser_validate = subparsers.add_parser(
        "validate",
        help="Validate a bundle file",
        description="Validates a bundle file without extracting it. Reports format, file count, and any errors."
    )
    parser_validate.add_argument(
        "input_file",
        type=Path,
        help="Path to the bundle file to validate"
    )
    parser_validate.add_argument(
        "--profile",
        help="Force a specific profile for validation (auto-detects if not specified)"
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Route to appropriate handler with error handling
    try:
        if args.command == "unbundle":
            handle_unbundle(args)
        elif args.command == "bundle":
            handle_bundle(args)
        elif args.command == "validate":
            handle_validate(args)
        
        sys.exit(0)  # Success
        
    except BundleFileToolError as e:
        # Catch all our custom exceptions
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        # Catch unexpected errors
        print(f"CRITICAL ERROR: An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)


def handle_unbundle(args):
    """
    Handler for unbundle command.
    
    Orchestrates: ConfigManager -> BundleParser -> BundleWriter
    Per George's architectural guidance: thin controller, no business logic.
    
    Args:
        args: Parsed command-line arguments from argparse
    """
    # 1. Load configuration
    config_manager = ConfigManager()
    
    # 2. Apply CLI overrides with precedence: CLI args > config > defaults
    output_dir = args.output or config_manager.get("global_settings.output_dir")
    if not output_dir:
        raise BundleFileToolError(
            "Output directory must be specified via --output or in bundle_config.json"
        )
    
    overwrite_policy = args.overwrite or config_manager.get("app_defaults.overwrite_policy", "prompt")
    add_headers = not args.no_headers and config_manager.get("app_defaults.add_headers", True)
    dry_run = args.dry_run
    
    # 3. Validate input file exists
    if not args.input_file.exists():
        raise BundleReadError(str(args.input_file), "File not found")
    
    # 4. Instantiate core components
    parser = BundleParser()
    writer = BundleWriter(
        base_path=output_dir,
        overwrite_policy=overwrite_policy,
        dry_run=dry_run,
        add_headers=add_headers
    )
    
    # 5. Parse bundle file
    print(f"Reading bundle: {args.input_file}")
    manifest = parser.parse_file(
        args.input_file,
        profile_name=args.profile,
        auto_detect=True
    )
    
    print(f"Detected format: {manifest.profile}")
    print(f"Files found: {manifest.get_file_count()}")
    print(f"  Text files: {manifest.get_text_count()}")
    print(f"  Binary files: {manifest.get_binary_count()}")
    
    # 6. Extract files to disk
    if dry_run:
        print("\n[DRY RUN MODE - No files will be written]")
    
    print(f"\nExtracting to: {output_dir}")
    stats = writer.extract_manifest(manifest, Path(output_dir))
    
    # 7. Report results
    print(f"\nExtraction complete:")
    print(f"  Processed: {stats['processed']}")
    print(f"  Skipped: {stats['skipped']}")
    print(f"  Errors: {stats['errors']}")
    
    if stats['errors'] > 0:
        sys.exit(1)


def handle_bundle(args):
    """
    Handler for bundle command.
    
    Orchestrates: ConfigManager -> BundleCreator -> Profile -> Output
    Per George's architectural guidance: thin controller, no business logic.
    
    Args:
        args: Parsed command-line arguments from argparse
    """
    # 1. Load configuration
    config_manager = ConfigManager()
    
    # 2. Apply CLI overrides with precedence
    profile_name = args.profile or config_manager.get("app_defaults.bundle_profile", "md_fence")
    base_path = args.base_path or Path.cwd()
    
    # Merge include/exclude globs
    allow_globs = args.include if args.include else config_manager.get("safety.allow_globs", ["**/*"])
    deny_globs = args.exclude if args.exclude else config_manager.get("safety.deny_globs", [])
    max_file_mb = args.max_size if hasattr(args, 'max_size') and args.max_size else config_manager.get("safety.max_file_mb", 10.0)
    treat_binary = config_manager.get("app_defaults.treat_binary_as_base64", True)
    
    # 3. Validate source paths
    for source_path in args.source_paths:
        if not source_path.exists():
            raise BundleFileToolError(f"Source path not found: {source_path}")
    
    # 4. Get profile instance
    registry = ProfileRegistry()
    try:
        profile = registry.get(profile_name)
    except ProfileNotFoundError as e:
        available = ", ".join(registry.list_profiles())
        raise BundleFileToolError(f"Invalid profile '{profile_name}'. Available: {available}")
    
    # 5. Instantiate BundleCreator
    creator = BundleCreator(
        allow_globs=allow_globs,
        deny_globs=deny_globs,
        max_file_mb=max_file_mb,
        treat_binary_as_base64=treat_binary
    )
    
    # 6. Discover files from all source paths
    print("Discovering files...")
    all_files = []
    for source_path in args.source_paths:
        discovered = creator.discover_files(source_path, base_path)
        all_files.extend(discovered)
    
    if not all_files:
        raise BundleFileToolError("No files found matching the specified criteria")
    
    print(f"Found {len(all_files)} files")
    
    # 7. Create manifest
    print(f"Creating bundle with profile: {profile_name}")
    manifest = creator.create_manifest(all_files, base_path, profile_name)
    
    # 8. Format bundle using profile
    bundle_text = profile.format_manifest(manifest)
    
    # 9. Handle output
    if args.output:
        # Write to file
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(bundle_text, encoding='utf-8')
        print(f"\nBundle created: {args.output}")
        print(f"  Total files: {len(manifest.entries)}")
        print(f"  Format: {profile_name}")
    else:
        # Write to stdout
        sys.stdout.write(bundle_text)


def handle_validate(args):
    """
    Handler for validate command.
    
    Orchestrates: BundleParser -> validation report
    Per George's architectural guidance: thin controller, no business logic.
    
    Args:
        args: Parsed command-line arguments from argparse
    """
    # 1. Validate input file exists
    if not args.input_file.exists():
        raise BundleReadError(str(args.input_file), "File not found")
    
    # 2. Instantiate parser
    parser = BundleParser()
    
    # 3. Validate bundle
    print(f"Validating: {args.input_file}")
    result = parser.validate_bundle(
        args.input_file.read_text(encoding='utf-8', errors='ignore'),
        profile_name=args.profile
    )
    
    # 4. Print validation report
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
    
    # Exit with error code if invalid
    if not result['valid']:
        sys.exit(1)


if __name__ == "__main__":
    main()


# ============================================================================
# LIFECYCLE STATUS: Proposed
# NEXT STEPS: Test suite for CLI commands, integration testing
# DEPENDENCIES: All Phase 1 & Phase 2 core modules
# ARCHITECT: Implements George's Phase 3 guidance exactly
# COMPLIANCE: Thin controller, no business logic, configuration precedence
# ============================================================================
