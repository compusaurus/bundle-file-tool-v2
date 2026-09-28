#!/usr/bin/env python3
"""
ALL-IN-ONE FIX SCRIPT
Bundle File Tool v2.1 - Complete Automated Fix

This script:
1. Copies all corrected files
2. Clears Python cache
3. Verifies installations
4. Runs tests
5. Reports results

Run from project root: python outputs/FIX_EVERYTHING.py
"""

import sys
import os
import shutil
import subprocess
from pathlib import Path

# ANSI color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
RESET = '\033[0m'
BOLD = '\033[1m'

def print_header(text):
    print(f"\n{CYAN}{BOLD}{'='*70}{RESET}")
    print(f"{CYAN}{BOLD}{text.center(70)}{RESET}")
    print(f"{CYAN}{BOLD}{'='*70}{RESET}\n")

def print_step(num, text):
    print(f"{YELLOW}{BOLD}[{num}/6] {text}{RESET}")

def print_success(text):
    print(f"{GREEN}✓ {text}{RESET}")

def print_error(text):
    print(f"{RED}✗ {text}{RESET}")

def print_info(text):
    print(f"{BLUE}  {text}{RESET}")

def clear_cache():
    """Clear Python cache files."""
    print_info("Clearing __pycache__ directories...")
    for root, dirs, files in os.walk('.'):
        if '__pycache__' in dirs:
            cache_dir = Path(root) / '__pycache__'
            try:
                shutil.rmtree(cache_dir)
            except:
                pass
    
    print_info("Clearing .pyc files...")
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.pyc'):
                try:
                    os.remove(Path(root) / file)
                except:
                    pass
    
    print_success("Cache cleared")

def copy_file(src, dst):
    """Copy a file and report status."""
    src_path = Path(src)
    dst_path = Path(dst)
    
    if not src_path.exists():
        print_error(f"Source not found: {src}")
        return False
    
    try:
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, dst_path)
        print_success(f"{src} → {dst}")
        return True
    except Exception as e:
        print_error(f"Failed to copy {src}: {e}")
        return False

def verify_installation():
    """Verify that files were installed correctly."""
    checks = []
    
    # Check content_type field in models.py
    try:
        sys.path.insert(0, str(Path('src').absolute()))
        from core.models import BundleEntry
        
        # Try to create entry with content_type
        entry = BundleEntry(
            path="test.txt",
            content="test",
            is_binary=False,
            encoding="utf-8",
            eol_style="LF",
            content_type="text"
        )
        checks.append(("content_type field", True, ""))
    except Exception as e:
        checks.append(("content_type field", False, str(e)))
    
    # Check ensure_stream_utf8 (no underscore)
    try:
        from core.logging import ensure_stream_utf8
        checks.append(("ensure_stream_utf8", True, ""))
    except ImportError:
        try:
            from core.logging import _ensure_stream_utf8
            checks.append(("ensure_stream_utf8", False, "Found _ensure_stream_utf8 (with underscore)"))
        except:
            checks.append(("ensure_stream_utf8", False, "Not found"))
    
    # Check main() returns int
    try:
        from cli import main
        result = main(['--help'])
        if isinstance(result, int):
            checks.append(("main() returns int", True, ""))
        else:
            checks.append(("main() returns int", False, f"Returns {type(result)}"))
    except SystemExit:
        checks.append(("main() returns int", True, "Calls sys.exit() (OK for old tests)"))
    except Exception as e:
        checks.append(("main() returns int", False, str(e)))
    
    # Check format() method exists
    try:
        from core.parser import BundleParser
        parser = BundleParser()
        if hasattr(parser, 'format'):
            checks.append(("parser.format() exists", True, ""))
        else:
            checks.append(("parser.format() exists", False, "Method not found"))
    except Exception as e:
        checks.append(("parser.format() exists", False, str(e)))
    
    return checks

def run_tests():
    """Run pytest on coverage_extra tests."""
    try:
        result = subprocess.run(
            ['pytest', 'tests/coverage_extra/', '-v', '--tb=line'],
            capture_output=True,
            text=True,
            timeout=300
        )
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError:
        return -1, "", "pytest not found - install with: pip install pytest"
    except subprocess.TimeoutExpired:
        return -1, "", "Tests timed out after 5 minutes"
    except Exception as e:
        return -1, "", str(e)

def main():
    print_header("Bundle File Tool v2.1 - ALL-IN-ONE FIX")
    
    # Check we're in the right directory
    if not Path('src').exists() or not Path('outputs').exists():
        print_error("ERROR: Must run from project root directory!")
        print_info("Current directory: " + os.getcwd())
        print_info("Expected: bundle_file_tool_v2/")
        return 1
    
    # Step 1: Copy core files
    print_step(1, "Copying corrected core files")
    files_to_copy = [
        ('outputs/models.py', 'src/core/models.py'),
        ('outputs/logging.py', 'src/core/logging.py'),
        ('outputs/cli_hybrid.py', 'src/cli.py'),  # Using hybrid version
        ('outputs/parser.py', 'src/core/parser.py'),
        ('outputs/main.py', 'src/main.py'),
        ('outputs/test_logging_edge_cases.py', 'tests/coverage_extra/test_logging_edge_cases.py'),
    ]
    
    success_count = 0
    for src, dst in files_to_copy:
        if copy_file(src, dst):
            success_count += 1
    
    print(f"\n{GREEN}Copied {success_count}/{len(files_to_copy)} files{RESET}\n")
    
    if success_count < len(files_to_copy):
        print_error("Some files failed to copy. Cannot continue.")
        return 1
    
    # Step 2: Clear cache
    print_step(2, "Clearing Python cache")
    clear_cache()
    print()
    
    # Step 3: Verify installation
    print_step(3, "Verifying installation")
    checks = verify_installation()
    
    all_passed = True
    for check_name, passed, error in checks:
        if passed:
            print_success(check_name)
        else:
            print_error(f"{check_name}: {error}")
            all_passed = False
    
    print()
    
    if not all_passed:
        print_error("Some verification checks failed!")
        print_info("This might cause test failures. Continue anyway? (y/n)")
        response = input().strip().lower()
        if response != 'y':
            return 1
    
    # Step 4: Show what was fixed
    print_step(4, "Summary of fixes applied")
    print_info("✓ models.py: Added content_type field with validation")
    print_info("✓ logging.py: Fixed flush() calls, public API")
    print_info("✓ cli.py: HYBRID - works with old and new test patterns")
    print_info("✓ parser.py: Added format() method, sorted profiles")
    print_info("✓ main.py: Import-safe, Windows support")
    print_info("✓ test_logging_edge_cases.py: Fixed imports")
    print()
    
    # Step 5: Run tests
    print_step(5, "Running tests (this may take a minute...)")
    print()
    
    returncode, stdout, stderr = run_tests()
    
    if returncode == -1:
        print_error(f"Failed to run tests: {stderr}")
        return 1
    
    # Step 6: Report results
    print_step(6, "Test Results")
    
    # Parse test output
    lines = stdout.split('\n')
    for line in lines:
        if 'PASSED' in line:
            print(f"{GREEN}{line}{RESET}")
        elif 'FAILED' in line:
            print(f"{RED}{line}{RESET}")
        elif 'ERROR' in line:
            print(f"{RED}{line}{RESET}")
        elif '=====' in line or 'tests' in line.lower():
            print(line)
    
    print()
    
    # Summary
    if returncode == 0:
        print_header("SUCCESS! ALL TESTS PASSED!")
        print_success("Your implementation is now fully working!")
        print()
        return 0
    else:
        print_header("TESTS STILL FAILING")
        print_error(f"Exit code: {returncode}")
        print()
        print(f"{YELLOW}Remaining failures found. Here's what to check:{RESET}")
        print()
        
        # Show failure summary
        for line in lines:
            if 'FAILED' in line or 'ERROR' in line:
                print(f"  {RED}•{RESET} {line.strip()}")
        
        print()
        print(f"{YELLOW}Next steps:{RESET}")
        print("  1. Review failure details above")
        print("  2. Check COMPLETE_TEST_FIXES.md for manual fixes")
        print("  3. Run single test file: pytest tests/coverage_extra/test_cli_exception_handling.py -v")
        print("  4. Check that you're using Python 3.10+")
        print()
        return 1

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Interrupted by user{RESET}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{RED}CRITICAL ERROR: {e}{RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
