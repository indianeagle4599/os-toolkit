"""
run_transfer — benchmark copy tools; each tool runs in an isolated run_tool subprocess.

Feature: Operators pass 1–4 drive paths for honest multi-drive copy measurement.
Must do: Matrix scenarios, scratch dirs with cleanup, physical-device tags on JSONL.
Must NOT: Auto-detect drives; run hardware benches in tests; fetch corpus.
"""

import argparse
import json
import os
import random
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from benchmarks.corpus import (
    RESULTS_DIR,
    build_bench_record,
    default_transfer_tools,
    remove_scratch_tree,
    resolve_corpus_for_bench,
    track_scratch_cleanup,
    utc_timestamp,
    warn_unavailable_datasets,
    write_jsonl_record,
)
from benchmarks.devices import device_tags as _device_tags
from benchmarks.matrix import (
    add_drive_args,
    iter_transfer_scenarios,
    parse_drives,
    scratch_paths,
)

BENCH_ROOT = Path(__file__).resolve().parent


def transfer_tools(args) -> List[str]:
    tools = default_transfer_tools()
    if args.shuffle_tools:
        random.Random(args.tool_seed).shuffle(tools)
    return tools


def _scenario_media_matches(scenario, media_filter: str) -> bool:
    if media_filter == "all":
        return True
    from os_toolkit.core.storage import describe_path

    src_rot = describe_path(str(scenario.src_path))["rotational"]
    dst_rot = describe_path(str(scenario.dst_path))["rotational"]
    if media_filter == "ssd":
        return src_rot is False and dst_rot is False
    if media_filter == "hdd":
        return src_rot is True or dst_rot is True
    raise ValueError(f"unknown media filter {media_filter!r}; use all, ssd, or hdd")


def _stage_corpus_to_scratch(corpus_dir: Path, src_dir: Path) -> Path:
    """Copy corpus onto the scenario source-drive scratch tree when paths differ."""
    if corpus_dir.resolve() == src_dir.resolve():
        return src_dir
    src_dir.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copytree(corpus_dir, src_dir, dirs_exist_ok=True)
    except OSError as exc:
        raise SystemExit(
            f"staging corpus failed: {corpus_dir} -> {src_dir}: {exc}"
        ) from exc
    return src_dir


def _log_bench_tool_failure(name: str, proc: subprocess.CompletedProcess) -> None:
    err = (proc.stderr or "").strip()
    tail = err[-500:] if err else "(no stderr)"
    print(f"[bench] {name} failed rc={proc.returncode}: {tail}", file=sys.stderr)


def bench_tool(
    name,
    src: Path,
    dst: Path,
    signature,
    profile,
    scenario_id: str,
    device_tags: dict,
):
    worker_meta = {"requested": None, "effective": None}
    workers = 1
    if name == "os_toolkit.transfer":
        from os_toolkit.core.storage import default_transfer_workers

        workers = default_transfer_workers()
        worker_meta["requested"] = workers
        worker_meta["effective"] = workers

    tool_dst = dst.parent / dst.name / name.replace(".", "_")
    tool_dst.mkdir(parents=True, exist_ok=True)

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "benchmarks.run_tool",
            "--tool",
            name,
            "--src",
            str(src),
            "--dst",
            str(tool_dst),
            "--workers",
            str(workers),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0 and not proc.stdout.strip():
        _log_bench_tool_failure(name, proc)
        return None
    try:
        payload = json.loads(proc.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        _log_bench_tool_failure(name, proc)
        return None

    exit_status = 0 if proc.returncode == 0 else int(proc.returncode)
    elapsed = float(payload["wall_time_sec"])
    dst_bytes = int(payload.get("dst_bytes", 0))
    bps = int(dst_bytes / elapsed) if exit_status == 0 and elapsed > 0 else 0
    return build_bench_record(
        tool=name,
        profile=profile,
        scenario="copy_tree",
        scenario_id=scenario_id,
        device_tags=device_tags,
        signature=signature,
        wall_time_sec=elapsed,
        bytes_per_sec=bps,
        exit_status=exit_status,
        dst_bytes=dst_bytes,
        workers_requested=worker_meta["requested"],
        workers_effective=worker_meta["effective"],
    )


def _bench_roots_for_scratch(src_dir: Path, dst_dir: Path) -> List[Path]:
    roots = [src_dir.parent]
    if dst_dir.parent != src_dir.parent:
        roots.append(dst_dir.parent)
    return roots


def run_single(args) -> None:
    tier, sub = args.profile.split("/", 1)
    smoke = BENCH_ROOT / "corpus" / tier / sub / "_bench_smoke"
    track_scratch_cleanup(smoke)
    copy_dest = smoke.parent / "_bench_copy_dest"
    track_scratch_cleanup(copy_dest)
    try:
        src, signature = resolve_corpus_for_bench(
            args.profile, args.corpus, args.ignore_manifest, smoke
        )
        tags = _device_tags(src, copy_dest)
        out = (
            Path(args.output)
            if args.output
            else RESULTS_DIR / f"transfer_{utc_timestamp()}.jsonl"
        )
        for tool in transfer_tools(args):
            record = bench_tool(
                tool, src, copy_dest, signature, args.profile, "synthetic", tags
            )
            if record is None:
                continue
            write_jsonl_record(out, record)
            print(
                f"{record['tool']:22} {record['wall_time_sec']:7.3f}s "
                f"{record['bytes_per_sec']:>12} B/s"
            )
        print(f"Results: {out}")
    finally:
        remove_scratch_tree(smoke)
        remove_scratch_tree(copy_dest)


def run_matrix(args, drives: dict) -> None:
    timestamp = utc_timestamp()
    out = (
        Path(args.output)
        if args.output
        else RESULTS_DIR / f"transfer_{timestamp}.jsonl"
    )
    tools = transfer_tools(args)
    for scenario in iter_transfer_scenarios(drives, args.scenarios):
        if not _scenario_media_matches(scenario, args.media_filter):
            continue
        src_dir, dst_dir = scratch_paths(scenario, timestamp)
        bench_roots = _bench_roots_for_scratch(src_dir, dst_dir)
        for root in bench_roots:
            track_scratch_cleanup(root)
        try:
            corpus_dir, signature = resolve_corpus_for_bench(
                args.profile, args.corpus, args.ignore_manifest, src_dir
            )
            staged_src = _stage_corpus_to_scratch(Path(corpus_dir), src_dir)
            tags = _device_tags(staged_src, dst_dir)
            print(f"Scenario {scenario.id}: {staged_src} -> {dst_dir}")
            for tool in tools:
                record = bench_tool(
                    tool,
                    staged_src,
                    dst_dir,
                    signature,
                    args.profile,
                    scenario.id,
                    tags,
                )
                if record is None:
                    continue
                write_jsonl_record(out, record)
                print(
                    f"  {record['tool']:20} {record['wall_time_sec']:7.3f}s "
                    f"{record['bytes_per_sec']:>12} B/s  "
                    f"same_phys={record['same_physical_device']}"
                )
        finally:
            for root in bench_roots:
                remove_scratch_tree(root)
    print(f"Results: {out}")


def build_parser():
    parser = argparse.ArgumentParser(description="Benchmark directory copy tools.")
    parser.add_argument("--profile", default="small/mixed")
    parser.add_argument("--corpus", default="")
    parser.add_argument("--dest", default="")
    parser.add_argument("--output", default="")
    parser.add_argument("--ignore-manifest", action="store_true")
    parser.add_argument(
        "--scenarios", default="all", help="all | within | cross | a->b,..."
    )
    parser.add_argument(
        "--media-filter",
        default="ssd",
        choices=["all", "ssd", "hdd"],
        help="Run only scenarios matching media type (hardware matrix only)",
    )
    parser.add_argument(
        "--shuffle-tools",
        action="store_true",
        help="Randomize tool run order (optional --tool-seed for reproducibility)",
    )
    parser.add_argument(
        "--tool-seed",
        type=int,
        default=None,
        help="RNG seed for --shuffle-tools",
    )
    add_drive_args(parser)
    return parser


def run_from_args(args) -> None:
    warn_unavailable_datasets()
    drives = parse_drives(args)
    if drives:
        run_matrix(args, drives)
    else:
        run_single(args)


def main(argv: Optional[List[str]] = None) -> None:
    run_from_args(build_parser().parse_args(argv))


if __name__ == "__main__":
    main()
