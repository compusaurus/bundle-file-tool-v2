"""Archive the verified source delivery with POSIX executable permissions."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import tarfile

from install_linux import verify_payload


def build(source: Path, output: Path, platform: str = "linux") -> Path:
    files = verify_payload(source)
    version = (source / "VERSION.txt").read_text().strip()
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f"bundle-file-tool-{version}-{platform}.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        for relative in [*files, Path("_delivery/delivery_manifest.sha256")]:
            path = source / relative
            info = tar.gettarinfo(str(path), arcname=f"bundle-file-tool-{version}/{relative.as_posix()}")
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            executable = path.suffix in {".sh", ".command"} or "MacOS" in relative.parts
            info.mode = 0o755 if executable else 0o644
            with path.open("rb") as stream:
                tar.addfile(info, stream)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_name(archive.name + ".sha256").write_text(
        f"{digest}  {archive.name}\n", encoding="ascii")
    print(archive.resolve())
    print(f"SHA256 {digest}")
    return archive


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, default=Path("dist"))
    parser.add_argument("--platform", choices=("linux", "macos"), default="linux")
    args = parser.parse_args()
    build(args.source.resolve(), args.output.resolve(), args.platform)
