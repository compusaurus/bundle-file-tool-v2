"""Governed contract for BFT's vendored PyThermX baseline candidate."""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import zipfile
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[2]
WHEEL_NAME = "pythermx-0.5.3-py3-none-any.whl"
WHEEL_SHA256 = "fdf58d38c61a91f539aed37f846eb25b94f8aaa7d3cba401308c312e517f2690"


def test_exactly_the_governed_pythermx_wheel_is_vendored():
    wheels = sorted((ROOT / "vendor").glob("pythermx-*.whl"))
    assert [wheel.name for wheel in wheels] == [WHEEL_NAME]

    wheel = wheels[0]
    assert wheel.stat().st_size == 54_044
    assert hashlib.sha256(wheel.read_bytes()).hexdigest() == WHEEL_SHA256


def test_vendored_wheel_identity_and_record_are_self_consistent():
    wheel = ROOT / "vendor" / WHEEL_NAME
    record_name = "pythermx-0.5.3.dist-info/RECORD"

    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        assert "pythermx-0.5.3.dist-info/METADATA" in names
        assert "pythermx/profile.py" in names
        assert "pythermx/profiles/default.json" in names
        assert "pythermx/schemas/pythermx-profile-1.1.schema.json" in names

        metadata = archive.read("pythermx-0.5.3.dist-info/METADATA").decode("utf-8")
        metadata_lines = set(metadata.splitlines())
        assert "Name: pythermx" in metadata_lines
        assert "Version: 0.5.3" in metadata_lines
        assert "Requires-Python: <3.14,>=3.11" in metadata_lines

        rows = csv.reader(io.StringIO(archive.read(record_name).decode("utf-8")))
        for member, digest, size in rows:
            member_path = PurePosixPath(member)
            assert not member_path.is_absolute()
            assert ".." not in member_path.parts
            assert member in names
            if member == record_name:
                assert digest == ""
                assert size == ""
                continue

            algorithm, encoded = digest.split("=", 1)
            assert algorithm == "sha256"
            payload = archive.read(member)
            actual = base64.urlsafe_b64encode(hashlib.sha256(payload).digest()).rstrip(b"=")
            assert actual.decode("ascii") == encoded
            assert len(payload) == int(size)


def test_dependency_and_installer_select_the_same_candidate():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    installers = sorted(ROOT.glob("INSTALL_BUNDLETOOL_*.bat"))
    assert installers, "no governed BFT installer is present"
    installer = installers[-1].read_text(encoding="utf-8")

    assert '"pythermx>=0.5.3,<0.6"' in pyproject
    assert WHEEL_NAME in installer
    assert "expected PyThermX 0.5.3" in installer
    assert "pythermx-0.5.0-py3-none-any.whl" not in installer
