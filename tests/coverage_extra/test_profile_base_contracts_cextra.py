import sys
from pathlib import Path
import pytest

# Robust to both import styles (src.core.* and core.*)
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_DIR = _REPO_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))
try:
    from src.core.profiles.base import ProfileBase  # type: ignore
    from src.core.models import BundleEntry, BundleManifest  # type: ignore
    from src.core.exceptions import ProfileFormatError  # type: ignore
except ModuleNotFoundError:
    from core.profiles.base import ProfileBase
    from core.models import BundleEntry, BundleManifest
    from core.exceptions import ProfileFormatError


class DummyNoBinary(ProfileBase):
    @property
    def profile_name(self) -> str:
        return "dummy_no_binary"

    def get_display_name(self):
        return "DummyNoBinary"

    def get_capabilities(self):
        return {
            "supports_binary": False,   # explicitly disallow binary
            "supports_checksums": False,
            "supports_metadata": True,
        }

    def detect_format(self, text: str) -> bool:
        return False

    def parse_stream(self, text: str):
        raise NotImplementedError("not implemented")

    def format_manifest(self, manifest: BundleManifest) -> str:
        raise NotImplementedError("not implemented")


def test_validate_manifest_rejects_binary_when_not_supported():
    entry = BundleEntry(
        path="bin.dat", content="AAEC", is_binary=True, encoding="utf-8", eol_style="n/a"
    )
    manifest = BundleManifest(entries=[entry], profile="dummy_no_binary")
    prof = DummyNoBinary()
    with pytest.raises(ProfileFormatError):
        prof.validate_manifest(manifest)


def test_abstract_methods_raise_not_implemented():
    prof = DummyNoBinary()
    with pytest.raises(NotImplementedError):
        prof.parse_stream("data")
    with pytest.raises(NotImplementedError):
        prof.format_manifest(BundleManifest(entries=[], profile="dummy_no_binary"))
