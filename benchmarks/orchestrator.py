"""
orchestrator — multi-run benchmark loop with cumulative MAD outlier filtering.

Re-runs a suite until each (tool, scenario_id) has enough non-outlier valid runs,
then writes an aggregate summary. Use via `just bench-multi transfer ...`.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

from benchmarks.aggregate import (
    build_aggregate,
    flag_outliers_per_pair,
    group_by_pair,
    load_run_files,
    pairs_satisfied,
    print_summary_table,
    valid_run_counts,
    write_aggregate,
)
from benchmarks.corpus import RESULTS_DIR, warn_unavailable_datasets
from benchmarks.matrix import add_drive_args
from benchmarks import run_analysis, run_transfer, run_zip

SUITES = ("transfer", "analysis", "zip")


def _suite_runner(suite: str):
    if suite == "transfer":
        return run_transfer
    if suite == "analysis":
        return run_analysis
    if suite == "zip":
        return run_zip
    raise ValueError(suite)


def _pairs_ready(paths: List[Path], min_valid: int) -> bool:
    if not paths:
        return False
    rows = load_run_files(paths)
    groups = group_by_pair(rows)
    flagged = flag_outliers_per_pair(groups)
    counts = valid_run_counts(groups, flagged)
    return pairs_satisfied(counts, min_valid)


def run_suite_loop(args) -> Path:
    results_dir = Path(args.results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    runner = _suite_runner(args.suite)
    paths: List[Path] = []
    attempt = 0
    while attempt < args.max_runs:
        attempt += 1
        out = results_dir / f"{args.suite}_run{attempt}.jsonl"
        print(f"[{args.suite}] run {attempt}/{args.max_runs} -> {out}", flush=True)
        args.output = str(out)
        runner.run_from_args(args)
        paths.append(out)
        if _pairs_ready(paths, args.min_valid):
            print(
                f"[{args.suite}] stopping: every (tool, scenario) has "
                f">={args.min_valid} non-outlier runs",
                flush=True,
            )
            break
        if attempt < args.max_runs:
            print(f"[{args.suite}] pairs not satisfied; continuing...", flush=True)
    agg_path = results_dir / f"{args.suite}_aggregate.json"
    payload = build_aggregate(paths, min_valid=args.min_valid)
    write_aggregate(agg_path, payload)
    print(f"[{args.suite}] aggregate: {agg_path}", flush=True)
    print_summary_table(payload)
    return agg_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Multi-run benchmark orchestrator.")
    parser.add_argument(
        "suite",
        choices=list(SUITES) + ["all"],
        help="transfer | analysis | zip | all",
    )
    parser.add_argument("--profile", default="small/mixed")
    parser.add_argument(
        "--corpus",
        default="",
        help="Corpus directory (optional; synthetic smoke when omitted)",
    )
    parser.add_argument("--results-dir", default=str(RESULTS_DIR))
    add_drive_args(parser)
    parser.add_argument("--scenarios", default="all")
    parser.add_argument("--ignore-manifest", action="store_true")
    parser.add_argument(
        "--media-filter",
        default="ssd",
        choices=["all", "ssd", "hdd"],
        help="Transfer only: filter scenarios by media type",
    )
    parser.add_argument("--shuffle-tools", action="store_true")
    parser.add_argument("--tool-seed", type=int, default=None)
    parser.add_argument("--max-runs", type=int, default=10)
    parser.add_argument("--min-valid", type=int, default=3)
    return parser


def main(argv: List[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    warn_unavailable_datasets()
    suites = SUITES if args.suite == "all" else (args.suite,)
    for suite in suites:
        args.suite = suite
        run_suite_loop(args)


if __name__ == "__main__":
    main()
