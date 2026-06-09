"""
run_analysis — benchmark disk usage tools vs stdlib baselines (function calls).

Feature: Operators pass 1–4 drive paths for within-drive scan measurement.
Must do: Matrix scenarios, corpus staging on drive, physical-device tags on JSONL.
Must NOT: Auto-detect drives; run hardware benches in tests; fetch corpus.

Bench params: max_depth=5, threshold=0.0 (full tree at depth 5). Production CLI
default threshold is 1.0% — published runtimes are not default-operator timings.
"""

import argparse
import os
import shutil
import sys
from pathlib import Path
from typing import List, Optional

from benchmarks.corpus import (
    RESULTS_DIR,
    build_bench_record,
    corpus_tree_bytes,
    remove_scratch_tree,
    resolve_corpus_for_bench,
    run_timed,
    track_scratch_cleanup,
    utc_timestamp,
    validate_profile,
    warn_unavailable_datasets,
    write_jsonl_record,
)
from benchmarks.devices import device_tags as _device_tags
from benchmarks.matrix import (
    add_drive_args,
    analysis_corpus_path,
    iter_analysis_scenarios,
    parse_drives,
)
from os_toolkit.core.storage import describe_path

BENCH_ROOT = Path(__file__).resolve().parent
ANALYSIS_TOOLS = ("os_toolkit.usage", "stdlib.os.walk", "stdlib.scandir")
BENCH_MAX_DEPTH = 5
BENCH_THRESHOLD = 0.0


def walk_total_size(root: str) -> int:
    total = 0
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            try:
                total += os.path.getsize(os.path.join(dirpath, name))
            except OSError:
                pass
    return total


def scandir_total_size(root: str) -> int:
    total = 0

    def rec(path):
        nonlocal total
        try:
            with os.scandir(path) as it:
                for entry in it:
                    if entry.is_file(follow_symlinks=False):
                        total += entry.stat().st_size
                    elif entry.is_dir(follow_symlinks=False):
                        rec(entry.path)
        except OSError:
            pass

    rec(root)
    return total


def _scenario_media_skip_reason(scenario, media_filter: str) -> Optional[str]:
    """Return a skip reason, or None when the scenario matches the filter."""
    if media_filter == "all":
        return None
    rot = describe_path(str(scenario.src_path))["rotational"]
    if media_filter == "ssd":
        if rot is False:
            return None
        if rot is True:
            return "HDD drive"
        return "unknown rotational media"
    if media_filter == "hdd":
        if rot is True:
            return None
        if rot is False:
            return "SSD drive"
        return "unknown rotational media"
    raise ValueError(f"unknown media filter {media_filter!r}; use all, ssd, or hdd")


def _stage_corpus(source: Path, dest: Path) -> Path:
    """Copy corpus onto the scenario drive when paths differ."""
    if source.resolve() == dest.resolve():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        shutil.rmtree(dest)
    try:
        shutil.copytree(source, dest)
    except OSError as exc:
        raise SystemExit(f"staging corpus failed: {source} -> {dest}: {exc}") from exc
    return dest


def _resolve_scenario_corpus(
    args,
    scenario,
    timestamp: str,
) -> tuple[Path, str]:
    if args.corpus:
        source = Path(args.corpus)
        if not source.is_dir():
            raise SystemExit(f"corpus path not found or not a directory: {source}")
        signature = validate_profile(str(source), "", args.ignore_manifest)
        if args.no_stage:
            return source, signature
        dest = analysis_corpus_path(scenario, timestamp)
        track_scratch_cleanup(dest.parent)
        return _stage_corpus(source, dest), signature
    smoke_parent = analysis_corpus_path(scenario, timestamp)
    track_scratch_cleanup(smoke_parent.parent)
    return resolve_corpus_for_bench(
        args.profile,
        "",
        args.ignore_manifest,
        smoke_parent,
        synthetic_files=30,
        synthetic_size=512,
    )


def bench_tool(
    name,
    corpus_path: str,
    signature,
    profile,
    scenario_id: str,
    device_tags: dict,
    corpus_bytes: int,
):
    from os_toolkit.analysis.usage import bench_usage_scan

    def _run():
        if name == "os_toolkit.usage":
            return bench_usage_scan(
                corpus_path,
                max_depth=BENCH_MAX_DEPTH,
                threshold=BENCH_THRESHOLD,
                shallow_scan=False,
            )
        if name == "stdlib.os.walk":
            walk_total_size(corpus_path)
            return True
        if name == "stdlib.scandir":
            scandir_total_size(corpus_path)
            return True
        raise ValueError(f"unknown analysis bench tool {name!r}")

    elapsed, exit_status = run_timed(_run)
    bps = 0
    if exit_status == 0 and elapsed > 0 and corpus_bytes > 0:
        bps = int(corpus_bytes / elapsed)
    return build_bench_record(
        tool=name,
        profile=profile,
        scenario="usage_scan",
        scenario_id=scenario_id,
        device_tags=device_tags,
        signature=signature,
        wall_time_sec=elapsed,
        bytes_per_sec=bps,
        exit_status=exit_status,
        dst_bytes=corpus_bytes,
    )


def run_single(args) -> None:
    tier, sub = args.profile.split("/", 1)
    smoke = BENCH_ROOT / "corpus" / tier / sub / "_bench_smoke"
    track_scratch_cleanup(smoke)
    try:
        corpus_path, signature = resolve_corpus_for_bench(
            args.profile,
            args.corpus,
            args.ignore_manifest,
            smoke,
            synthetic_files=30,
            synthetic_size=512,
        )
        tags = _device_tags(Path(corpus_path))
        corpus_bytes = corpus_tree_bytes(Path(corpus_path))
        out = (
            Path(args.output)
            if args.output
            else RESULTS_DIR / f"analysis_{utc_timestamp()}.jsonl"
        )
        for tool in ANALYSIS_TOOLS:
            record = bench_tool(
                tool,
                str(corpus_path),
                signature,
                args.profile,
                "synthetic",
                tags,
                corpus_bytes,
            )
            write_jsonl_record(out, record)
            print(
                f"{record['tool']:22} {record['wall_time_sec']:7.3f}s "
                f"{record['bytes_per_sec']:>12} B/s  exit={record['exit_status']}",
                flush=True,
            )
        print(f"Results: {out}", flush=True)
    finally:
        remove_scratch_tree(smoke)


def run_matrix(args, drives: dict) -> None:
    timestamp = utc_timestamp()
    out = (
        Path(args.output)
        if args.output
        else RESULTS_DIR / f"analysis_{timestamp}.jsonl"
    )
    for scenario in iter_analysis_scenarios(drives, args.scenarios):
        skip = _scenario_media_skip_reason(scenario, args.media_filter)
        if skip:
            print(
                f"Scenario {scenario.id}: skip ({skip}, "
                f"--media-filter {args.media_filter})",
                file=sys.stderr,
                flush=True,
            )
            continue
        bench_root = analysis_corpus_path(scenario, timestamp).parent
        track_scratch_cleanup(bench_root)
        try:
            corpus_path, signature = _resolve_scenario_corpus(args, scenario, timestamp)
            tags = _device_tags(corpus_path)
            corpus_bytes = corpus_tree_bytes(corpus_path)
            print(
                f"Scenario {scenario.id}: scan {corpus_path} "
                f"({corpus_bytes / (1024**2):.1f} MB)",
                flush=True,
            )
            for tool in ANALYSIS_TOOLS:
                record = bench_tool(
                    tool,
                    str(corpus_path),
                    signature,
                    args.profile,
                    scenario.id,
                    tags,
                    corpus_bytes,
                )
                write_jsonl_record(out, record)
                print(
                    f"  {record['tool']:20} {record['wall_time_sec']:7.3f}s "
                    f"{record['bytes_per_sec']:>12} B/s  "
                    f"same_phys={record['same_physical_device']}",
                    flush=True,
                )
        finally:
            remove_scratch_tree(bench_root)
    print(f"Results: {out}", flush=True)


def build_parser():
    parser = argparse.ArgumentParser(description="Benchmark analysis / usage tools.")
    parser.add_argument("--profile", default="small/mixed")
    parser.add_argument("--corpus", default="", help="Override corpus directory")
    parser.add_argument("--output", default="")
    parser.add_argument("--ignore-manifest", action="store_true")
    parser.add_argument(
        "--scenarios", default="all", help="all | within (analysis: N scans only)"
    )
    parser.add_argument(
        "--media-filter",
        default="ssd",
        choices=["all", "ssd", "hdd"],
        help="Skip scenarios whose scan drive is not SSD/HDD/all",
    )
    parser.add_argument(
        "--no-stage",
        action="store_true",
        help="Scan --corpus in place (no copy to --drive-* scratch)",
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
