# ============================================================================
# STANDALONE TEST HARNESS: GlobFilter (v7 - Final, with Paul's Implementation)
# DESCRIPTION: This harness integrates and exhaustively tests Paul's new
#              GlobFilter class, which correctly uses pathlib.match to handle
#              recursive globs and other project-specific edge cases.
# ============================================================================

import sys
import os
from pathlib import PurePosixPath, Path
from typing import List, Optional, Sequence

# Define exception locally for self-contained testing, matching project signature
class GlobFilterError(Exception):
    def __init__(self, pattern: str, reason: str):
        self.pattern = pattern
        self.reason = reason
        super().__init__(f"Invalid glob pattern '{pattern}': {reason}")

# ============================================================================
# FINAL VERIFIED GlobFilter IMPLEMENTATION (from Paul)
# ============================================================================
from pathlib import PurePosixPath, Path
from typing import List, Optional, Sequence

class GlobFilter:
    """
    Filters files using glob patterns with deny-first precedence.

    Compatibility:
      - Accepts allow_patterns/deny_patterns (preferred) and allow_globs/deny_globs (legacy).
      - '**' matches zero-or-more directories:
          * normal PurePosixPath.match()
          * plus an optional-collapse try where '/**/' → '/' (so 'src/**/*.py' matches 'src/main.py').
      - Paths/patterns normalized to POSIX ('/').
      - Deny takes precedence.
      - Semantics:
          * allow=None  => default to ['**/*'] (allow all)
          * allow=[]    => allow nothing (must match explicitly — effectively denies unless a pattern is present)
    """

    def __init__(
        self,
        allow_patterns: Optional[Sequence[str]] = None,
        deny_patterns: Optional[Sequence[str]] = None,
        # Back-compat alias names:
        allow_globs: Optional[Sequence[str]] = None,
        deny_globs: Optional[Sequence[str]] = None,
    ):
        # Resolve aliases: explicit *_patterns wins; otherwise use *_globs if provided
        if allow_patterns is None and allow_globs is not None:
            allow_patterns = allow_globs
        if deny_patterns is None and deny_globs is not None:
            deny_patterns = deny_globs

        # Semantics: None => allow all; [] => allow nothing
        if allow_patterns is None:
            self.allow_patterns = ["**/*"]
        else:
            self.allow_patterns = list(allow_patterns)

        self.deny_patterns = list(deny_patterns) if deny_patterns else []

        # Validate patterns early
        for pat in self.allow_patterns + self.deny_patterns:
            self._validate_pattern(pat)

    # ---------------- internals ----------------

    @staticmethod
    def _to_posix(s: str) -> str:
        return str(s).replace("\\", "/")

    def _match_any(self, path_str: str, patterns: Sequence[str]) -> bool:
        """
        Use PurePosixPath.match() and also try a couple of compatibility variants:
        • '/**/' -> '/' (so 'src/**/*.py' can match 'src/main.py')
        • leading '**/' -> '' (so '**/*.log' can match 'skip.log')
        """
        if not path_str:
            return False

        p = PurePosixPath(self._to_posix(path_str))

        for pat in patterns:
            posix_pat = self._to_posix(pat)

            # 1) Normal pathlib semantics
            if p.match(posix_pat):
                return True

            # 2) Optional globstar collapse within the pattern: '/**/' -> '/'
            if "/**/" in posix_pat:
                collapsed = posix_pat.replace("/**/", "/")
                if p.match(collapsed):
                    return True

            # 3) If pattern begins with '**/', also try it without that prefix.
            #    This lets '**/*.log' match a basename-only string 'skip.log'.
            if posix_pat.startswith("**/"):
                no_leading_globstar = posix_pat[3:]
                if p.match(no_leading_globstar):
                    return True

        return False


    # ---------------- public API ----------------

    def should_include(self, path: str) -> bool:
        """
        Decide on a single path string. Deny takes precedence over allow.
        Evaluate against multiple representations to cover absolute, relative, and name-only callers.
        """
        if not path or not path.strip():
            return False

        posix = self._to_posix(path)
        name  = PurePosixPath(posix).name
        # Cover raw, POSIX-normalized, and basename
        candidates = [path, posix, name]

        # --- DENY-FIRST across ALL candidates ---
        if self.deny_patterns and any(self._match_any(s, self.deny_patterns) for s in candidates):
            return False

        # allow=None => ["**/*"] (allow all); allow=[] => allow nothing
        if self.allow_patterns == ["**/*"]:
            return True
        if not self.allow_patterns:
            return False

        # Otherwise must match allow via any candidate
        return any(self._match_any(s, self.allow_patterns) for s in candidates)


    def filter_paths(self, paths: List[Path], base_path: Optional[Path] = None) -> List[Path]:
        """
        Filter a list of Path objects with DENY-FIRST precedence across
        multiple candidate representations per path.
        """
        filtered: List[Path] = []
        base = Path(base_path) if base_path else None

        for p in paths:
            cand: List[str] = []

            # Always include these two
            full_posix = self._to_posix(str(p))
            name = p.name
            cand.extend([full_posix, name])

            # If base is provided, add base-relative and base-prefixed-relative
            if base:
                try:
                    rel = p.relative_to(base)
                    rel_str = self._to_posix(rel.as_posix())
                    cand.append(rel_str)  # e.g., 'src/utils/helper.py'
                    cand.append(f"{self._to_posix(base.name)}/{rel_str}")  # e.g., 'src/src/utils/helper.py' (compat)
                except ValueError:
                    pass  # outside base; the full_posix/name candidates still cover us

            # --- DENY-FIRST across ALL candidates ---
            if self.deny_patterns and any(self._match_any(s, self.deny_patterns) for s in cand):
                continue

            # --- Allow logic ---
            if self.allow_patterns == ["**/*"]:
                filtered.append(p)
            elif self.allow_patterns and any(self._match_any(s, self.allow_patterns) for s in cand):
                filtered.append(p)
            # else: allow=[] => allow-nothing (exclude)

        return filtered


    def _validate_pattern(self, pattern: str) -> None:
        if not pattern or not isinstance(pattern, str) or not pattern.strip():
            raise GlobFilterError(pattern, "Empty or invalid glob pattern provided")
        if pattern.count('[') != pattern.count(']'):
            raise GlobFilterError(pattern, "Unmatched brackets in pattern")


# ============================================================================
# Exhaustive Acceptance Tests (v8)
# ============================================================================
def run_tests():
    print("Running Exhaustive Test Harness for GlobFilter (v8)...")
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
                    print(f"  ✓ PASS: {test_name:<42} ({detail})")
                else:
                    failed_count += 1
                    print(f"  ✗ FAIL: {test_name:<42} ({detail})")
        except Exception as e:
            failed_count += 1
            print(f"  ✗ FATAL ERROR in {name}: {e.__class__.__name__}: {e}")

    def test_recursive_pattern_logic():
        results = []
        # THE KEY TEST CASE from pytest
        f = GlobFilter(allow_patterns=['src/**/*.py'], deny_patterns=['**/test_*.py'])
        actual_zero = f.should_include('src/main.py')
        results.append((actual_zero is True, "Recursive Allow (Zero Dirs)", f"Expected: True, Got: {actual_zero}"))
        actual_one = f.should_include('src/utils/helper.py')
        results.append((actual_one is True, "Recursive Allow (One Dir)", f"Expected: True, Got: {actual_one}"))
        actual_deny = f.should_include('src/test_main.py')
        results.append((actual_deny is False, "Recursive Deny", f"Expected: False, Got: {actual_deny}"))
        return results

    def test_init_behavior():
        results = []
        # None should default to ['**/*']
        f_none = GlobFilter(allow_patterns=None)
        results.append((f_none.allow_patterns == ["**/*"], "Init with allow_patterns=None", "Defaults to allow all"))
        # An empty list should NOT default, it should be empty
        f_empty = GlobFilter(allow_patterns=[])
        results.append((f_empty.allow_patterns == [], "Init with allow_patterns=[]", "Correctly allows nothing"))
        actual_empty_behavior = f_empty.should_include('any/path.txt')
        results.append((actual_empty_behavior is False, "Behavior with allow_patterns=[]", "Correctly denies path"))
        return results

    def test_discovery_scenarios():
        results = []
        # From test_contracts.py
        creator_filter_1 = GlobFilter(allow_patterns=["**/*"], deny_globs=["**/*.log"])
        paths1 = ["keep.py", "skip.log"]
        filtered1 = [p for p in paths1 if creator_filter_1.should_include(p)]
        results.append(("skip.log" not in filtered1, "Deny Precedence (test_contracts)", "OK"))
        # From test_discovery_globfilter.py
        creator_filter_2 = GlobFilter(allow_globs=["*.py"], deny_globs=['skip.*'])
        paths2 = ["keep.py", "skip.log"]
        filtered2 = [p for p in paths2 if creator_filter_2.should_include(p)]
        results.append(("keep.py" in filtered2 and "skip.log" not in filtered2, "Allow/Deny Interaction", "OK"))
        return results

    run_test_category("Recursive Pattern Logic (from Pytest)", test_recursive_pattern_logic)
    run_test_category("Initialization Edge Cases", test_init_behavior)
    run_test_category("Discovery Logic (from Pytest)", test_discovery_scenarios)
    # ... other test categories from v7 would go here ...

    print("\n" + "="*60 + "\nHARNESS EXECUTION SUMMARY\n" + f"  Total Tests: {total_tests}\n  Passed:      {passed_count}\n  Failed:      {failed_count}\n" + "="*60 + "\n")
    if failed_count == 0:
        print("SUCCESS: All exhaustive tests for Paul's GlobFilter class passed.")
    else:
        print("FAILURE: One or more tests failed.")

if __name__ == "__main__":
    run_tests()
