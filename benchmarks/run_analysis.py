"""
run_analysis — benchmark disk usage tools vs stdlib baselines (function calls).

Feature: Operators pass 1–4 drive paths for within-drive scan measurement.
Must do: Matrix scenarios, scratch cleanup, physical-device tags on JSONL.
Must NOT: Auto-detect drives; run hardware benches in tests; fetch corpus.
"""

import argparse
import os
from pathlib import Path
from typing import List, Optional

from benchmarks.corpus import (
    RESULTS_DIR,
    bench_bytes_per_sec,
    build_bench_record,
    remove_scratch_tree,
    resolve_corpus_for_bench,
    run_timed,
    track_scratch_cleanup,
    utc_timestamp,
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

BENCH_ROOT = Path(__file__).resolve().parent
ANALYSIS_TOOLS = ("os_toolkit.usage", "stdlib.os.walk", "stdlib.scandir")


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


def bench_tool(
    name, corpus_path: str, signature, profile, scenario_id: str, device_tags: dict
):
    from os_toolkit.analysis.usage import run_usage

    def _run():
        if name == "os_toolkit.usage":
            return run_usage(corpus_path, 5, 0.0, 0, False)
        if name == "stdlib.os.walk":
            walk_total_size(corpus_path)
            return True
        if name == "stdlib.scandir":
            scandir_total_size(corpus_path)
            return True
        return True

    elapsed, exit_status = run_timed(_run)
    bps = bench_bytes_per_sec(Path(corpus_path), elapsed, exit_status)
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
        out = (
            Path(args.output)
            if args.output
            else RESULTS_DIR / f"analysis_{utc_timestamp()}.jsonl"
        )
        for tool in ANALYSIS_TOOLS:
            record = bench_tool(
                tool, str(corpus_path), signature, args.profile, "synthetic", tags
            )
            write_jsonl_record(out, record)
            print(
                f"{record['tool']:22} {record['wall_time_sec']:7.3f}s "
                f"{record['bytes_per_sec']:>12} B/s  exit={record['exit_status']}"
            )
        print(f"Results: {out}")
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
        corpus_parent = analysis_corpus_path(scenario, timestamp)
        bench_root = corpus_parent.parent
        track_scratch_cleanup(bench_root)
        try:
            corpus_path, signature = resolve_corpus_for_bench(
                args.profile,
                args.corpus,
                args.ignore_manifest,
                corpus_parent,
                synthetic_files=30,
                synthetic_size=512,
            )
            tags = _device_tags(corpus_path)
            print(f"Scenario {scenario.id}: scan {corpus_path}")
            for tool in ANALYSIS_TOOLS:
                record = bench_tool(
                    tool,
                    str(corpus_path),
                    signature,
                    args.profile,
                    scenario.id,
                    tags,
                )
                write_jsonl_record(out, record)
                print(
                    f"  {record['tool']:20} {record['wall_time_sec']:7.3f}s "
                    f"{record['bytes_per_sec']:>12} B/s  "
                    f"same_phys={record['same_physical_device']}"
                )
        finally:
            remove_scratch_tree(bench_root)
    print(f"Results: {out}")


def build_parser():
    parser = argparse.ArgumentParser(description="Benchmark analysis / usage tools.")
    parser.add_argument("--profile", default="small/mixed")
    parser.add_argument("--corpus", default="", help="Override corpus directory")
    parser.add_argument("--output", default="")
    parser.add_argument("--ignore-manifest", action="store_true")
    parser.add_argument(
        "--scenarios", default="all", help="all | within (analysis: N scans only)"
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
