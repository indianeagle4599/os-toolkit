"""
run_tool — isolated subprocess runner for a single transfer benchmark tool.

Feature: One tool per process with perf_counter on full copy (blank slate to done).
Must do: Emit one JSON line (tool, wall_time_sec, dst_bytes) on stdout.
Must NOT: Run multiple tools; import run_transfer.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from benchmarks.corpus import corpus_tree_bytes


def _run_os_toolkit(src: str, dst: str, workers: int) -> tuple[float, bool]:
    from os_toolkit.core.storage import rotational_for_path
    from os_toolkit.transfer.copy import hdd_copy, ssd_copy

    is_hdd = rotational_for_path(dst) is not False
    start = time.perf_counter()
    if is_hdd:
        ok = hdd_copy(src, dst, verbosity=0, resume=False)
    else:
        ok = ssd_copy(
            src, dst, workers=max(1, workers), verbosity=0, resume=False
        )
    return time.perf_counter() - start, ok


def _run_copytree(src: str, dst: str) -> tuple[float, bool]:
    start = time.perf_counter()
    shutil.copytree(src, dst, dirs_exist_ok=True)
    return time.perf_counter() - start, True


def _rsync_trailing_slash(path: str) -> str:
    return path.rstrip("/\\") + "/"


def _run_rsync(src: str, dst: str) -> tuple[float, bool]:
    start = time.perf_counter()
    proc = subprocess.run(
        ["rsync", "-a", _rsync_trailing_slash(src), _rsync_trailing_slash(dst)],
        check=False,
        capture_output=True,
    )
    elapsed = time.perf_counter() - start
    return elapsed, proc.returncode == 0


def _run_robocopy(src: str, dst: str) -> tuple[float, bool]:
    start = time.perf_counter()
    proc = subprocess.run(
        ["robocopy", src, dst, "/E", "/NFL", "/NDL", "/NJH", "/NJS"],
        check=False,
        capture_output=True,
    )
    elapsed = time.perf_counter() - start
    return elapsed, proc.returncode < 8


def run_one(tool: str, src: Path, dst: Path, workers: int) -> tuple[float, int, bool]:
    src_s, dst_s = str(src), str(dst)
    dst.mkdir(parents=True, exist_ok=True)
    ok = False
    elapsed = 0.0
    if tool == "os_toolkit.transfer":
        elapsed, ok = _run_os_toolkit(src_s, dst_s, workers)
    elif tool == "stdlib.copytree":
        elapsed, ok = _run_copytree(src_s, dst_s)
    elif tool == "rsync":
        elapsed, ok = _run_rsync(src_s, dst_s)
    elif tool == "robocopy" and os.name == "nt":
        elapsed, ok = _run_robocopy(src_s, dst_s)
    else:
        return 0.0, 0, False
    dst_bytes = corpus_tree_bytes(dst) if ok else 0
    return elapsed, dst_bytes, ok


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run one transfer bench tool.")
    parser.add_argument("--tool", required=True)
    parser.add_argument("--src", required=True)
    parser.add_argument("--dst", required=True)
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args(argv)
    elapsed, dst_bytes, ok = run_one(
        args.tool, Path(args.src), Path(args.dst), args.workers
    )
    print(
        json.dumps(
            {
                "tool": args.tool,
                "wall_time_sec": round(elapsed, 4),
                "dst_bytes": dst_bytes,
            }
        ),
        flush=True,
    )
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
