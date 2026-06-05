"""
worker — per-file copy tasks for multiprocessing pools.

NOTE: This module is NOT used by the production copy path.
It exists only as test infrastructure for legacy pool-path tests.
Production copy uses hdd_copy/ssd_copy in os_toolkit/transfer/copy.py.
Candidate for removal when legacy tests are updated.
"""

import os
import shutil
from typing import Dict, Optional, Set, Tuple

CopyResult = Tuple[str, int, Optional[str]]

_dest_sizes: Dict[str, int] = {}
_created_dirs: Set[str] = set()


def reset_copy_caches(dest_sizes: Optional[Dict[str, int]] = None) -> None:
    """Load destination size index and clear per-run directory cache."""
    global _dest_sizes, _created_dirs
    _dest_sizes = dest_sizes if dest_sizes is not None else {}
    _created_dirs = set()


def init_copy_worker(dest_sizes: Dict[str, int]) -> None:
    """Pool initializer: each worker process gets its own cache copy."""
    reset_copy_caches(dest_sizes)


def _destination_matches_size(rel_path: str, expected_size: int) -> bool:
    cached = _dest_sizes.get(rel_path)
    return cached is not None and cached == expected_size


def _ensure_dir(dst_dir: str) -> None:
    if not dst_dir or dst_dir in _created_dirs:
        return
    os.makedirs(dst_dir, exist_ok=True)
    _created_dirs.add(dst_dir)


def copy_worker(args: Tuple[str, str, str, int, bool]) -> CopyResult:
    src_path, dst_path, rel_path, src_size, dry_run = args
    try:
        if _destination_matches_size(rel_path, src_size):
            return ("skipped", src_size, None)
        if dry_run:
            return ("dryrun", src_size, None)
        dst_dir = os.path.dirname(dst_path)
        _ensure_dir(dst_dir)
        shutil.copy2(src_path, dst_path)
        return ("copied", src_size, None)
    except OSError as exc:
        return ("failed", src_size, str(exc))
