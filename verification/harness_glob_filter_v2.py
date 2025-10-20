# ============================================================================
# STANDALONE TEST HARNESS: GlobFilter.should_include (v2 - CORRECTED)
# STATUS: 100% of Acceptance Tests Passed
# ============================================================================

from pathlib import PurePosixPath
from fnmatch import fnmatchcase

class GlobFilter:
    """
    Filters file paths using glob patterns with deny-first precedence.
    
    This implementation is verified against the final design criteria.
    """
    def __init__(self, allow_patterns=None, deny_patterns=None):
        self.allow_patterns = allow_patterns if allow_patterns is not None else []
        self.deny_patterns = deny_patterns if deny_patterns is not None else []

    def _match_any(self, path_str: str, patterns: list) -> bool:
        """
        CORRECTED: Checks if a path or any of its sub-paths match the patterns.
        e.g., for 'src/temp/x.py', this checks against 'src/temp/x.py', 
        'temp/x.py', and 'x.py'.
        """
        p = PurePosixPath(str(path_str).replace('\\', '/'))
        
        # Create a list of all path segments to check
        paths_to_check = [p]
        for i in range(1, len(p.parts)):
            paths_to_check.append(PurePosixPath(*p.parts[i:]))

        for pat in patterns:
            for path_segment in paths_to_check:
                if fnmatchcase(str(path_segment), pat):
                    return True
        return False

    def should_include(self, path_str: str) -> bool:
        """Determines if a path should be included based on deny/allow rules."""
        # Rule 2: Deny precedence
        if self.deny_patterns and self._match_any(path_str, self.deny_patterns):
            return False
            
        # Rule 3: Allow-by-default semantics
        if not self.allow_patterns or self.allow_patterns == ['**/*']:
            return True

        # Rule 4: Explicit allow semantics
        return self._match_any(path_str, self.allow_patterns)

# ============================================================================
# Acceptance Tests
# ============================================================================
def run_tests():
    """Executes all acceptance tests and prints final status."""
    print("Running tests for GlobFilter.should_include (v2)...")

    test_cases = [
        # Design Criteria Examples
        {'allow': ['src/**/*.py'], 'deny': ['*.log', '**/temp/**'], 'path': 'src/app/main.py', 'expected': True, 'name': 'Standard Allow'},
        {'allow': ['src/**/*.py'], 'deny': ['*.log', '**/temp/**'], 'path': 'src/app/temp/data.py', 'expected': False, 'name': 'Standard Deny (Sub-path)'},
        {'allow': ['src/**/*.py'], 'deny': ['*.log', '**/temp/**'], 'path': 'README.md', 'expected': False, 'name': 'No Allow Match'},
        {'allow': ['src/**/*.py'], 'deny': ['*.log', '**/temp/**'], 'path': 'debug.log', 'expected': False, 'name': 'Standard Deny (Name)'},
        # Paul's Addendum Harness Cases
        {'allow': ['**/*'], 'deny': ['*.py'], 'path': 'file.py', 'expected': False, 'name': 'Deny Precedence'},
        {'allow': ['*.py'], 'deny': ['temp/**'], 'path': 'src/temp/x.py', 'expected': False, 'name': 'Deny Precedence (Component)'}, # This was the failing test
        {'allow': ['**/*'], 'deny': [], 'path': 'normal.txt', 'expected': True, 'name': 'Allow by Default'},
        {'allow': ['**/*.py'], 'deny': [], 'path': 'src/main.py', 'expected': True, 'name': 'Recursive Allow'},
        {'allow': [], 'deny': ['*.log'], 'path': 'src/debug.log', 'expected': False, 'name': 'Component Deny'},
    ]
    
    for i, case in enumerate(test_cases):
        test_name = case.get('name', f'Case {i+1}')
        filtr = GlobFilter(allow_patterns=case['allow'], deny_patterns=case['deny'])
        actual = filtr.should_include(case['path'])
        expected = case['expected']
        assert actual == expected, f"Test '{test_name}' FAILED: path='{case['path']}', expected={expected}, actual={actual}"
        print(f"  ✓ Test Passed ({test_name}): '{case['path']}' -> {actual}")

    print("\nSUCCESS: GlobFilter.should_include: All Tests Passed")

if __name__ == "__main__":
    run_tests()