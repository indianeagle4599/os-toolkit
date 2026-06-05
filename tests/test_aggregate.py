"""Benchmark aggregation — benchmarks/aggregate.py."""

import json
from pathlib import Path

from benchmarks.aggregate import build_aggregate, pairs_satisfied
from benchmarks.aggregate import group_by_pair, load_run_files, flag_outliers_per_pair
from benchmarks.aggregate import valid_run_counts


def _write_run(path: Path, tool: str, scenario_id: str, bps: int, run_label: str):
    rec = {
        "tool": tool,
        "scenario_id": scenario_id,
        "corpus_signature": "sig",
        "wall_time_sec": 1.0,
        "bytes_per_sec": bps,
        "exit_status": 0,
        "bench_run": run_label,
    }
    path.write_text(json.dumps(rec) + "\n", encoding="utf-8")


def test_pairs_satisfied_requires_all_groups(tmp_path):
    p1 = tmp_path / "transfer_run1.jsonl"
    p2 = tmp_path / "transfer_run2.jsonl"
    p3 = tmp_path / "transfer_run3.jsonl"
    for p in (p1, p2, p3):
        _write_run(p, "os_toolkit.transfer", "a_to_b", 1000, p.stem)
    rows = load_run_files([p1, p2, p3])
    groups = group_by_pair(rows)
    flagged = flag_outliers_per_pair(groups)
    counts = valid_run_counts(groups, flagged)
    assert pairs_satisfied(counts, 3)


def test_build_aggregate_median_correct(tmp_path):
    paths = []
    for i, bps in enumerate((900, 1000, 1100), start=1):
        p = tmp_path / f"transfer_run{i}.jsonl"
        _write_run(p, "os_toolkit.transfer", "a_to_c", bps, p.stem)
        paths.append(p)
    agg = build_aggregate(paths, min_valid=3)
    summary = agg["summaries"][0]
    assert summary["bytes_per_sec_median"] == 1000
    assert summary["runs_valid"] == 3
    assert agg["pairs_satisfied"] is True
