"""
archive — smart zip public API and CLI orchestration.
"""

import os

from os_toolkit.core.format import human_readable_size
from os_toolkit.transfer.archive_scan import (
    base,
    choose_candidates,
    is_descendant,
    print_candidate,
    print_candidates,
    scan_root,
    settings,
)
from os_toolkit.transfer.archive_zip import run_zip_jobs


def _cli_error(parser, message: str) -> None:
    if parser is not None:
        parser.error(message)
    raise SystemExit(message)


def collect_decisions(candidates, cfg):
    approved = []
    print("\nSmart zip recommendations")
    if not candidates:
        print("  No strong zip candidates found.")
        return approved

    print("\nChoices: y=create zip, N=skip, s=skip remaining, q=quit.")
    if cfg["delete_originals"]:
        print("Delete prompts appear only after you approve a zip.")
    for index, candidate in enumerate(candidates, 1):
        print_candidate(index, len(candidates), candidate)
        answer = input("\nZip this folder? [y/N/s/q] ").strip().lower()
        if answer in {"q", "quit"}:
            return []
        if answer in {"s", "skip all", "skip-all"}:
            break
        if answer not in {"y", "yes"}:
            continue
        delete_original = False
        if cfg["delete_originals"]:
            delete_answer = input(
                "Delete original after newly created valid zip? [y/N] "
            )
            delete_original = delete_answer.strip().lower() in {"y", "yes"}
        approved.append((candidate, delete_original))
    return approved


def confirm_execute(candidates, cfg):
    """Single confirmation for --execute batch mode."""
    total_bytes = sum(c.stat.bytes for c in candidates)
    msg = (
        f"\nAbout to create {len(candidates):,} zip(s) "
        f"from ~{human_readable_size(total_bytes, extended_units=True)} of source data."
    )
    if cfg["delete_originals"]:
        msg += "\nOriginal folders will be DELETED after each valid zip."
    print(msg)
    answer = input("Proceed? [y/N] ").strip().lower()
    if answer not in {"y", "yes"}:
        print("Aborted.")
        return []
    return [(c, cfg["delete_originals"]) for c in candidates]


def run_smart_zip(args, config_module=None, parser=None):
    if not args.root:
        _cli_error(parser, "--root is required (or set ROOT in smart_zip_config.py)")
    if args.workers < 1:
        _cli_error(parser, "--workers must be >= 1")
    if args.interactive and args.execute:
        _cli_error(parser, "--interactive and --execute are mutually exclusive")

    is_dry_run = args.dry_run or not (args.interactive or args.execute)
    if args.dry_run and (args.interactive or args.execute):
        args.interactive = args.execute = False
        print("Note: --dry-run overrides --interactive/--execute.")

    ignored = [
        f
        for f, v in [
            ("--resume", args.resume),
            ("--overwrite", args.overwrite),
            ("--delete-originals", args.delete_originals),
        ]
        if v
    ]
    if is_dry_run and ignored:
        print(
            f"Warning: {', '.join(ignored)} ignored in dry-run mode; "
            f"use --interactive or --execute to create zips."
        )

    original_root = os.path.abspath(args.root)
    if (
        base(original_root) == "objects"
        and base(os.path.dirname(original_root)) == ".git"
    ):
        args.root = os.path.dirname(original_root.rstrip(os.sep))
        print(f"Root is .git/objects; scanning .git instead: {args.root}")
    cfg = settings(args, config_module)
    if not os.path.isdir(cfg["root"]):
        _cli_error(parser, f"--root is not a directory: {cfg['root']}")
    if cfg["output"]:
        out = os.path.normcase(os.path.abspath(cfg["output"]))
        rt = os.path.normcase(os.path.abspath(cfg["root"]))
        if out == rt or is_descendant(out, rt):
            _cli_error(parser, "--output must be outside --root")

    mode = (
        "Interactive"
        if args.interactive
        else "Batch execute" if args.execute else "Dry-run"
    )
    print(f"Smart Zip Pro | {mode} | sensitivity={cfg['sensitivity']}")

    stats = scan_root(cfg)
    candidates = choose_candidates(stats, cfg)

    if args.interactive:
        approved = collect_decisions(candidates, cfg)
        run_zip_jobs(approved, cfg)
    elif args.execute:
        print_candidates(candidates)
        if candidates:
            approved = confirm_execute(candidates, cfg)
            run_zip_jobs(approved, cfg)
    else:
        print_candidates(candidates)
        print("\nDry run only. Use --interactive or --execute to create zips.")
