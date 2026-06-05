"""
copy — directory copy with HDD/SSD paths and optional robocopy backend.
"""

from __future__ import annotations

import os
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from os_toolkit.core.format import format_progress_bar, human_readable_size
from os_toolkit.core.paths import extended_path, is_under


def _dest_cache(dest: str, resume: bool) -> dict[str, int]:
    if not resume or not os.path.isdir(dest):
        return {}
    from os_toolkit.analysis.usage import index_file_sizes

    return index_file_sizes(dest)


def _maybe_progress(
    files_done: int,
    total_files: int,
    bytes_done: int,
    bytes_total: int,
    elapsed: float,
    verbosity: int,
    last_at: float,
) -> float:
    if verbosity < 1:
        return last_at
    now = time.time()
    if files_done % 1000 == 0 or now - last_at >= 2.0:
        line = format_progress_bar(
            bytes_done, bytes_total, elapsed, files_done, total_files
        )
        sys.stdout.write(f"\r{line}  ")
        sys.stdout.flush()
        return now
    return last_at


def _print_transfer_summary(
    duration: float,
    dry_run: bool,
    copied: int,
    skipped: int,
    failed: int,
    dryrun_count: int,
    bytes_actually_copied: int,
    bytes_dryrun: int,
) -> None:
    avg_speed = (
        f"{human_readable_size(int(bytes_actually_copied / duration))}/s"
        if bytes_actually_copied > 0 and duration > 0
        else "--"
    )
    print(f"\nTransfer complete  - {duration:.1f} s\n")
    if dry_run:
        print(
            f"    {'Would copy':<12}: {dryrun_count:>6,} files  ({human_readable_size(bytes_dryrun)})"
        )
        print(f"    {'Skipped':<12}: {skipped:>6,} files  (already up to date)")
    else:
        print(
            f"    {'Copied':<12}: {copied:>6,} files  ({human_readable_size(bytes_actually_copied)})"
        )
        print(f"    {'Skipped':<12}: {skipped:>6,} files  (already up to date)")
        print(f"    {'Failed':<12}: {failed:>6,} files")
        print(f"    {'Avg speed':<12}: {avg_speed}")


def _source_has_files(source_dir: str) -> bool:
    for _, _, filenames in os.walk(source_dir):
        if filenames:
            return True
    return False


def _source_file_count(source_dir: str) -> int:
    return sum(len(fs) for _, _, fs in os.walk(source_dir))


def hdd_copy(
    src: str, dst: str, resume: bool = True, dry_run: bool = False, verbosity: int = 1
) -> bool:
    src, dst = os.path.abspath(src), os.path.abspath(dst)
    dest_sizes = _dest_cache(dst, resume)
    copied = skipped = failed = done = 0
    bytes_discovered = bytes_done_b = 0
    failures: list[tuple[str, str]] = []
    last_at, t0 = time.time(), time.time()
    for dirpath, _, filenames in os.walk(src):
        rel = os.path.relpath(dirpath, src)
        d = dst if rel == "." else os.path.join(dst, rel)
        os.makedirs(d, exist_ok=True)
        for f in filenames:
            sp = os.path.join(dirpath, f)
            src_size = 0
            if dest_sizes or verbosity >= 1:
                try:
                    src_size = os.stat(extended_path(sp)).st_size
                except OSError:
                    src_size = 0
            bytes_discovered += src_size
            if dest_sizes:
                rf = f if rel == "." else os.path.join(rel, f)
                try:
                    if dest_sizes.get(rf) == src_size:
                        skipped += 1
                        done += 1
                        bytes_done_b += src_size
                        last_at = _maybe_progress(
                            done,
                            0,
                            bytes_done_b,
                            bytes_discovered,
                            time.time() - t0,
                            verbosity,
                            last_at,
                        )
                        continue
                except OSError:
                    pass
            if not dry_run:
                try:
                    shutil.copy2(extended_path(sp), extended_path(os.path.join(d, f)))
                    copied += 1
                except OSError as exc:
                    failed += 1
                    failures.append((sp, str(exc)))
            else:
                copied += 1
            done += 1
            bytes_done_b += src_size
            last_at = _maybe_progress(
                done,
                0,
                bytes_done_b,
                bytes_discovered,
                time.time() - t0,
                verbosity,
                last_at,
            )
    if verbosity >= 1:
        sys.stdout.write("\n")
        print(
            f"done {time.time() - t0:.1f}s copied={copied} skipped={skipped} failed={failed}"
        )
    return failed == 0


def ssd_copy(
    src: str,
    dst: str,
    workers: int = 8,
    resume: bool = True,
    dry_run: bool = False,
    verbosity: int = 1,
) -> bool:
    src, dst = os.path.abspath(src), os.path.abspath(dst)
    dest_sizes = _dest_cache(dst, resume)
    pairs: list[tuple[str, str, int]] = []
    skipped = 0
    for dirpath, _, filenames in os.walk(src):
        rel = os.path.relpath(dirpath, src)
        for f in filenames:
            sp = os.path.join(dirpath, f)
            rf = f if rel == "." else os.path.join(rel, f)
            src_size = 0
            if dest_sizes or verbosity >= 1:
                try:
                    src_size = os.stat(extended_path(sp)).st_size
                except OSError:
                    src_size = 0
            if dest_sizes:
                try:
                    if dest_sizes.get(rf) == src_size:
                        skipped += 1
                        continue
                except OSError:
                    pass
            pairs.append((sp, extended_path(os.path.join(dst, rf)), src_size))
    total_files = skipped + len(pairs)
    total_bytes = sum(size for _, _, size in pairs)
    if dry_run:
        print(f"DRY-RUN would_copy={len(pairs)} skipped={skipped}")
        return True
    dirs = {os.path.dirname(dp) for _, dp, _ in pairs}
    for d in dirs:
        os.makedirs(d, exist_ok=True)
    copied = failed = 0
    done = skipped
    bytes_done_b = 0
    last_at, t0 = time.time(), time.time()

    def _copy_pair(pair: tuple[str, str, int]) -> None:
        nonlocal copied, failed, done, last_at, bytes_done_b
        s, d, size = pair
        try:
            shutil.copy2(s, d)
            copied += 1
        except OSError as exc:
            failed += 1
            if verbosity >= 2:
                print(f"FAILED: {s}: {exc}")
        done += 1
        bytes_done_b += size
        last_at = _maybe_progress(
            done,
            total_files,
            bytes_done_b,
            total_bytes,
            time.time() - t0,
            verbosity,
            last_at,
        )

    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(_copy_pair, pairs))
    if verbosity >= 1:
        sys.stdout.write("\n")
        print(
            f"done {time.time() - t0:.1f}s copied={copied} skipped={skipped} failed={failed}"
        )
    return failed == 0


def parallel_copy(
    source_dir: str,
    destination_dir: str,
    workers: int = 8,
    verbosity: int = 1,
    dry_run: bool = False,
    strategy: str = "balanced",
    adaptive: bool = False,
    hdd_max_workers: int = 1,
    unknown_media_max_workers: int = 2,
    hdd_file_count_threshold: int = 50_000,
    _dst_rotational: Optional[bool] = None,
) -> bool:
    """Copy source to destination. Returns False on validation failure."""
    del strategy, adaptive, hdd_max_workers, unknown_media_max_workers

    if not os.path.exists(source_dir):
        print(f"ERROR: Source directory does not exist: {source_dir}")
        return False
    if not os.path.isdir(source_dir):
        print(f"ERROR: Source is not a directory: {source_dir}")
        return False

    source_abs = os.path.abspath(source_dir)
    dest_abs = os.path.abspath(destination_dir)
    if is_under(dest_abs, source_abs):
        print(
            f"ERROR: Destination cannot be inside source:\n"
            f"  source: {source_dir}\n"
            f"  dest:   {destination_dir}"
        )
        return False
    if not _source_has_files(source_dir):
        print(f"WARNING: No files found in {source_dir}")
        return False

    from os_toolkit.core.storage import rotational_for_path
    from os_toolkit.transfer.robocopy import (
        robocopy_enabled,
        robocopy_on_path,
        run_robocopy_copy,
        should_use_robocopy,
    )

    if _dst_rotational is None:
        dst_rot = rotational_for_path(dest_abs)
    else:
        dst_rot = _dst_rotational
    is_slow_dest = dst_rot is not False

    if is_slow_dest:
        if (
            robocopy_enabled()
            and not dry_run
            and should_use_robocopy(
                dst_rotational=dst_rot,
                file_count=_source_file_count(source_dir),
                threshold=hdd_file_count_threshold,
                dry_run=dry_run,
                workers=1,
            )
        ):
            if verbosity >= 1:
                print("Robocopy backend: OS_TOOLKIT_ROBOCOPY=1")
            if robocopy_on_path():
                start_time = time.time()
                try:
                    rc, _out, robocopy_files, robocopy_bytes = run_robocopy_copy(
                        source_abs, destination_dir
                    )
                except FileNotFoundError:
                    if verbosity >= 0:
                        print(
                            "Warning: OS_TOOLKIT_ROBOCOPY=1 set but robocopy not found; "
                            "using walk path"
                        )
                else:
                    duration = time.time() - start_time
                    if rc in (2, 3) and verbosity >= 1:
                        print(f"Warning: robocopy exit {rc} (some files skipped)")
                    if rc >= 8:
                        print(f"ERROR: robocopy failed with exit code {rc}")
                        return False
                    _print_transfer_summary(
                        duration, False, robocopy_files, 0, 0, 0, robocopy_bytes, 0
                    )
                    return True
            elif verbosity >= 0:
                print(
                    "Warning: OS_TOOLKIT_ROBOCOPY=1 set but robocopy not found; "
                    "using walk path"
                )
        return hdd_copy(source_dir, destination_dir, dry_run=dry_run, verbosity=verbosity)

    return ssd_copy(
        source_dir,
        destination_dir,
        workers=max(1, workers),
        dry_run=dry_run,
        verbosity=verbosity,
    )
