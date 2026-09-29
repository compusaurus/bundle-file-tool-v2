"""Runtime access to the package-owned Bundle File Tool version.

BFT_B103_PACKAGE_VERSION - Build 103 payload owns the installed version
(ratified D-004: the delivery payload owns it; the stager never increments it).
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


PACKAGE_NAME = "bundle-file-tool"
FALLBACK_VERSION = "2.1.136"
SOURCE_VERSION_FILE = Path(__file__).resolve().parents[2] / "VERSION.txt"


def get_version() -> str:
    """Return the package-owned source identity, installed metadata, or fallback.

    Delivery kits run directly from ``src`` and own ``VERSION.txt``. Prefer
    that identity so stale developer-generated ``*.egg-info`` metadata cannot
    make a newly installed source tree report the previous build.
    """
    try:
        source_version = SOURCE_VERSION_FILE.read_text(encoding="utf-8").strip()
        if source_version:
            return source_version
    except OSError:
        pass

    try:
        return version(PACKAGE_NAME)
    except PackageNotFoundError:
        return FALLBACK_VERSION


__version__ = get_version()
