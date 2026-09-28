from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parents[1]
WORK = WORKSPACE / "work"
TOOL_BASE = WORK / "pyprojectmgrV2_sandbox_20260724"
TARGET_BASE = WORK / "bft_qc_target_base_20260724"
RUN_ROOT = WORK / "bft_clean_db_scan_then_qc_patched_20260724"
PYTHON = Path(r"C:\ProgramData\Anaconda3\python.exe")
LIVE_SITE_PACKAGES = Path(
    r"C:\Users\mpw\Python\pyprojectmgrV2\.venv\Lib\site-packages"
)
RESULT_PATH = WORK / "bft_clean_db_scan_then_qc_patched_results_20260724.json"


def recreate(path: Path) -> None:
    if path.exists():
        if WORK.resolve() not in path.resolve().parents:
            raise RuntimeError(f"Refusing to replace non-work path: {path}")
        shutil.rmtree(path)
    path.mkdir(parents=True)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(root: Path) -> dict[str, str]:
    excluded = {"__pycache__", ".pytest_cache", "logs"}
    return {
        path.relative_to(root).as_posix(): digest(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
        and path.suffix != ".pyc"
        and not any(part in excluded for part in path.parts)
    }


def diff(before: dict[str, str], after: dict[str, str]) -> list[str]:
    return sorted(
        path
        for path in set(before) | set(after)
        if before.get(path) != after.get(path)
    )


def env(tool_root: Path) -> dict[str, str]:
    result = os.environ.copy()
    result["PYTHONDONTWRITEBYTECODE"] = "1"
    result["PYTHONIOENCODING"] = "utf-8"
    result["PYTHONUTF8"] = "1"
    result["VIRTUAL_ENV"] = str(tool_root / ".sandbox-venv")
    result["PYTHONPATH"] = os.pathsep.join(
        [str(tool_root / "src"), str(LIVE_SITE_PACKAGES)]
    )
    result["PATH"] = os.pathsep.join([str(PYTHON.parent), result.get("PATH", "")])
    return result


def run(args: list[str], cwd: Path, environment: dict[str, str], prefix: str) -> dict[str, object]:
    completed = subprocess.run(
        args,
        cwd=cwd,
        env=environment,
        capture_output=True,
        timeout=240,
        check=False,
    )
    stdout_path = RUN_ROOT / f"{prefix}_stdout.txt"
    stderr_path = RUN_ROOT / f"{prefix}_stderr.txt"
    stdout_path.write_text(completed.stdout.decode("utf-8", errors="replace"), encoding="utf-8")
    stderr_path.write_text(completed.stderr.decode("utf-8", errors="replace"), encoding="utf-8")
    return {
        "command": args,
        "exit_code": completed.returncode,
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
    }


def db_summary(path: Path) -> dict[str, object]:
    connection = sqlite3.connect(path)
    tables = [
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
    ]
    if "assets" not in tables:
        connection.close()
        return {"asset_count": None, "tables": tables, "assets_table_missing": True}
    columns = [row[1] for row in connection.execute("PRAGMA table_info(assets)")]
    count = connection.execute("SELECT COUNT(*) FROM assets").fetchone()[0]
    status_counts = connection.execute(
        "SELECT status, COUNT(*) FROM assets GROUP BY status ORDER BY status"
    ).fetchall()
    path_sample = connection.execute(
        "SELECT file_path FROM assets ORDER BY asset_id LIMIT 5"
    ).fetchall()
    connection.close()
    return {
        "asset_count": count,
        "columns": columns,
        "status_counts": status_counts,
        "file_path_sample": [row[0] for row in path_sample],
    }


def main() -> None:
    recreate(RUN_ROOT)
    tool_root = RUN_ROOT / "tool"
    target_root = RUN_ROOT / "bft_target"
    shutil.copytree(TOOL_BASE, tool_root)
    shutil.copytree(TARGET_BASE, target_root)
    environment = env(tool_root)

    target_initial = inventory(target_root)
    db_path = target_root / ".pyprojectmgr" / "assets.db"
    db_path.unlink()
    db_before = {"asset_count": 0, "removed_stale_catalog": True}
    base_command = [
        str(PYTHON),
        "-m",
        "cli.cli_interface",
        "--project-root",
        str(target_root),
        "--no-color",
    ]
    scan_result = run(
        base_command
        + [
            "scan",
            "--target-dir",
            str(target_root),
            "--baseline",
        ],
        tool_root,
        environment,
        "scan",
    )
    target_after_scan = inventory(target_root)
    db_after_scan = db_summary(db_path)
    qc_result = run(
        base_command + ["qc", "--strict"],
        tool_root,
        environment,
        "qc",
    )
    target_after_qc = inventory(target_root)

    result = {
        "scan": scan_result,
        "qc": qc_result,
        "db_before": db_before,
        "db_after_scan": db_after_scan,
        "scan_changes": diff(target_initial, target_after_scan),
        "qc_changes": diff(target_after_scan, target_after_qc),
    }
    RESULT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "result": str(RESULT_PATH),
                "scan_exit": scan_result["exit_code"],
                "qc_exit": qc_result["exit_code"],
                "db_before_assets": db_before["asset_count"],
                "db_after_assets": db_after_scan["asset_count"],
                "scan_changes": result["scan_changes"],
                "qc_changes": result["qc_changes"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
