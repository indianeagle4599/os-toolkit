"""
Superfast File Transfer Pro — parallel copy with pre-scan, strategies, live progress,
resume/dry-run, optional config defaults, and adaptive worker tuning.
"""

import argparse
import multiprocessing

from os_toolkit.core.config import cfg_get
from os_toolkit.transfer.copy import parallel_copy

try:
    import file_transfer_config as _cfg
except ImportError:
    _cfg = None


def main():
    print("Superfast File Transfer Pro | Pre-scan | Strategy | Live Progress | Resume")

    workers_default = cfg_get(_cfg, "WORKERS", multiprocessing.cpu_count() // 2)

    parser = argparse.ArgumentParser(
        description="Parallel directory copy with pre-scan, resume, and optional adaptive workers.",
        epilog="Optional file_transfer_config.py sets defaults (SOURCE, DEST, …); CLI wins.",
    )
    parser.add_argument(
        "--source",
        "-s",
        default=cfg_get(_cfg, "SOURCE", ""),
        help="Source directory path",
    )
    parser.add_argument(
        "--dest",
        "-d",
        default=cfg_get(_cfg, "DEST", ""),
        help="Destination directory path",
    )
    parser.add_argument(
        "--workers",
        "-w",
        type=int,
        default=workers_default,
        help=f"Parallel worker processes (default: {workers_default})",
    )
    parser.add_argument(
        "--verbosity",
        "-v",
        type=int,
        choices=[0, 1, 2],
        default=cfg_get(_cfg, "VERBOSITY", 1),
        help="0=quiet, 1=normal (default), 2=verbose",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=cfg_get(_cfg, "DRY_RUN", False),
        help="Simulate without copying files",
    )
    parser.add_argument(
        "--strategy",
        choices=["smallest-first", "largest-first", "balanced"],
        default=cfg_get(_cfg, "STRATEGY", "balanced"),
        help="File scheduling strategy (default: balanced)",
    )
    parser.add_argument(
        "--adaptive",
        action="store_true",
        default=cfg_get(_cfg, "ADAPTIVE", False),
        help="Auto-tune worker count via timer-driven probing (default: off)",
    )

    args = parser.parse_args()

    if not args.source:
        parser.error("--source is required (or set SOURCE in file_transfer_config.py)")
    if not args.dest:
        parser.error("--dest is required (or set DEST in file_transfer_config.py)")

    parallel_copy(
        source_dir=args.source,
        destination_dir=args.dest,
        workers=args.workers,
        verbosity=args.verbosity,
        dry_run=args.dry_run,
        strategy=args.strategy,
        adaptive=args.adaptive,
    )


if __name__ == "__main__":
    main()
