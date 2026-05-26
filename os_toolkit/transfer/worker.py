"""
worker — per-file copy tasks for multiprocessing pools.
"""

import os
import shutil
from typing import Optional, Tuple

from os_toolkit.transfer.verify import destination_matches_size

CopyResult = Tuple[str, int, Optional[str]]


def copy_worker(args: Tuple[str, str, int, bool]) -> CopyResult:
    src_path, dst_path, src_size, dry_run = args
    try:
        if destination_matches_size(dst_path, src_size):
            return ("skipped", src_size, None)
        if dry_run:
            return ("dryrun", src_size, None)
        dst_dir = os.path.dirname(dst_path)
        if dst_dir:
            os.makedirs(dst_dir, exist_ok=True)
        shutil.copy2(src_path, dst_path)
        return ("copied", src_size, None)
    except OSError as exc:
        return ("failed", src_size, str(exc))
