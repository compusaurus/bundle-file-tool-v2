import sys
from pathlib import Path
import pytest

# Robust to both import styles (src.core.* and core.*)
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_DIR = _REPO_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))
try:
    from src.core.parser import BundleParser, ProfileDetectionError  # type: ignore
except ModuleNotFoundError:
    from core.parser import BundleParser, ProfileDetectionError

PLAIN = (
    "# ====================================================================\n"
    "# FILE: file.txt\n"
    "# META: encoding=utf-8; eol=LF; mode=text\n"
    "# ====================================================================\n"
    "content\n"
)

def test_detect_profile_name_extremely_short_snippet():
    p = BundleParser()
    with pytest.raises(ProfileDetectionError):
        p.detect_profile_name("# F")

def test_detect_profile_name_very_long_snippet():
    p = BundleParser()
    long_text = PLAIN + ("\n" * 2048)
    assert p.detect_profile_name(long_text) == "plain_marker"

def test_validate_bundle_benign_meta_variants_still_valid():
    p = BundleParser()
    text = PLAIN.replace("mode=text", "mode=text; unknown_key=foo;;")
    report = p.validate_bundle(text)
    assert report.get("valid") is True
    assert report.get("errors") in ([], None)

def test_validate_bundle_reports_errors_for_clearly_invalid_bundle():
    p = BundleParser()
    bad = "this is not a bundle format at all\n(no markers)\n"
    report = p.validate_bundle(bad)
    assert report.get("valid") is False
    assert report.get("errors"), "Expected errors for invalid input"

def test_detect_profile_name_unknown_profile_raises():
    p = BundleParser()
    with pytest.raises(ProfileDetectionError):
        p.detect_profile_name("This is not a bundle\nAnd has no markers\n")
