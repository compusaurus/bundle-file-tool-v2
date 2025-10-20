# ============================================================================
# FILE: conftest.py
# RELPATH: bundle_file_tool_v2/tests/conftest.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.0
# LIFECYCLE: Proposed
# DESCRIPTION: Pytest fixtures for Bundle File Tool v2.1 test suite
# ============================================================================

"""
Pytest configuration and shared fixtures.

This module provides reusable test fixtures for the Bundle File Tool v2.1
test suite, including sample data, mock objects, and test utilities.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from core.models import BundleEntry, BundleManifest
from core.profiles.plain_marker import PlainMarkerProfile


# ============================================================================
# Sample Data Fixtures
# ============================================================================

@pytest.fixture
def sample_text_entry():
    """Create a sample text file entry."""
    return BundleEntry(
        path="src/example.py",
        content='def greet(name: str) -> None:\n    print(f"Hello, {name}!")\n\nif __name__ == "__main__":\n    greet("World")\n',
        is_binary=False,
        encoding="utf-8",
        eol_style="LF",
        checksum=None
    )


@pytest.fixture
def sample_binary_entry():
    """Create a sample binary file entry (1x1 PNG)."""
    # 1x1 transparent PNG as base64
    png_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGOoPqELAAMyAXHORGq8AAAAAElFTkSuQmCC"
    return BundleEntry(
        path="assets/icon.png",
        content=png_base64,
        is_binary=True,
        encoding="base64",
        eol_style="n/a",
        checksum=None
    )


@pytest.fixture
def sample_html_entry():
    """Create a sample HTML file with UTF-8 BOM and CRLF."""
    content = '\ufeff<!doctype html>\r\n<html>\r\n  <head>\r\n    <meta charset="utf-8" />\r\n    <title>Sample</title>\r\n  </head>\r\n  <body>\r\n    <h1>Test</h1>\r\n  </body>\r\n</html>\r\n'
    return BundleEntry(
        path="templates/index.html",
        content=content,
        is_binary=False,
        encoding="utf-8-bom",
        eol_style="CRLF",
        checksum=None
    )


@pytest.fixture
def sample_windows1252_entry():
    """Create a sample file with Windows-1252 encoding and CRLF."""
    # Contains smart quotes, em-dash, euro symbol (Windows-1252 specific)
    content = 'Sample project \x96 v2.1 QA bundle.\r\nFeatures: smart quotes \x93like this\x94, em-dash\x97, and euro \x80 symbol.\r\n'
    return BundleEntry(
        path="README.md",
        content=content,
        is_binary=False,
        encoding="windows-1252",
        eol_style="CRLF",
        checksum=None
    )


@pytest.fixture
def sample_jpg_entry():
    """Create a sample JPEG binary entry."""
    # Minimal JPEG header + data as base64
    jpg_base64 = "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwDfooor4U8g/9k="
    return BundleEntry(
        path="assets/photo.jpg",
        content=jpg_base64,
        is_binary=True,
        encoding="base64",
        eol_style="n/a",
        checksum=None
    )


@pytest.fixture
def sample_manifest(sample_text_entry, sample_binary_entry, sample_html_entry):
    """Create a sample manifest with multiple entries."""
    return BundleManifest(
        entries=[sample_text_entry, sample_html_entry, sample_binary_entry],
        profile="plain_marker",
        metadata={"test": "fixture"}
    )


@pytest.fixture
def empty_manifest():
    """Create an empty manifest."""
    return BundleManifest(
        entries=[],
        profile="plain_marker"
    )


# ============================================================================
# Bundle Text Fixtures (Sample Files)
# ============================================================================

@pytest.fixture
def sample_plain_marker_bundle():
    """Return the content of sample_project_plain_marker.txt."""
    return """# ===================================================================
# FILE: src/example.py
# META: encoding=utf-8; eol=LF; mode=text
# ===================================================================
def greet(name: str) -> None:
    print(f"Hello, {name}!")

if __name__ == "__main__":
    greet("World")

# ===================================================================
# FILE: config/settings.json
# META: encoding=utf-8; eol=LF; mode=text
# ===================================================================
{
  "app_name": "sample_app",
  "debug": true,
  "max_items": 10
}

# ===================================================================
# FILE: assets/icon.png
# META: encoding=base64; eol=n/a; mode=binary
# ===================================================================
iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGOoPqELAAMyAXHORGq8AAAAAElFTkSuQmCC"""


@pytest.fixture
def sample_markdown_fence_bundle():
    """Return the content of sample_project_markdown_fence.txt."""
    return """<!-- FILE: src/example.py; encoding=utf-8; eol=LF; mode=text -->
```python
def greet(name: str) -> None:
    print(f"Hello, {name}!")

if __name__ == "__main__":
    greet("World")

```

<!-- FILE: config/settings.json; encoding=utf-8; eol=LF; mode=text -->
```json
{
  "app_name": "sample_app",
  "debug": true,
  "max_items": 10
}

```

<!-- FILE: assets/icon.png; encoding=base64; eol=n/a; mode=binary -->
```
iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGOoPqELAAMyAXHORGq8AAAAAElFTkSuQmCC
```"""


# ============================================================================
# Profile Fixtures
# ============================================================================

@pytest.fixture
def plain_marker_profile():
    """Create a PlainMarkerProfile instance."""
    return PlainMarkerProfile()


# ============================================================================
# Filesystem Fixtures
# ============================================================================

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test file operations."""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    # Cleanup
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def temp_config_file(temp_dir):
    """Create a temporary config file path."""
    config_path = temp_dir / "bundle_config.json"
    yield config_path
    # Cleanup handled by temp_dir fixture


@pytest.fixture
def sample_project_structure(temp_dir):
    """
    Create a sample project directory structure for testing bundling.
    
    Structure:
        src/
            main.py
            utils.py
        docs/
            README.md
        config/
            settings.json
        assets/
            logo.png (mock binary)
    """
    # Create directories
    (temp_dir / "src").mkdir()
    (temp_dir / "docs").mkdir()
    (temp_dir / "config").mkdir()
    (temp_dir / "assets").mkdir()
    
    # Create text files
    (temp_dir / "src" / "main.py").write_text("def main():\n    pass\n")
    (temp_dir / "src" / "utils.py").write_text("def helper():\n    return True\n")
    (temp_dir / "docs" / "README.md").write_text("# Project\n\nDescription here.\n")
    (temp_dir / "config" / "settings.json").write_text('{"key": "value"}\n')
    
    # Create mock binary file
    png_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGOoPqELAAMyAXHORGq8AAAAAElFTkSuQmCC"
    (temp_dir / "assets" / "logo.png").write_bytes(bytes.fromhex("89504e47"))  # PNG header
    
    yield temp_dir


# ============================================================================
# Config Fixtures
# ============================================================================

@pytest.fixture
def v115_config():
    """Return a v1.1.5 style configuration dictionary."""
    return {
        "input_dir": "",
        "output_dir": "",
        "log_dir": "logs",
        "buttons_position": "bottom",
        "show_info_panel": True,
        "info_panel_position": "middle",
        "relative_base_path": "",
        "first_launch": True,
        "add_headers": True,
    }


@pytest.fixture
def v21_config():
    """Return a v2.1 style configuration dictionary."""
    return {
        "global_settings": {
            "input_dir": "",
            "output_dir": "",
            "log_dir": "logs",
            "relative_base_path": "",
            "ui_layout": {
                "buttons_position": "bottom",
                "show_info_panel": True,
                "info_panel_position": "middle"
            }
        },
        "session": {
            "first_launch": True,
            "window_geometry": ""
        },
        "app_defaults": {
            "default_mode": "unbundle",
            "bundle_profile": "md_fence",
            "add_headers": True,
            "encoding": "auto",
            "eol": "auto",
            "overwrite_policy": "prompt",
            "dry_run_default": True,
            "treat_binary_as_base64": True
        },
        "safety": {
            "allow_globs": ["src/**", "docs/**"],
            "deny_globs": ["**/.venv/**", "**/__pycache__/**", "*.log"],
            "max_file_mb": 10
        }
    }


# ============================================================================
# Assertion Helpers
# ============================================================================

def assert_bundles_equivalent(manifest1: BundleManifest, manifest2: BundleManifest):
    """
    Assert that two manifests are equivalent (same files, same content).
    
    Useful for round-trip tests.
    """
    assert manifest1.get_file_count() == manifest2.get_file_count(), \
        "File counts differ"
    
    # Sort entries by path for comparison
    entries1 = sorted(manifest1.entries, key=lambda e: e.path)
    entries2 = sorted(manifest2.entries, key=lambda e: e.path)
    
    for e1, e2 in zip(entries1, entries2):
        assert e1.path == e2.path, f"Paths differ: {e1.path} vs {e2.path}"
        assert e1.content == e2.content, f"Content differs for {e1.path}"
        assert e1.is_binary == e2.is_binary, f"Binary flag differs for {e1.path}"
        assert e1.encoding == e2.encoding, f"Encoding differs for {e1.path}"
        assert e1.eol_style == e2.eol_style, f"EOL style differs for {e1.path}"


# ============================================================================
# LIFECYCLE STATUS: Proposed
# NEXT STEPS: Add more fixtures as needed for specific test scenarios
# DEPENDENCIES: core/models.py, core/profiles/plain_marker.py
# USAGE: Import fixtures in test files, pytest auto-discovers them
# ============================================================================
