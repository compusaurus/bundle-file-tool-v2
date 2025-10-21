import os
import sys
import tempfile
import shutil
from pathlib import Path
from typing import List, Set

# ============================================================================
# SETUP: Ensure the project's source code is importable
# ============================================================================
# This harness assumes it is located in a 'verification' directory
# at the root of the 'bundle_file_tool_v2' project.
try:
    project_root = Path(__file__).resolve().parent.parent
    src_path = project_root / 'src'
    if not src_path.exists():
        raise FileNotFoundError("Could not find 'src' directory.")
    sys.path.insert(0, str(src_path))

    from core.writer import BundleCreator
    print("✅ Successfully imported BundleCreator from project source.")

except (ImportError, FileNotFoundError) as e:
    print("\n---")
    print("🔥 FATAL ERROR: Could not import project code.")
    print("Please ensure the following directory structure is correct:")
    print("    bundle_file_tool_v2/ (your project root)")
    print("    ├── src/")
    print("    │   └── core/")
    print("    │       └── writer.py")
    print("    └── verification/  (this harness should be here)")
    print("        └── harness_discover_files.py")
    print(f"\nDetails: {e}")
    sys.exit(1)

# ============================================================================
# TEST ENVIRONMENT SETUP
# ============================================================================

def setup_test_directory(root: Path) -> None:
    """Creates a nested project structure to test discovery logic."""
    print(f"\nSetting up test directory at: {root}")
    
    # Structure mimics a legacy v1 project containing the new v2 project
    legacy_v1_path = root / "legacy_v1"
    new_v2_path = legacy_v1_path / "bundle_file_tool_v2"
    
    # Create v2 files
    (new_v2_path / "nested").mkdir(parents=True, exist_ok=True)
    (new_v2_path / "Makefile").write_text("v2 Makefile")
    (new_v2_path / "common_file.txt").write_text("v2 common file")
    (new_v2_path / "v2_only.py").write_text("v2 only")
    (new_v2_path / "nested" / "new_file.py").write_text("new file")
    
    # Create v1 files (legacy)
    (legacy_v1_path / "Makefile").write_text("v1 Makefile")
    (legacy_v1_path / "common_file.txt").write_text("v1 common file")
    (legacy_v1_path / "legacy_only.txt").write_text("legacy only")
    
    print("    - legacy_v1/Makefile")
    print("    - legacy_v1/common_file.txt")
    print("    - legacy_v1/legacy_only.txt")
    print("    - legacy_v1/bundle_file_tool_v2/Makefile")
    print("    - legacy_v1/bundle_file_tool_v2/common_file.txt")
    print("    - ... and other v2 files")

# ============================================================================
# TEST HARNESS LOGIC
# ============================================================================

class TestRunner:
    """Runs a series of tests against the discover_files function."""
    def __init__(self, test_dir: Path):
        self.test_dir = test_dir
        self.legacy_path = self.test_dir / "legacy_v1"
        self.v2_path = self.legacy_path / "bundle_file_tool_v2"
        self.failures = 0

    def run(self):
        """Execute all test cases."""
        print("\n--- Running Tests ---")
        self.test_1_standard_discovery()
        self.test_2_deny_globs()
        self.test_3_duplicate_detection_failure()
        print("--- Tests Finished ---")
        
        if self.failures == 0:
            print("\n✅🏆 All tests passed! The discover_files function is robust. 🏆✅")
        else:
            print(f"\n🔥🔥 {self.failures} test(s) failed. The discover_files function has bugs. 🔥🔥")
            print("Please see the recommended fix in the accompanying documentation.")

    def _assert(self, condition: bool, pass_msg: str, fail_msg: str):
        """Custom assertion to print formatted results."""
        if condition:
            print(f"    [PASS] {pass_msg}")
        else:
            print(f"    [FAIL] {fail_msg}")
            self.failures += 1
            
    def _get_relative_paths(self, files: List[Path], base: Path) -> Set[str]:
        """Helper to convert absolute paths to relative path strings."""
        return {str(p.relative_to(base)).replace('\\', '/') for p in files}

    def test_1_standard_discovery(self):
        """Tests standard discovery within the target directory."""
        print("\n[Test 1] Standard discovery from v2 sub-directory")
        creator = BundleCreator()
        
        # Discover files starting from the v2 directory
        discovered_files = creator.discover_files(self.v2_path)
        
        # Convert to relative paths for stable comparison
        relative_paths = self._get_relative_paths(discovered_files, self.v2_path)
        
        expected_paths = {
            "Makefile",
            "common_file.txt",
            "v2_only.py",
            "nested/new_file.py"
        }
        
        self._assert(len(relative_paths) == 4,
                     f"Correct file count found: {len(relative_paths)}",
                     f"Expected 4 files, but found {len(relative_paths)}")
        
        self._assert(relative_paths == expected_paths,
                     "Discovered file paths match expected paths.",
                     f"Path mismatch. Found: {relative_paths}")

    def test_2_deny_globs(self):
        """Tests that deny_globs correctly exclude files."""
        print("\n[Test 2] Deny globs correctly exclude files")
        creator = BundleCreator(deny_globs=["**/Makefile", "*.txt"])
        
        discovered_files = creator.discover_files(self.v2_path)
        relative_paths = self._get_relative_paths(discovered_files, self.v2_path)
        
        expected_paths = {
            "v2_only.py",
            "nested/new_file.py"
        }
        
        self._assert(len(relative_paths) == 2,
                     f"Correct file count found after filtering: {len(relative_paths)}",
                     f"Expected 2 files after filtering, but found {len(relative_paths)}")

        self._assert(relative_paths == expected_paths,
                     "Correctly excluded Makefile and .txt files.",
                     f"Incorrect files remained. Found: {relative_paths}")

    def test_3_duplicate_detection_failure(self):
        """
        THIS IS THE CRITICAL TEST.
        It simulates the condition causing duplicate files by scanning from the
        parent directory. A robust function should NOT find duplicates.
        """
        print("\n[Test 3] Scanning from parent directory (potential for duplicates)")
        creator = BundleCreator()
        
        # THIS IS THE SCENARIO THAT REVEALS THE BUG:
        # We scan from the parent ('legacy_v1') but the user is interested in the
        # contents relative to that folder.
        discovered_files = creator.discover_files(self.legacy_path)
        
        # A flawed function will find 7 files but might create duplicate relative paths
        # in the manifest later. A robust function returns a clean, unique list.
        # The true test is the number of unique files found.
        
        # Here we check for absolute path uniqueness.
        unique_absolute_paths = set(discovered_files)
        
        self._assert(len(discovered_files) == 7,
                     f"Found the correct total number of files: {len(discovered_files)}",
                     f"Expected to find 7 total files, but found {len(discovered_files)}")
        
        self._assert(len(unique_absolute_paths) == len(discovered_files),
                     "All discovered file paths are unique.",
                     "BUG CONFIRMED: Duplicate absolute paths were found in the discovery list.")


if __name__ == "__main__":
    # Create a temporary directory for the test
    temp_dir = Path(tempfile.gettempdir()) / f"bft_harness_{os.getpid()}"
    
    # Clean up previous runs if they exist
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
        
    try:
        # Set up the test environment
        temp_dir.mkdir(parents=True)
        setup_test_directory(temp_dir)
        
        # Run the tests
        runner = TestRunner(temp_dir)
        runner.run()
        
    finally:
        # Clean up the test directory
        print(f"\nCleaning up test directory: {temp_dir}")
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
