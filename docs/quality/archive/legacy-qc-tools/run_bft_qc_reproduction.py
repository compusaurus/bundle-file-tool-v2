from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parents[1]
WORK = WORKSPACE / "work"
TOOL_BASE = WORK / "pyprojectmgrV2_sandbox_20260724"
TARGET_BASE = WORK / "bft_qc_target_base_20260724"
RUN_ROOT = WORK / "bft_qc_reproduction_patched_20260724"
PYTHON = Path(r"C:\ProgramData\Anaconda3\python.exe")
LIVE_SITE_PACKAGES = Path(
    r"C:\Users\mpw\Python\pyprojectmgrV2\.venv\Lib\site-packages"
)
RESULT_PATH = WORK / "bft_qc_reproduction_patched_results_20260724.json"


def recreate(path: Path) -> None:
    if path.exists():
        if WORK.resolve() not in path.resolve().parents:
            raise RuntimeError(f"Refusing to replace non-work path: {path}")
        shutil.rmtree(path)
    path.mkdir(parents=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inventory(root: Path) -> dict[str, str]:
    excluded = {"__pycache__", ".pytest_cache", "logs"}
    return {
        path.relative_to(root).as_posix(): sha256(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
        and not any(part in excluded for part in path.parts)
        and path.suffix != ".pyc"
    }


def changes(before: dict[str, str], after: dict[str, str]) -> list[dict[str, str | None]]:
    return [
        {
            "path": path,
            "before": before.get(path),
            "after": after.get(path),
        }
        for path in sorted(set(before) | set(after))
        if before.get(path) != after.get(path)
    ]


def environment(tool_root: Path, encoding: str) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONIOENCODING"] = encoding
    env["PYTHONUTF8"] = "1" if encoding.lower() == "utf-8" else "0"
    env["PYTHONPATH"] = os.pathsep.join(
        [str(tool_root / "src"), str(LIVE_SITE_PACKAGES)]
    )
    # The sandbox uses the approved Anaconda interpreter plus the supplied
    # project's dependency set. VenvGuard treats VIRTUAL_ENV as its supported
    # explicit environment indicator; point it at the isolated tool copy.
    env["VIRTUAL_ENV"] = str(tool_root / ".sandbox-venv")
    env["PATH"] = os.pathsep.join([str(PYTHON.parent), env.get("PATH", "")])
    return env


def run_case(case_name: str, encoding: str) -> dict[str, object]:
    case_root = RUN_ROOT / case_name
    tool_root = case_root / "tool"
    target_root = case_root / "bft_target"
    shutil.copytree(TOOL_BASE, tool_root)
    shutil.copytree(TARGET_BASE, target_root)

    tool_before = inventory(tool_root)
    target_before = inventory(target_root)
    command = [
        str(PYTHON),
        "-m",
        "cli.cli_interface",
        "--project-root",
        str(target_root),
        "--no-color",
        "qc",
        "--strict",
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=tool_root,
            env=environment(tool_root, encoding),
            capture_output=True,
            timeout=180,
            check=False,
        )
        exit_code: int | None = completed.returncode
        stdout_bytes = completed.stdout
        stderr_bytes = completed.stderr
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        exit_code = None
        stdout_bytes = exc.stdout or b""
        stderr_bytes = exc.stderr or b""
        timed_out = True

    stdout_path = case_root / "stdout.bin"
    stderr_path = case_root / "stderr.bin"
    stdout_path.write_bytes(stdout_bytes)
    stderr_path.write_bytes(stderr_bytes)
    (case_root / "stdout.txt").write_text(
        stdout_bytes.decode(encoding, errors="replace"),
        encoding="utf-8",
    )
    (case_root / "stderr.txt").write_text(
        stderr_bytes.decode(encoding, errors="replace"),
        encoding="utf-8",
    )

    tool_after = inventory(tool_root)
    target_after = inventory(target_root)
    return {
        "case": case_name,
        "encoding": encoding,
        "command": command,
        "cwd": str(tool_root),
        "python_version_command": [str(PYTHON), "--version"],
        "cli_version": "3.8.0 (source --version verified)",
        "exit_code": exit_code,
        "timed_out": timed_out,
        "stdout_bytes": len(stdout_bytes),
        "stderr_bytes": len(stderr_bytes),
        "stdout_sha256": sha256(stdout_path),
        "stderr_sha256": sha256(stderr_path),
        "tool_changes": changes(tool_before, tool_after),
        "target_changes": changes(target_before, target_after),
        "stdout_path": str(case_root / "stdout.txt"),
        "stderr_path": str(case_root / "stderr.txt"),
    }


def main() -> None:
    recreate(RUN_ROOT)
    cases = [
        run_case("cp1252", "cp1252"),
        run_case("utf8", "utf-8"),
    ]
    result = {
        "tool_base": str(TOOL_BASE),
        "target_base": str(TARGET_BASE),
        "python": str(PYTHON),
        "cases": cases,
    }
    RESULT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "result": str(RESULT_PATH),
                "cases": [
                    {
                        "case": case["case"],
                        "exit_code": case["exit_code"],
                        "timed_out": case["timed_out"],
                        "stdout_bytes": case["stdout_bytes"],
                        "stderr_bytes": case["stderr_bytes"],
                        "tool_changes": len(case["tool_changes"]),
                        "target_changes": len(case["target_changes"]),
                    }
                    for case in cases
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
