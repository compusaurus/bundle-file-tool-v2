"""
Diagnostic script to identify where duplicate paths are created.
Run this from bundle_file_tool_v2/verification/ directory.
Location: bundle_file_tool_v2/verification/manifest_diagnostic.py
"""
import sys
from pathlib import Path
from collections import Counter

# Add src to path
# This script is in: bundle_file_tool_v2/verification/
# We need to add:   bundle_file_tool_v2/src/
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent  # Go up one level to bundle_file_tool_v2
src_path = project_root / 'src'

print(f"Script location: {script_dir}")
print(f"Project root: {project_root}")
print(f"Src path: {src_path}")
print(f"Src exists: {src_path.exists()}\n")

sys.path.insert(0, str(src_path))

from core.writer import BundleCreator

def diagnose_duplicate_paths(source_dir: Path):
    """
    Diagnose where duplicate paths are being created.
    """
    print("=" * 70)
    print("DUPLICATE PATH DIAGNOSTIC")
    print("=" * 70)
    
    # Step 1: Discover files
    print(f"\n1. DISCOVERY PHASE")
    print(f"   Source directory: {source_dir}")
    print(f"   Absolute: {source_dir.resolve()}")
    
    creator = BundleCreator()
    discovered_files = creator.discover_files(source_dir)
    
    print(f"   ✓ Discovered {len(discovered_files)} files")
    print(f"   ✓ Unique absolute paths: {len(set(discovered_files))}")
    
    if len(discovered_files) != len(set(discovered_files)):
        print("   ⚠️  DUPLICATE ABSOLUTE PATHS FOUND IN DISCOVERY!")
        abs_counts = Counter(discovered_files)
        for path, count in abs_counts.items():
            if count > 1:
                print(f"      {path}: {count} times")
        return
    
    # Step 2: Simulate manifest creation with different base_paths
    print(f"\n2. RELATIVE PATH CALCULATION PHASE")
    
    # Test with source_dir as base
    print(f"\n   Test A: base_path = source_dir")
    test_relative_paths(discovered_files, source_dir)
    
    # Test with parent as base (common mistake)
    parent_dir = source_dir.parent
    print(f"\n   Test B: base_path = parent directory")
    print(f"            (parent: {parent_dir})")
    test_relative_paths(discovered_files, parent_dir)
    
    # Test with None (defaults to cwd)
    print(f"\n   Test C: base_path = None (uses file location)")
    test_relative_paths(discovered_files, None)
    
    # Step 3: Show actual file locations
    print(f"\n3. FILE LOCATION ANALYSIS")
    print(f"   First 10 discovered files:")
    for i, file_path in enumerate(discovered_files[:10], 1):
        print(f"   {i}. {file_path}")
    
    # Step 4: Check for files outside source_dir
    print(f"\n4. BOUNDS CHECK")
    source_resolved = source_dir.resolve()
    outside_files = []
    for file_path in discovered_files:
        try:
            file_path.resolve().relative_to(source_resolved)
        except ValueError:
            outside_files.append(file_path)
    
    if outside_files:
        print(f"   ⚠️  FOUND {len(outside_files)} FILES OUTSIDE SOURCE DIRECTORY!")
        print(f"      These shouldn't have been discovered:")
        for f in outside_files[:5]:
            print(f"      - {f}")
    else:
        print(f"   ✓ All files are within source directory")

def test_relative_paths(files: list, base_path: Path):
    """
    Test converting absolute paths to relative with given base.
    """
    if base_path:
        base_path = base_path.resolve()
    
    relative_paths = []
    failed_conversions = []
    
    for file_path in files:
        file_resolved = file_path.resolve()
        
        if base_path:
            try:
                rel_path = str(file_resolved.relative_to(base_path)).replace('\\', '/')
                relative_paths.append(rel_path)
            except ValueError as e:
                # Can't make relative
                failed_conversions.append((file_path, str(e)))
                relative_paths.append(file_path.name)  # Fallback to name
        else:
            relative_paths.append(file_path.name)
    
    # Check for duplicates
    path_counts = Counter(relative_paths)
    duplicates = {path: count for path, count in path_counts.items() if count > 1}
    
    print(f"      Total relative paths: {len(relative_paths)}")
    print(f"      Unique relative paths: {len(set(relative_paths))}")
    
    if duplicates:
        print(f"      ❌ DUPLICATES FOUND: {len(duplicates)} duplicate paths")
        print(f"      Showing first 5 duplicates:")
        for path, count in list(duplicates.items())[:5]:
            print(f"         '{path}': appears {count} times")
            # Show which absolute paths map to this relative path
            matching_files = [f for f, rp in zip(files, relative_paths) if rp == path]
            for mf in matching_files[:3]:
                print(f"            <- {mf}")
    else:
        print(f"      ✓ No duplicates")
    
    if failed_conversions:
        print(f"      ⚠️  {len(failed_conversions)} files couldn't be made relative")
        for fp, err in failed_conversions[:3]:
            print(f"         {fp}")

if __name__ == "__main__":
    # Use the actual project directory
    v2_project = Path(r"C:\Users\mpw\Python\bundle_file_project\bundle_file_tool_v2")
    
    if not v2_project.exists():
        print(f"ERROR: Directory not found: {v2_project}")
        print("Please update the path in this script to match your environment.")
        sys.exit(1)
    
    diagnose_duplicate_paths(v2_project)
    
    print("\n" + "=" * 70)
    print("DIAGNOSIS COMPLETE")
    print("=" * 70)
