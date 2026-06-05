"""
run_zip — benchmark smart zip scan and scoring only (dry-run path).
"""

import argparse
from pathlib import Path
from types import SimpleNamespace
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

BENCH_ROOT = Path(__file__).resolve().parent


def bench_scan_score(
    corpus_path: Path, signature, profile, scenario_id: str, device_tags: dict
):
    from os_toolkit.transfer.archive_scan import choose_candidates, scan_root, settings

    args = SimpleNamespace(
        root=str(corpus_path),
        output="",
        sensitivity="high",
        exclude=[],
        workers=1,
        verbosity=0,
        dry_run=True,
        interactive=False,
        execute=False,
        overwrite=False,
        resume=False,
        delete_originals=False,
    )
    cfg = settings(args, None)

    def _run():
        stats = scan_root(cfg)
        choose_candidates(stats, cfg)

    elapsed, exit_status = run_timed(_run)
    bps = bench_bytes_per_sec(corpus_path, elapsed, exit_status)
    return build_bench_record(
        tool="os_toolkit.smart_zip_scan",
        profile=profile,
        scenario="scan_score_dry_run",
        scenario_id=scenario_id,
        device_tags=device_tags,
        signature=signature,
        wall_time_sec=elapsed,
        bytes_per_sec=bps,
        exit_status=exit_status,
    )


def run_from_args(args) -> None:
    warn_unavailable_datasets()
    tier, sub = args.profile.split("/", 1)
    smoke = None
    if args.corpus:
        corpus_path, signature = resolve_corpus_for_bench(
            args.profile, args.corpus, args.ignore_manifest, Path(".")
        )
    else:
        smoke = BENCH_ROOT / "corpus" / tier / sub / "_bench_smoke_zip"
        track_scratch_cleanup(smoke)
        corpus_path, signature = resolve_corpus_for_bench(
            args.profile,
            "",
            args.ignore_manifest,
            smoke,
            synthetic_files=50,
            synthetic_size=200,
        )
    try:
        tags = _device_tags(corpus_path)
        out = (
            Path(args.output)
            if args.output
            else RESULTS_DIR / f"zip_{utc_timestamp()}.jsonl"
        )
        record = bench_scan_score(
            corpus_path, signature, args.profile, "zip_scan", tags
        )
        write_jsonl_record(out, record)
        print(
            f"{record['tool']:28} {record['wall_time_sec']:7.3f}s "
            f"{record['bytes_per_sec']:>12} B/s"
        )
        print(f"Results: {out}")
    finally:
        if smoke is not None:
            remove_scratch_tree(smoke)


def build_parser():
    parser = argparse.ArgumentParser(description="Benchmark smart zip scan/scoring.")
    parser.add_argument("--profile", default="small/mixed")
    parser.add_argument("--corpus", default="")
    parser.add_argument("--output", default="")
    parser.add_argument("--ignore-manifest", action="store_true")
    return parser


def main(argv: Optional[List[str]] = None) -> None:
    run_from_args(build_parser().parse_args(argv))


if __name__ == "__main__":
    main()
