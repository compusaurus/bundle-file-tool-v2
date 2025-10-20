# ============================================================================
# STANDALONE TEST HARNESS: GlobFilter (v6 - Final, Hardened Version)
# DESCRIPTION: This harness contains the final, unified GlobFilter class with
#              a hardened __init__ method to handle empty allow lists. It also
#              includes a new test category for this specific edge case.
# ============================================================================

import sys
import os
from pathlib import PurePosixPath, Path
from fnmatch import fnmatchcase
from typing import List, Optional, Sequence

# This makes the harness a true integration test by using the project's code
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
try:
    from core.exceptions import GlobFilterError
except ImportError:
    # Define a fallback exception if the harness is run completely standalone
    class GlobFilterError(Exception):
        def __init__(self, pattern, reason):
            self.pattern = pattern
            self.reason = reason
            super().__init__(f"Invalid glob pattern '{pattern}': {reason}")

# ============================================================================
# FINAL VERIFIED GlobFilter IMPLEMENTATION (v6)
# This class is now ready to be copied into validators.py
# ============================================================================
class GlobFilter:
    """
    Filters files using glob patterns with deny-first precedence.
    This implementation is verified against all design criteria and edge cases.
    """

    def __init__(self,
                 allow_patterns: Optional[Sequence[str]] = None,
                 deny_patterns: Optional[Sequence[str]] = None):
        # (v6 HARDENED LOGIC) Treat `None` or an empty list for allow_patterns
        # as a default "allow all".
        self.allow_patterns = list(allow_patterns) if allow_patterns else ["**/*"]
        self.deny_patterns = list(deny_patterns) if deny_patterns else []
        for pattern in self.allow_patterns + self.deny_patterns:
            self._validate_pattern(pattern)

    def _match_any(self, path_str: str, patterns: list) -> bool:
        if not path_str: return False
        p = PurePosixPath(str(path_str).replace('\\', '/'))
        paths_to_check = [p] + [PurePosixPath(*p.parts[i:]) for i in range(1, len(p.parts))]
        for pat in patterns:
            for path_segment in paths_to_check:
                if fnmatchcase(str(path_segment), pat):
                    return True
        return False

    def should_include(self, path: str) -> bool:
        if not path or not path.strip():
            return False
        if self.deny_patterns and self._match_any(path, self.deny_patterns):
            return False
        # If allow_patterns is empty OR is the default "allow all", then it's an allow.
        if not self.allow_patterns or self.allow_patterns == ["**/*"]:
             return True
        return self._match_any(path, self.allow_patterns)

    def filter_paths(self, paths: List[str], base_path: Optional[str] = None) -> List[str]:
        filtered = []
        base = Path(base_path) if base_path else None
        for path_str in paths:
            path_obj = Path(path_str)
            rel_path = path_str
            if base:
                try: rel_path = str(path_obj.relative_to(base))
                except ValueError: rel_path = path_obj.name
            if self.should_include(rel_path):
                filtered.append(path_str)
        return filtered

    def _validate_pattern(self, pattern: str) -> None:
        if not pattern or not isinstance(pattern, str) or not pattern.strip():
            raise GlobFilterError(pattern, "Empty or invalid glob pattern provided")
        if pattern.count('[') != pattern.count(']'):
            raise GlobFilterError(pattern, "Unmatched brackets in pattern")

# ============================================================================
# Exhaustive Acceptance Tests (v6)
# ============================================================================
def run_tests():
    print("Running Exhaustive Test Harness for GlobFilter (v6)...")
    total_tests, passed_count, failed_count = 0, 0, 0

    def run_test_category(name, test_func):
        nonlocal total_tests, passed_count, failed_count
        print(f"\n--- Testing Category: {name} ---")
        try:
            results = test_func()
            total_tests += len(results)
            for success, test_name, detail in results:
                if success:
                    passed_count += 1
                    print(f"  ✓ PASS: {test_name:<40} ({detail})")
                else:
                    failed_count += 1
                    print(f"  ✗ FAIL: {test_name:<40} ({detail})")
        except Exception as e:
            failed_count += 1
            print(f"  ✗ FATAL ERROR in {name}: {e.__class__.__name__}: {e}")

    def test_init_and_validation():
        results = []
        try:
            f = GlobFilter()
            results.append((f.allow_patterns == ["**/*"] and f.deny_patterns == [], "Default __init__", "OK"))
            GlobFilter(allow_patterns=["*.py"], deny_patterns=["*.log"])
            results.append((True, "Valid Custom Patterns", "OK"))
        except Exception as e:
            results.append((False, "Valid Inits", f"Crashed: {e}"))
        
        try:
            GlobFilter(allow_patterns=["[unclosed"])
            results.append((False, "Invalid Pattern (unclosed bracket)", "Did not raise GlobFilterError"))
        except GlobFilterError as e:
            detail = "Raised GlobFilterError as expected"
            results.append((e.pattern == "[unclosed" and "Unmatched" in e.reason, "Invalid Pattern (unclosed bracket)", detail))
        try:
            GlobFilter(deny_patterns=[" "])
            results.append((False, "Invalid Pattern (whitespace)", "Did not raise GlobFilterError"))
        except GlobFilterError as e:
            detail = "Raised GlobFilterError as expected"
            results.append((e.pattern == " " and "Empty" in e.reason, "Invalid Pattern (whitespace)", detail))
        return results
        
    def test_init_edge_cases():
        results = []
        # Test 1: `allow_patterns` is None (should default to ['**/*'])
        f1 = GlobFilter(allow_patterns=None, deny_patterns=['*.log'])
        actual1 = f1.should_include('src/main.py')
        results.append((actual1 is True, "Init with allow=None", "Correctly allows path"))

        # Test 2: `allow_patterns` is an empty list (should also default to ['**/*'])
        f2 = GlobFilter(allow_patterns=[], deny_patterns=['*.log'])
        actual2 = f2.should_include('src/main.py')
        results.append((actual2 is True, "Init with allow=[]", "Correctly allows path"))
        
        # Test 3: Ensure deny still works with default allow
        actual3 = f2.should_include('app.log')
        results.append((actual3 is False, "Init with allow=[] and deny", "Correctly denies path"))
        return results

    def test_should_include_logic():
        cases = [
            {'name': 'Deny Overrides Allow', 'allow': ['**/*'], 'deny': ['*.log'], 'path': 'app.log', 'expected': False},
            {'name': 'Deny Overrides Specific Allow', 'allow': ['*.py', '*.log'], 'deny': ['*.log'], 'path': 'app.log', 'expected': False},
            {'name': 'Deny Component Overrides Allow', 'allow': ['src/**/*.py'], 'deny': ['**/temp/**'], 'path': 'src/app/temp/main.py', 'expected': False},
            {'name': 'Deny Component (Windows Path)', 'allow': ['src/**/*.py'], 'deny': ['**/temp/**'], 'path': 'src\\app\\temp\\main.py', 'expected': False},
            {'name': 'Allow by Default (No Allow Rules)', 'allow': None, 'deny': [], 'path': 'README.md', 'expected': True},
            {'name': 'Allow with Default (Deny Only)', 'allow': None, 'deny': ['*.tmp'], 'path': 'README.md', 'expected': True},
            {'name': 'Deny with Default Allow', 'allow': None, 'deny': ['*.md'], 'path': 'README.md', 'expected': False},
            {'name': 'Allow **/* (No Deny)', 'allow': ['**/*'], 'deny': [], 'path': 'any/file.txt', 'expected': True},
            {'name': 'Explicit Allow Match', 'allow': ['*.py'], 'deny': [], 'path': 'main.py', 'expected': True},
            {'name': 'Explicit Allow No Match', 'allow': ['*.py'], 'deny': [], 'path': 'README.md', 'expected': False},
            {'name': 'Recursive Allow Match', 'allow': ['**/*.py'], 'deny': [], 'path': 'src/app/c/button.py', 'expected': True},
            {'name': 'Recursive Allow No Match', 'allow': ['src/**/*.py'], 'deny': [], 'path': 'tests/test_button.py', 'expected': False},
            {'name': 'Filename Only Match', 'allow': ['main.py'], 'deny': [], 'path': 'src/app/main.py', 'expected': True},
            {'name': 'Filename Only Deny', 'allow': ['**/*'], 'deny': ['main.py'], 'path': 'src/app/main.py', 'expected': False},
            {'name': 'Empty Path String', 'allow': ['**/*'], 'deny': [], 'path': '', 'expected': False},
            {'name': 'Whitespace Path String', 'allow': ['**/*'], 'deny': [], 'path': '  ', 'expected': False},
            {'name': 'None Path', 'allow': ['**/*'], 'deny': [], 'path': None, 'expected': False},
        ]
        results = []
        for case in cases:
            f = GlobFilter(allow_patterns=case['allow'], deny_patterns=case['deny'])
            actual = f.should_include(case['path'])
            expected = case['expected']
            detail = f"Expected: {expected}, Got: {actual}"
            results.append((actual == expected, case['name'], detail))
        return results

    def test_filter_paths_method():
        paths = ["src/main.py", "src/config.json", "logs/app.log", "tests/test.py"]
        results = []
        f = GlobFilter(deny_patterns=["*.log"])
        filtered = f.filter_paths(paths)
        expected = ["src/main.py", "src/config.json", "tests/test.py"]
        results.append((filtered == expected, "filter_paths: Simple Deny", f"Got {len(filtered)}/{len(expected)} items"))
        f = GlobFilter(allow_patterns=["*.py"])
        filtered = f.filter_paths(paths)
        expected = ["src/main.py", "tests/test.py"]
        results.append((filtered == expected, "filter_paths: Explicit Allow", f"Got {len(filtered)}/{len(expected)} items"))
        f = GlobFilter(allow_patterns=["src/**"], deny_patterns=["*.json"])
        filtered = f.filter_paths(paths)
        expected = ["src/main.py"]
        results.append((filtered == expected, "filter_paths: Allow and Deny", f"Got {len(filtered)}/{len(expected)} item"))
        paths_full = [str(Path.cwd() / p) for p in paths]
        f = GlobFilter(allow_patterns=["src/*.py"])
        filtered = f.filter_paths(paths_full, base_path=str(Path.cwd()))
        expected = [str(Path.cwd() / "src/main.py")]
        results.append((filtered == expected, "filter_paths: With Base Path", f"Got {len(filtered)}/{len(expected)} item"))
        return results

    # Execute all test categories
    run_test_category("__init__ and Validation", test_init_and_validation)
    run_test_category("Initialization Edge Cases", test_init_edge_cases)
    run_test_category("should_include Logic", test_should_include_logic)
    run_test_category("filter_paths Method", test_filter_paths_method)

    # Print Summary
    print("\n" + "="*60)
    print("HARNESS EXECUTION SUMMARY")
    print(f"  Total Tests: {total_tests}\n  Passed:      {passed_count}\n  Failed:      {failed_count}")
    print("="*60 + "\n")
    
    if failed_count == 0:
        print("SUCCESS: All exhaustive tests for the complete GlobFilter class passed.")
    else:
        print("FAILURE: One or more tests failed.")

if __name__ == "__main__":
    run_tests()

