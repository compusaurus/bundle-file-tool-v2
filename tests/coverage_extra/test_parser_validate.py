import sys
from pathlib import Path

# Robust to both import styles (src.core.* and core.*)
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_DIR = _REPO_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

try:
    from src.core.parser import BundleParser, ProfileDetectionError  # type: ignore
except ModuleNotFoundError:
    from core.parser import BundleParser, ProfileDetectionError

import pytest

PLAIN = (
    "# ====================================================================\n"
    "# FILE: file.txt\n"
    "# META: encoding=utf-8; eol=LF; mode=text\n"
    "# ====================================================================\n"
    "content\n"
)


def test_detect_profile_name_success():
    p = BundleParser()
    assert p.detect_profile_name(PLAIN) == "plain_marker"


def test_detect_profile_name_failure_raises():
    p = BundleParser()
    with pytest.raises(ProfileDetectionError):
        p.detect_profile_name("no markers here")


def test_validate_bundle_report_shape():
    p = BundleParser()
    report = p.validate_bundle(PLAIN)
    keys = set(report.keys())
    assert {"valid", "profile", "file_count"} <= keys
    assert "errors" in keys or "warnings" in keys
