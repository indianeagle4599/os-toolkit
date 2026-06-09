"""
aggregate — load bench JSONL runs, apply outlier filter, write aggregate.json.

Use after one or more benchmark runs to compute median wall time and throughput
per (tool, scenario_id) with MAD outlier removal.
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from benchmarks.outliers import DEFAULT_THRESHOLD, outlier_flags

REQUIRED_FIELDS = (
    "tool",
    "scenario_id",
    "corpus_signature",
    "wall_time_sec",
    "bytes_per_sec",
    "exit_status",
)


def load_jsonl(path: Path) -> List[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def load_run_files(paths: Sequence[Path]) -> List[Tuple[str, dict]]:
    rows: List[Tuple[str, dict]] = []
    for path in paths:
        run_id = path.stem
        for rec in load_jsonl(path):
            for key in REQUIRED_FIELDS:
                if key not in rec:
                    raise ValueError(f"{path}: missing {key}")
            rows.append((run_id, rec))
    return rows


def group_by_pair(
    rows: Sequence[Tuple[str, dict]],
) -> Dict[Tuple[str, str], List[Tuple[str, dict]]]:
    groups: Dict[Tuple[str, str], List[Tuple[str, dict]]] = defaultdict(list)
    for run_id, rec in rows:
        key = (rec["tool"], rec["scenario_id"])
        groups[key].append((run_id, rec))
    return groups


def flag_outliers_per_pair(
    groups: Dict[Tuple[str, str], List[Tuple[str, dict]]],
    *,
    threshold: float = DEFAULT_THRESHOLD,
) -> Dict[Tuple[str, str, str], bool]:
    """Map (run_id, tool, scenario_id) -> is_outlier on bytes_per_sec."""
    flagged: Dict[Tuple[str, str, str], bool] = {}
    for (tool, scenario_id), items in groups.items():
        values = [float(rec["bytes_per_sec"]) for _, rec in items]
        flags = outlier_flags(values, threshold=threshold)
        for (run_id, _), is_out in zip(items, flags):
            flagged[(run_id, tool, scenario_id)] = is_out
    return flagged


def valid_run_counts(
    groups: Dict[Tuple[str, str], List[Tuple[str, dict]]],
    flagged: Dict[Tuple[str, str, str], bool],
) -> Dict[Tuple[str, str], int]:
    counts: Dict[Tuple[str, str], int] = {}
    for key, items in groups.items():
        tool, scenario_id = key
        good = {
            run_id
            for run_id, _ in items
            if not flagged.get((run_id, tool, scenario_id), False)
        }
        counts[key] = len(good)
    return counts


def pairs_satisfied(valid_counts: Dict[Tuple[str, str], int], min_valid: int) -> bool:
    if not valid_counts:
        return False
    return all(n >= min_valid for n in valid_counts.values())


def summarize_pair(
    items: Sequence[Tuple[str, dict]], flagged: Dict[Tuple[str, str, str], bool]
) -> dict:
    tool, scenario_id = items[0][1]["tool"], items[0][1]["scenario_id"]
    kept = [
        rec
        for run_id, rec in items
        if not flagged.get((run_id, tool, scenario_id), False)
    ]
    wall = [rec["wall_time_sec"] for rec in kept]
    bps = [rec["bytes_per_sec"] for rec in kept]
    return {
        "tool": tool,
        "scenario_id": scenario_id,
        "runs_total": len(items),
        "runs_valid": len(kept),
        "outliers_removed": len(items) - len(kept),
        "wall_time_sec_median": statistics.median(wall) if wall else None,
        "bytes_per_sec_median": statistics.median(bps) if bps else None,
    }


def build_aggregate(
    paths: Sequence[Path],
    *,
    min_valid: int = 3,
    threshold: float = DEFAULT_THRESHOLD,
) -> dict:
    rows = load_run_files(paths)
    groups = group_by_pair(rows)
    flagged = flag_outliers_per_pair(groups, threshold=threshold)
    valid_counts = valid_run_counts(groups, flagged)
    first = rows[0][1] if rows else {}
    return {
        "runs_attempted": len(paths),
        "min_valid_per_pair": min_valid,
        "outlier_threshold": threshold,
        "corpus_signature": first.get("corpus_signature"),
        "pairs_satisfied": pairs_satisfied(valid_counts, min_valid),
        "valid_counts": {
            f"{tool}|{scenario_id}": n
            for (tool, scenario_id), n in valid_counts.items()
        },
        "summaries": [summarize_pair(items, flagged) for items in groups.values()],
    }


def write_aggregate(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")


def load_aggregate(path: Path) -> dict:
    """Read an aggregate JSON file written by write_aggregate."""
    return json.loads(path.read_text(encoding="utf-8"))


def print_summary_table(payload: dict) -> None:
    print(f"pairs_satisfied={payload.get('pairs_satisfied')}")
    for row in payload.get("summaries", []):
        wall = row.get("wall_time_sec_median")
        bps = row.get("bytes_per_sec_median")
        wall_s = f"{wall:.3f}" if wall is not None else "—"
        bps_s = f"{bps}" if bps is not None else "—"
        print(
            f"  {row['tool']:22} {row['scenario_id']:12} "
            f"valid={row['runs_valid']}/{row['runs_total']}  "
            f"wall_median={wall_s}s  bps_median={bps_s}"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Aggregate benchmark JSONL runs with MAD outlier filtering."
    )
    parser.add_argument(
        "jsonl_paths",
        nargs="+",
        help="One or more JSONL result files",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Write aggregate JSON here (default: first input stem + _aggregate.json)",
    )
    parser.add_argument("--min-valid", type=int, default=3)
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help="Modified Z-score threshold (default 3.5)",
    )
    return parser


def main(argv: List[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    paths = [Path(p) for p in args.jsonl_paths]
    payload = build_aggregate(paths, min_valid=args.min_valid, threshold=args.threshold)
    out = (
        Path(args.output)
        if args.output
        else paths[0].with_name(f"{paths[0].stem.rsplit('_run', 1)[0]}_aggregate.json")
    )
    write_aggregate(out, payload)
    print(f"Aggregate: {out}")
    print_summary_table(payload)


if __name__ == "__main__":
    main()
