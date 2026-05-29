"""
copy — parallel directory copy with adaptive workers and live progress.
"""

import multiprocessing
import os
import queue as stdlib_queue
import sys
import threading
import time
from typing import Dict, List, Optional, Tuple

from os_toolkit.core.format import format_eta, human_readable_size
from os_toolkit.core.paths import extended_path, is_under
from os_toolkit.transfer.strategies import (
    IN_FLIGHT_MULT,
    apply_strategy,
    choose_optimal,
    prescan_source,
    probe_sequence,
    scan_size_buckets,
)
from os_toolkit.transfer.worker import copy_worker


def _progress_line(
    bytes_resolved: int,
    total_bytes: int,
    files_done: int,
    total_files: int,
    elapsed: float,
    bytes_copied: int,
    workers: Optional[int] = None,
    adapt_state: Optional[str] = None,
    width: int = 20,
) -> str:
    pct = min(bytes_resolved, total_bytes) / total_bytes if total_bytes else 0
    filled = int(width * pct)
    bar = "#" * filled + "-" * (width - filled)
    copy_speed = bytes_copied / elapsed if elapsed > 0 and bytes_copied > 0 else 0
    remaining = total_bytes - min(bytes_resolved, total_bytes)
    eta_str = (
        format_eta(int(remaining / copy_speed))
        if copy_speed > 0 and remaining > 0
        else "--:--"
    )
    br_show = min(bytes_resolved, total_bytes)
    line = (
        f"[{bar}] {pct * 100:5.1f}%  |  "
        f"{human_readable_size(br_show)} / {human_readable_size(total_bytes)}  |  "
        f"{human_readable_size(int(copy_speed))}/s  |  "
        f"ETA {eta_str}  |  "
        f"{files_done}/{total_files} files"
    )
    if workers is not None and adapt_state is not None:
        line += f"  |  {workers}w {adapt_state}"
    return line


def _render_loop(progress: Dict, lock: threading.Lock) -> None:
    while progress["active"]:
        elapsed = time.time() - progress["start_time"]
        if elapsed > 0:
            line = _progress_line(
                progress["bytes_resolved"],
                progress["total_bytes"],
                progress["files_done"],
                progress["total_files"],
                elapsed,
                progress["bytes_copied"],
                workers=progress.get("workers"),
                adapt_state=progress.get("adapt_state"),
            )
            with lock:
                sys.stdout.write(f"\r{line}  ")
                sys.stdout.flush()
        time.sleep(0.25)


def parallel_copy(
    source_dir: str,
    destination_dir: str,
    workers: int = 8,
    verbosity: int = 1,
    dry_run: bool = False,
    strategy: str = "balanced",
    adaptive: bool = False,
) -> bool:
    """Copy source to destination. Returns False on validation failure."""
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

    if verbosity >= 1:
        print(f"\nScanning {source_dir} ...")

    files = prescan_source(source_dir)
    total_files = len(files)
    if total_files == 0:
        print(f"WARNING: No files found in {source_dir}")
        return False

    total_bytes = sum(f[2] for f in files)
    probe_seq = probe_sequence(workers)
    probe_cost = sum(probe_seq)
    avg_bpf = total_bytes / total_files

    use_adaptive = (
        adaptive and not dry_run and workers > 1 and total_files >= probe_cost
    )

    if verbosity >= 1:
        ns, ss, nm, sm, nl, sl = scan_size_buckets(files)
        print(
            f"\nSource  {source_dir}  - {total_files:,} files  ({human_readable_size(total_bytes)})"
        )
        print(f"  Small  < 1 MB    : {ns:6,} files  |  {human_readable_size(ss)}")
        print(f"  Medium 1-100 MB  : {nm:6,} files  |  {human_readable_size(sm)}")
        print(f"  Large  > 100 MB  : {nl:6,} files  |  {human_readable_size(sl)}")
        mode = "DRY RUN" if dry_run else "COPY"
        workers_label = f"{workers} (adaptive)" if use_adaptive else str(workers)
        print(f"\nStrategy: {strategy}  |  Workers: {workers_label}  |  Mode: {mode}")
        if adaptive and not use_adaptive:
            if dry_run:
                reason = "dry-run mode cannot measure real throughput"
            elif workers <= 1:
                reason = "only one worker count available"
            else:
                reason = f"need {probe_cost}+ files for a probe, have {total_files}"
            print(f"  (adaptive disabled: {reason})")
        print()

    files = apply_strategy(files, strategy)
    worker_args = [
        (src, extended_path(os.path.join(destination_dir, rel)), size, dry_run)
        for src, rel, size in files
    ]

    start_time = time.time()
    copied = skipped = failed = dryrun_count = 0
    bytes_actually_copied = 0
    bytes_dryrun = 0

    stdout_lock = threading.Lock()
    progress: Dict = {
        "bytes_resolved": 0,
        "bytes_copied": 0,
        "total_bytes": total_bytes,
        "files_done": 0,
        "total_files": total_files,
        "start_time": start_time,
        "active": True,
        "adapt_state": "pending" if use_adaptive else "static",
    }

    cancelled = False
    pool = None
    pool_workers = 0
    target_in_flight = 0

    def switch_pool(new_count: int):
        nonlocal pool, pool_workers, target_in_flight
        if pool is not None:
            pool.close()
            pool.join()
        pool = multiprocessing.Pool(processes=new_count)
        pool_workers = new_count
        target_in_flight = new_count * IN_FLIGHT_MULT
        progress["workers"] = new_count

    switch_pool(workers)
    q = stdlib_queue.Queue()
    submitted = 0
    collected = 0
    last_probe_time = 0.0

    render_thread = None
    if verbosity >= 1:
        render_thread = threading.Thread(
            target=_render_loop, args=(progress, stdout_lock), daemon=True
        )
        render_thread.start()

    def submit_next():
        nonlocal submitted
        idx = submitted

        def _err(exc):
            sz = worker_args[idx][2]
            q.put(("failed", sz, str(exc)))

        pool.apply_async(
            copy_worker, (worker_args[idx],), callback=q.put, error_callback=_err
        )
        submitted += 1

    def collect_one(timeout):
        nonlocal copied, skipped, failed, dryrun_count
        nonlocal bytes_actually_copied, bytes_dryrun, collected
        try:
            status, size, error = q.get(timeout=timeout)
        except stdlib_queue.Empty:
            return False
        collected += 1
        progress["bytes_resolved"] += size
        if status == "copied":
            copied += 1
            bytes_actually_copied += size
            progress["bytes_copied"] = bytes_actually_copied
        elif status == "skipped":
            skipped += 1
        elif status == "dryrun":
            dryrun_count += 1
            bytes_dryrun += size
        elif status == "failed":
            failed += 1
            if verbosity >= 2:
                with stdout_lock:
                    sys.stdout.write(f"\n  FAILED: {error}\n")
                    sys.stdout.flush()
        progress["files_done"] = copied + skipped + failed + dryrun_count
        return True

    def drain_in_flight():
        while collected < submitted:
            collect_one(timeout=0.5)

    def run_probe():
        progress["adapt_state"] = "probing"
        drain_in_flight()
        measurements: List[Tuple[int, float]] = []
        for w in probe_seq:
            test_size = min(w, total_files - submitted)
            if test_size <= 0:
                break
            switch_pool(w)
            t_start = time.time()
            bytes_before = bytes_actually_copied
            for _ in range(test_size):
                submit_next()
            drain_in_flight()
            elapsed_test = time.time() - t_start
            test_bytes = bytes_actually_copied - bytes_before
            measurements.append(
                (w, test_bytes / elapsed_test if elapsed_test > 0 else 0)
            )
        optimal = choose_optimal(measurements)
        if pool_workers != optimal:
            switch_pool(optimal)
        progress["adapt_state"] = "locked"

    try:
        while collected < total_files:
            while (
                submitted < total_files and (submitted - collected) < target_in_flight
            ):
                submit_next()
            collect_one(timeout=0.5)
            if use_adaptive and progress.get("adapt_state") == "pending":
                interval = 5.0
                if time.time() - max(last_probe_time, start_time) > interval:
                    elapsed = time.time() - start_time
                    throughput = bytes_actually_copied / elapsed if elapsed > 0 else 0
                    rem_bytes = max(0, total_bytes - progress["bytes_resolved"])
                    if total_files - submitted >= probe_cost and throughput > 0:
                        remaining_time = rem_bytes / throughput
                        probe_overhead = (
                            len(probe_seq) * 1.0 + probe_cost * avg_bpf / throughput
                        )
                        if remaining_time > probe_overhead * 5:
                            run_probe()
                            last_probe_time = time.time()
        if use_adaptive and progress.get("adapt_state") == "pending":
            progress["adapt_state"] = "locked"
    except KeyboardInterrupt:
        cancelled = True
        progress["active"] = False
        with stdout_lock:
            sys.stdout.write("\nStopping transfer...\n")
            sys.stdout.flush()
    finally:
        (pool.terminate if cancelled else pool.close)()
        pool.join()
        progress["active"] = False
        if render_thread:
            render_thread.join(timeout=0.5)
        if verbosity >= 1:
            with stdout_lock:
                sys.stdout.write("\n")

    if cancelled:
        print("Transfer cancelled.")
        return False

    duration = time.time() - start_time
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
    return True
