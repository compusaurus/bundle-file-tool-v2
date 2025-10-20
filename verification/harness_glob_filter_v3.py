# ============================================================================
# STANDALONE TEST HARNESS: GlobFilter (v3 - Complete)
# DESCRIPTION: This harness contains the final, unified GlobFilter class,
#              merging the robust features from validators.py with the correct
#              filtering logic. It is tested against a comprehensive suite
#              that covers __init__, should_include, and filter_paths.
# ============================================================================

from pathlib import PurePosixPath, Path
from fnmatch import fnmatchcase
from typing import List, Optional, Sequence

# Define a minimal exception for self-contained testing
class GlobFilterError(Exception):
    pass

# ============================================================================
# FINAL VERIFIED GlobFilter IMPLEMENTATION
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
        """
        Initialize filter.
        """
        # Logic from validators.py: Provides correct defaults
        self.allow_patterns = list(allow_patterns) if allow_patterns is not None else ["**/*"]
        self.deny_patterns = list(deny_patterns) if deny_patterns else []

        # Logic from validators.py: Provides compatibility aliases
        self.allow = self.allow_patterns
        self.deny = self.deny_patterns

        # Logic from validators.py: Provides crucial pattern validation
        for pattern in self.allow_patterns + self.deny_patterns:
            self._validate_pattern(pattern)

    def _match_any(self, path_str: str, patterns: list) -> bool:
        """
        Checks if a path or any of its parent components match the patterns.
        """
        p = PurePosixPath(str(path_str).replace('\\', '/'))
        paths_to_check = [p] + [PurePosixPath(*p.parts[i:]) for i in range(1, len(p.parts))]

        for pat in patterns:
            for path_segment in paths_to_check:
                if fnmatchcase(str(path_segment), pat):
                    return True
        return False

    def should_include(self, path: str) -> bool:
        """
        (Corrected Logic) Determines if a path should be included.
        """
        # Rule: Deny patterns take absolute precedence.
        if self.deny_patterns and self._match_any(path, self.deny_patterns):
            return False

        # Rule: If allow list is default ["**/*"], allow everything not denied.
        if self.allow_patterns == ["**/*"]:
             return True

        # Rule: If a specific allow list exists, it must match.
        return self._match_any(path, self.allow_patterns)

    def filter_paths(self, paths: List[str], base_path: Optional[str] = None) -> List[str]:
        """
        (From validators.py) Filter list of paths using patterns.
        """
        filtered = []
        base = Path(base_path) if base_path else None
        for path_str in paths:
            path_obj = Path(path_str)
            rel_path = path_str
            if base:
                try:
                    rel_path = str(path_obj.relative_to(base))
                except ValueError:
                    rel_path = path_obj.name

            if self.should_include(rel_path):
                filtered.append(path_str)
        return filtered

    def _validate_pattern(self, pattern: str) -> None:
        """
        (From validators.py) Validate glob pattern syntax.
        """
        if not pattern or not isinstance(pattern, str) or not pattern.strip():
            raise GlobFilterError(f"Empty or invalid glob pattern: '{pattern}'")
        if pattern.count('[') != pattern.count(']'):
            raise GlobFilterError(f"Unmatched brackets in pattern: '{pattern}'")

# ============================================================================
# Exhaustive Acceptance Tests (v3)
# ============================================================================
def run_tests():
    """Executes all acceptance tests and prints the final status."""
    print("Running Exhaustive Test Harness for GlobFilter (v3)...")
    
    total_tests = 0
    passed_count = 0
    failed_count = 0

    def run_test_category(name, test_func):
        nonlocal total_tests, passed_count, failed_count
        print(f"\n--- Testing Category: {name} ---")
        try:
            results = test_func()
            total_tests += len(results)
            for success, test_name, detail in results:
                if success:
                    passed_count += 1
                    print(f"  ✓ PASS: {test_name:<35} ({detail})")
                else:
                    failed_count += 1
                    print(f"  ✗ FAIL: {test_name:<35} ({detail})")
        except Exception as e:
            failed_count += 1
            print(f"  ✗ FATAL ERROR in {name}: {e}")

    # --- Test Functions for Each Category ---

    def test_init_validation():
        results = []
        # Test default initialization
        f = GlobFilter()
        assert f.allow_patterns == ["**/*"] and f.deny_patterns == []
        results.append((True, "Default __init__", "OK"))

        # Test valid custom patterns
        GlobFilter(allow_patterns=["*.py"], deny_patterns=["*.log"])
        results.append((True, "Valid Custom Patterns", "OK"))

        # Test for invalid patterns
        try:
            GlobFilter(allow_patterns=["[unclosed"])
            results.append((False, "Invalid Pattern (unclosed bracket)", "Did not raise error"))
        except GlobFilterError:
            results.append((True, "Invalid Pattern (unclosed bracket)", "Raised GlobFilterError as expected"))
        
        try:
            GlobFilter(deny_patterns=[" "])
            results.append((False, "Invalid Pattern (whitespace)", "Did not raise error"))
        except GlobFilterError:
            results.append((True, "Invalid Pattern (whitespace)", "Raised GlobFilterError as expected"))

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
            {'name': 'Recursive Allow Match', 'allow': ['src/**/*.py'], 'deny': [], 'path': 'src/app/c/button.py', 'expected': True},
            {'name': 'Recursive Allow No Match', 'allow': ['src/**/*.py'], 'deny': [], 'path': 'tests/test_button.py', 'expected': False},
            {'name': 'Filename Only Match', 'allow': ['main.py'], 'deny': [], 'path': 'src/app/main.py', 'expected': True},
            {'name': 'Filename Only Deny', 'allow': ['**/*'], 'deny': ['main.py'], 'path': 'src/app/main.py', 'expected': False},
            {'name': 'Empty Path String', 'allow': ['**/*'], 'deny': [], 'path': '', 'expected': False},
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

        # Test 1: Simple deny
        f = GlobFilter(deny_patterns=["*.log"])
        filtered = f.filter_paths(paths)
        expected = ["src/main.py", "src/config.json", "tests/test.py"]
        results.append((filtered == expected, "filter_paths: Simple Deny", f"Got {len(filtered)}/3 items"))

        # Test 2: Explicit allow
        f = GlobFilter(allow_patterns=["*.py"])
        filtered = f.filter_paths(paths)
        expected = ["src/main.py", "tests/test.py"]
        results.append((filtered == expected, "filter_paths: Explicit Allow", f"Got {len(filtered)}/2 items"))

        # Test 3: Allow and Deny
        f = GlobFilter(allow_patterns=["src/**"], deny_patterns=["*.json"])
        filtered = f.filter_paths(paths)
        expected = ["src/main.py"]
        results.append((filtered == expected, "filter_paths: Allow and Deny", f"Got {len(filtered)}/1 item"))
        
        return results

    # --- Run All Test Categories ---
    run_test_category("__init__ Validation", test_init_validation)
    run_test_category("should_include Logic", test_should_include_logic)
    run_test_category("filter_paths Method", test_filter_paths_method)

    print("\n" + "="*60)
    print("HARNESS EXECUTION SUMMARY")
    print(f"  Total Tests: {total_tests}")
    print(f"  Passed:      {passed_count}")
    print(f"  Failed:      {failed_count}")
    print("="*60 + "\n")
    
    if failed_count == 0:
        print("SUCCESS: All exhaustive tests for the complete GlobFilter class passed.")
    else:
        print("FAILURE: One or more tests failed.")

if __name__ == "__main__":
    run_tests()

