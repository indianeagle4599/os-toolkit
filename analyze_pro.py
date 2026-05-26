"""
Analyze Pro — unified analysis CLI (usage, profile, compare).

Features:
- usage: disk usage tree (2x2 Usage)
- profile: nested profile + features CSV under runs/
- compare: inter-root profile match using feature CSVs
"""

import argparse
import os
import sys

from os_toolkit.analysis.profile import run_profile_to_dir
from os_toolkit.analysis.runs import new_run_id, run_dir, write_manifest
from os_toolkit.analysis.usage import run_usage


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


def cmd_profile(args):
    run_path = run_dir(args.run_id)

    if args.old_root and args.new_root:
        run_profile_to_dir(
            args.old_root, run_path, prefix="old_", verbosity=args.verbosity
        )
        run_profile_to_dir(
            args.new_root, run_path, prefix="new_", verbosity=args.verbosity
        )
        write_manifest(
            run_path,
            {
                "command": "analyze.profile",
                "inputs": {"old_root": args.old_root, "new_root": args.new_root},
                "outputs": {
                    "old_profile": os.path.join(run_path, "old_profile.json"),
                    "new_profile": os.path.join(run_path, "new_profile.json"),
                    "old_features": os.path.join(run_path, "old_features.csv"),
                    "new_features": os.path.join(run_path, "new_features.csv"),
                },
            },
        )
        print(f"\nRun artifacts: {run_path}")
        return

    if not args.root:
        raise SystemExit("profile requires --root or both --old-root and --new-root")

    run_profile_to_dir(args.root, run_path, prefix="", verbosity=args.verbosity)
    write_manifest(
        run_path,
        {
            "command": "analyze.profile",
            "inputs": {"root": args.root},
            "outputs": {
                "profile": os.path.join(run_path, "profile.json"),
                "features": os.path.join(run_path, "features.csv"),
            },
        },
    )
    print(f"\nRun artifacts: {run_path}")


def cmd_compare(args):
    from os_toolkit.analysis.compare import run_compare, settings_from_namespace

    if args.run_id and not args.old and not args.new:
        run_path = run_dir(args.run_id)
        args.old = args.old or os.path.join(run_path, "old_features.csv")
        args.new = args.new or os.path.join(run_path, "new_features.csv")

    if not args.old or not args.new:
        raise SystemExit("compare requires --old and --new feature CSV paths")

    args.run_id = args.run_id or "manual"
    run_compare(settings_from_namespace(args))


def build_parser():
    parser = argparse.ArgumentParser(
        description="Analyze Pro — usage, profile, and compare subcommands"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    usage = sub.add_parser("usage", help="Disk usage tree for one root")
    usage.add_argument("-p", "--path", required=True, help="Root directory")
    usage.add_argument("-d", "--max-depth", type=int, default=7)
    usage.add_argument("-t", "--threshold", type=float, default=1.0)
    usage.add_argument("-v", "--verbosity", type=int, choices=[0, 1, 2], default=1)
    usage.add_argument("-s", "--shallow-scan", action="store_true")
    usage.set_defaults(func=cmd_usage)

    profile = sub.add_parser("profile", help="Nested profile + features under runs/")
    profile.add_argument("--root", help="Single root to profile")
    profile.add_argument("--old-root", help="Old root (pair with --new-root)")
    profile.add_argument("--new-root", help="New root (pair with --old-root)")
    profile.add_argument(
        "--run-id",
        default=None,
        help="Run folder under runs/ (default: new timestamp id)",
    )
    profile.add_argument("-v", "--verbosity", type=int, choices=[0, 1, 2], default=1)
    profile.set_defaults(func=cmd_profile)

    compare = sub.add_parser("compare", help="Match old/new feature CSVs")
    compare.add_argument("--old", help="Old features CSV")
    compare.add_argument("--new", help="New features CSV")
    compare.add_argument("--run-id", default=None, help="Run under runs/")
    compare.add_argument("--threshold", type=float, default=0.7)
    compare.add_argument("--topk", type=int, default=3)
    compare.add_argument("--batch-size", type=int, default=5000)
    compare.add_argument("--structure-filter", type=float, default=0.4)
    compare.add_argument(
        "--name-sim", default="tfidf", choices=["rapidfuzz", "tfidf", "bert"]
    )
    compare.add_argument("--tfidf-ngrams", default="2-4")
    compare.add_argument("--tokenizer", default="char", choices=["char", "path"])
    compare.add_argument("--depth-limit", type=int, default=0)
    compare.add_argument("--workers", type=int, default=min(os.cpu_count() or 1, 6))
    compare.add_argument("--color", action="store_true")
    compare.set_defaults(func=cmd_compare)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "profile" and args.run_id is None:
        args.run_id = new_run_id("profile")
    if args.command == "compare" and args.run_id is None and (args.old or args.new):
        args.run_id = "manual"
    args.func(args)


if __name__ == "__main__":
    main()
