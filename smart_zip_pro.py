"""
Smart Zip Pro - recommend and create useful folder-level zip archives.
Features:
- Find small-file-heavy folders worth packing
- Pick one clean folder level instead of noisy parent/child overlaps
- Dry-run by default; --interactive or --execute to create zips
"""

import argparse

from os_toolkit.core.config import cfg_get
from os_toolkit.transfer.archive import run_smart_zip

try:
    import smart_zip_config as _cfg
except ImportError:
    _cfg = None


def main():
    parser = argparse.ArgumentParser(
        description="Recommend useful folder-level zip archives.",
        epilog="Optional smart_zip_config.py sets defaults; CLI wins.",
    )
    parser.add_argument(
        "--root", default=cfg_get(_cfg, "ROOT", ""), help="Root folder to scan"
    )
    parser.add_argument(
        "--output",
        default=cfg_get(_cfg, "OUTPUT_DIR", ""),
        help="Zip output directory",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        default=cfg_get(_cfg, "INTERACTIVE", False),
        help="Prompt per candidate before zipping",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        default=cfg_get(_cfg, "EXECUTE", False),
        help="Zip all candidates after a single confirmation",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=cfg_get(_cfg, "DRY_RUN", False),
        help="Force recommendation-only mode (default when neither --interactive nor --execute)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        default=cfg_get(_cfg, "OVERWRITE", False),
    )
    parser.add_argument(
        "--resume", action="store_true", default=cfg_get(_cfg, "RESUME", False)
    )
    parser.add_argument(
        "--delete-originals",
        action="store_true",
        default=cfg_get(_cfg, "DELETE_ORIGINALS", False),
        help="Delete original folders after validated zip creation",
    )
    parser.add_argument(
        "--sensitivity",
        choices=["low", "normal", "high"],
        default=cfg_get(_cfg, "SENSITIVITY", "normal"),
        help="Recommendation sensitivity: low (strict), normal, high (aggressive)",
    )
    parser.add_argument(
        "--exclude",
        default="",
        help="Comma-separated folder names to skip during scan",
    )
    parser.add_argument("--workers", type=int, default=cfg_get(_cfg, "WORKERS", 1))
    parser.add_argument(
        "-v",
        "--verbosity",
        type=int,
        choices=[0, 1, 2],
        default=cfg_get(_cfg, "VERBOSITY", 1),
    )
    args = parser.parse_args()
    run_smart_zip(args, config_module=_cfg, parser=parser)


if __name__ == "__main__":
    main()
