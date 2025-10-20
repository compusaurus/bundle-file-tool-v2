# ============================================================================
# STANDALONE TEST HARNESS: Binary File Detection (_read_file_to_entry)
# FILE: verification/harness_binary_detection.py (v2 - Platform Fix)
# STATUS: 100% of Acceptance Tests Passed
# ============================================================================

import base64
import os
import tempfile
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

# To maintain isolation, we define simplified local versions of project classes.
# This ensures the harness has zero dependencies on the main codebase.

@dataclass
class LocalBundleEntry:
    """A simplified, local version of the BundleEntry model."""
    path: str
    content: str
    is_binary: bool
    encoding: str
    eol_style: str
    file_size_bytes: Optional[int] = None

class LocalBundleWriteError(Exception):
    """A simplified, local version of the BundleWriteError exception."""
    def __init__(self, path, message):
        super().__init__(f"Failed on '{path}': {message}")

# ============================================================================
# VERIFIED FUNCTIONS
# ============================================================================

def _detect_eol(text: str) -> str:
    """Detects end-of-line style from a string."""
    if "\r\n" in text:
        return "CRLF"
    elif "\n" in text:
        return "LF"
    elif "\r" in text:
        return "CR"
    return "LF" # Default for single-line or empty files

def _read_file_to_entry(file_path: Path, relative_path: str, treat_binary_as_base64: bool = True) -> LocalBundleEntry:
    """
    Reads a file and creates a BundleEntry, using a robust heuristic
    to detect if the file is binary before reading its full content.
    """
    try:
        # Heuristic: Read the first 1024 bytes to detect binary content.
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
            # Null bytes are a strong indicator of a binary file.
            if b'\x00' in chunk:
                is_binary = True
            else:
                # If no null bytes, try decoding as utf-8 as a final check.
                chunk.decode('utf-8')
                is_binary = False
    except (UnicodeDecodeError, TypeError):
        is_binary = True
    except Exception:
        # Fallback for empty files or other read issues.
        is_binary = False

    if is_binary:
        if not treat_binary_as_base64:
            raise LocalBundleWriteError(str(relative_path), "Binary file found but handling is disabled.")
        content_bytes = file_path.read_bytes()
        content = base64.b64encode(content_bytes).decode('ascii')
        encoding = "base64"
        eol_style = "n/a"
    else:
        # We now know it's safe to read as text.
        content = file_path.read_text(encoding='utf-8')
        encoding = "utf-8"
        eol_style = _detect_eol(content)

    return LocalBundleEntry(
        path=relative_path,
        content=content,
        is_binary=is_binary,
        encoding=encoding,
        eol_style=eol_style,
        file_size_bytes=file_path.stat().st_size
    )

# ============================================================================
# Acceptance Tests
# ============================================================================
def run_tests():
    """Creates test files and runs them through the verification logic."""
    print("Running tests for Binary File Detection (v2)...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        
        # 1. Create test files
        (p / "ascii.txt").write_text("Hello, world!")
        # CORRECTED LINE: Explicitly set encoding to utf-8 for cross-platform compatibility.
        (p / "utf8.txt").write_text("Hello, 世界!", encoding='utf-8')
        (p / "binary.png").write_bytes(b'\x89PNG\r\n\x1a\n')
        (p / "null_byte.bin").write_bytes(b'some\x00binary\x00data')
        (p / "empty.txt").touch()

        # 2. Define test cases
        test_cases = [
            {"file": "ascii.txt", "is_binary": False, "encoding": "utf-8"},
            {"file": "utf8.txt", "is_binary": False, "encoding": "utf-8"},
            {"file": "binary.png", "is_binary": True, "encoding": "base64"},
            {"file": "null_byte.bin", "is_binary": True, "encoding": "base64"},
            {"file": "empty.txt", "is_binary": False, "encoding": "utf-8"},
        ]

        # 3. Run tests
        for i, case in enumerate(test_cases):
            file_path = p / case["file"]
            entry = _read_file_to_entry(file_path, case["file"])

            assert entry.is_binary == case["is_binary"], f"Test {i+1} FAILED: is_binary for {case['file']}"
            assert entry.encoding == case["encoding"], f"Test {i+1} FAILED: encoding for {case['file']}"
            
            if entry.is_binary:
                original_bytes = file_path.read_bytes()
                decoded_bytes = base64.b64decode(entry.content)
                assert original_bytes == decoded_bytes, f"Test {i+1} FAILED: base64 content mismatch for {case['file']}"
            else:
                original_text = file_path.read_text(encoding='utf-8')
                assert original_text == entry.content, f"Test {i+1} FAILED: text content mismatch for {case['file']}"
            
            print(f"  ✓ Test {i+1} Passed: Correctly processed '{case['file']}'")

    print("\nSUCCESS: Binary File Detection: All Tests Passed")

if __name__ == "__main__":
    run_tests()