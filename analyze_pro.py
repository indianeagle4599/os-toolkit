"""
Analyze Pro — unified analysis CLI (usage, compare).

Features:
- usage: disk usage tree (2x2 Usage)
- compare: match two directory trees (profiles internally, then compare)
"""

import argparse
import os
import sys

from os_toolkit.analysis.runs import (
    compare_run_id,
    ensure_profile,
    run_dir,
)
from os_toolkit.analysis.usage import add_usage_arguments, run_usage


def cmd_usage(args):
    ok = run_usage(
        args.path,
        args.max_depth,
        args.threshold,
        args.verbosity,
        args.shallow_scan,
    )
    if not ok:
        sys.exit(1)


def cmd_compare(args):
    from os_toolkit.analysis.compare import run_compare, settings_from_namespace

    if not args.old or not args.new:
        raise SystemExit("compare requires --old and --new directory roots")

    old_root = os.path.abspath(args.old)
    new_root = os.path.abspath(args.new)
    if not os.path.isdir(old_root):
        raise SystemExit(f"--old is not a directory: {old_root}")
    if not os.path.isdir(new_root):
        raise SystemExit(f"--new is not a directory: {new_root}")

    run_id = args.run_id or compare_run_id(old_root, new_root)
    run_path = run_dir(run_id)

    args.old = ensure_profile(
        old_root, run_path, prefix="old_", verbosity=args.verbosity
    )
    args.new = ensure_profile(
        new_root, run_path, prefix="new_", verbosity=args.verbosity
    )
    args.run_id = run_id
    args.run_path = run_path

    if args.verbosity >= 1:
        print(f"\nRun artifacts: {run_path}")

    run_compare(settings_from_namespace(args))


def build_parser():
    parser = argparse.ArgumentParser(
        description="Analyze Pro — usage and compare subcommands"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    usage = sub.add_parser("usage", help="Disk usage tree for one root")
    add_usage_arguments(usage, path_required=True)
    usage.set_defaults(func=cmd_usage)

    compare = sub.add_parser(
        "compare", help="Match two directory trees (profiles cached under runs/)"
    )
    compare.add_argument("--old", required=True, help="Old root directory")
    compare.add_argument("--new", required=True, help="New root directory")
    compare.add_argument(
        "--run-id",
        default=None,
        help="Run folder under runs/ (default: stable id from both roots)",
    )
    compare.add_argument("-v", "--verbosity", type=int, choices=[0, 1, 2], default=1)
    compare.add_argument(
        "--threshold",
        type=float,
        default=0.7,
        help="Minimum match score (0-1) for summary lines",
    )
    compare.add_argument(
        "--topk", type=int, default=3, help="Top candidate matches per old row"
    )
    compare.add_argument(
        "--batch-size",
        type=int,
        default=5000,
        help="Structure similarity batch size (rows)",
    )
    compare.add_argument(
        "--structure-filter",
        type=float,
        default=0.4,
        help="Min structure similarity before name scoring",
    )
    compare.add_argument(
        "--name-sim",
        default="tfidf",
        choices=["rapidfuzz", "tfidf", "bert"],
        help="Name similarity backend (bert/rapidfuzz need extra pip packages)",
    )
    compare.add_argument(
        "--tfidf-ngrams", default="2-4", help="TF-IDF n-gram range, e.g. 2-4"
    )
    compare.add_argument(
        "--tokenizer",
        default="char",
        choices=["char", "path"],
        help="Tokenize folder names by character or path segment",
    )
    compare.add_argument(
        "--depth-limit",
        type=int,
        default=0,
        help="Top-level group depth for text summary (0 = root children)",
    )
    compare.add_argument(
        "--workers",
        type=int,
        default=min(os.cpu_count() or 1, 6),
        help="Parallel workers for top-level filter",
    )
    compare.add_argument("--color", action="store_true", help="ANSI colors in summary")
    compare.set_defaults(func=cmd_compare)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
