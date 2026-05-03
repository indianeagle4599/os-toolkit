"""
Superfast File Transfer Pro — parallel copy with pre-scan, strategies, live progress,
resume/dry-run, optional config defaults, and adaptive worker tuning.
"""

import os
import sys
import shutil
import argparse
import multiprocessing
import queue as stdlib_queue
import threading
import time
from typing import Dict, List, Optional, Tuple

try:
    import file_transfer_config as _cfg
except ImportError:
    _cfg = None


def _cfg_get(attr: str, fallback):
    if _cfg is not None:
        val = getattr(_cfg, attr, None)
        if val is not None and val != "":
            return val
    return fallback


def _format_eta(eta: int) -> str:
    if eta < 3600:
        return f"{eta // 60}:{eta % 60:02d}"
    if eta < 86400:
        return f"{eta // 3600}h {(eta % 3600) // 60:02d}m"
    if eta < 604800:
        return f"{eta // 86400}d {(eta % 86400) // 3600:02d}h"
    if eta < 31536000:
        return f"{eta // 604800}w {(eta % 604800) // 86400}d"
    return f"{eta // 31536000}y {(eta % 31536000) // 86400}d"


def human_readable_size(size_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            break
        if unit != "TB":
            size_bytes /= 1024.0
    return f"{size_bytes:.1f} {unit}"


def extended_path(path: str) -> str:
    """Prefix path for Windows extended-length path support (>260 chars)."""
    if os.name == "nt" and not path.startswith("\\\\?\\"):
        path = "\\\\?\\" + os.path.abspath(path)
    return path


def prescan_source(source_dir: str) -> List[Tuple[str, str, int]]:
    files = []
    for root, _, filenames in os.walk(source_dir):
        for filename in filenames:
            full_path = extended_path(os.path.join(root, filename))
            rel = os.path.relpath(full_path, extended_path(source_dir))
            try:
                size = os.path.getsize(full_path)
            except OSError:
                size = 0
            files.append((full_path, rel, size))
    return files


def apply_strategy(
    files: List[Tuple[str, str, int]], strategy: str
) -> List[Tuple[str, str, int]]:
    if strategy == "smallest-first":
        return sorted(files, key=lambda x: x[2])
    if strategy == "largest-first":
        return sorted(files, key=lambda x: x[2], reverse=True)
    # balanced: interleave smallest and largest so workers see a continuous mix
    asc = sorted(files, key=lambda x: x[2])
    result, left, right = [], 0, len(asc) - 1
    toggle = True
    while left <= right:
        result.append(asc[left] if toggle else asc[right])
        left, right = (left + 1, right) if toggle else (left, right - 1)
        toggle = not toggle
    return result


def _scan_size_buckets(
    files: List[Tuple[str, str, int]],
) -> Tuple[int, int, int, int, int, int]:
    """One pass: counts and byte sums for <1MB, 1–100MB, >=100MB buckets."""
    ns = ss = nm = sm = nl = sl = 0
    for _, _, s in files:
        if s < 1_000_000:
            ns += 1
            ss += s
        elif s < 100_000_000:
            nm += 1
            sm += s
        else:
            nl += 1
            sl += s
    return ns, ss, nm, sm, nl, sl


def _probe_sequence(max_workers: int) -> List[int]:
    # Ascending worker counts: small tests (few files, short drains) before the max-W run.
    raw = [max(1, max_workers // 4), max(1, max_workers // 2), max_workers]
    seen, result = set(), []
    for w in raw:
        if w not in seen:
            seen.add(w)
            result.append(w)
    return result


def _choose_optimal(probe_results: List[Tuple[int, float]]) -> int:
    if not probe_results:
        return 1
    best = max(t for _, t in probe_results)
    good = [w for w, t in probe_results if t >= best * 0.90]
    return min(good)  # prefer fewer workers when throughput is equivalent


# Lower cap = shorter drain before/inside probe (less queued work vs worker starvation).
_IN_FLIGHT_MULT = 2


def copy_worker(
    args: Tuple[str, str, int, bool],
) -> Tuple[str, int, Optional[str]]:
    """Copy one file. Returns (status, size, error_or_None)."""
    src_path, dst_path, src_size, dry_run = args
    try:
        if os.path.exists(dst_path) and os.path.getsize(dst_path) == src_size:
            return ("skipped", src_size, None)
        if dry_run:
            return ("dryrun", src_size, None)
        dst_dir = os.path.dirname(dst_path)
        if dst_dir:
            os.makedirs(dst_dir, exist_ok=True)
        shutil.copy2(src_path, dst_path)
        return ("copied", src_size, None)
    except Exception as e:
        return ("failed", src_size, str(e))


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
    if copy_speed > 0 and remaining > 0:
        eta_str = _format_eta(int(remaining / copy_speed))
    else:
        eta_str = "--:--"
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
):
    if not os.path.exists(source_dir):
        print(f"ERROR: Source directory does not exist: {source_dir}")
        return

    if verbosity >= 1:
        print(f"\nScanning {source_dir} ...")

    files = prescan_source(source_dir)
    total_files = len(files)
    if total_files == 0:
        print(f"WARNING: No files found in {source_dir}")
        return

    total_bytes = sum(f[2] for f in files)

    # probe_cost = sum(probe_seq); e.g. W=14 → 3+7+14 = 24 files (ascending ladder, no lone 1w test).
    probe_seq = _probe_sequence(workers)
    probe_cost = sum(probe_seq)
    avg_bpf = total_bytes / total_files

    use_adaptive = (
        adaptive and not dry_run and workers > 1 and total_files >= probe_cost
    )

    if verbosity >= 1:
        ns, ss, nm, sm, nl, sl = _scan_size_buckets(files)
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
    }
    progress["adapt_state"] = "pending" if use_adaptive else "static"

    cancelled = False
    pool = None
    pool_workers = 0
    target_in_flight = 0

    def switch_pool(new_count: int):
        """Single source of truth for changing worker count: closes the old pool,
        opens a new one, and updates pool_workers / target_in_flight / progress."""
        nonlocal pool, pool_workers, target_in_flight
        if pool is not None:
            pool.close()
            pool.join()
        pool = multiprocessing.Pool(processes=new_count)
        pool_workers = new_count
        target_in_flight = new_count * _IN_FLIGHT_MULT
        progress["workers"] = new_count

    switch_pool(workers)
    q = stdlib_queue.Queue()
    submitted = 0
    collected = 0
    last_probe_time = 0.0  # wall clock of last run_probe; first window 5 s from start

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
            # Worker process died (rare); main exception path is handled in copy_worker.
            sz = worker_args[idx][2]
            q.put(("failed", sz, str(exc)))

        pool.apply_async(
            copy_worker,
            (worker_args[idx],),
            callback=q.put,
            error_callback=_err,
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

        optimal = _choose_optimal(measurements)
        if pool_workers != optimal:
            switch_pool(optimal)
        progress["adapt_state"] = "locked"

    try:
        while collected < total_files:
            # Feed: top up the pool's queue so workers never starve.
            while (
                submitted < total_files and (submitted - collected) < target_in_flight
            ):
                submit_next()

            # Collect: short timeout keeps Ctrl+C responsive (~0.5 s).
            collect_one(timeout=0.5)

            # Probe gate: one probe pass per run; locks after first.
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
        return

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


def main():
    print("Superfast File Transfer Pro | Pre-scan | Strategy | Live Progress | Resume")

    _workers_default = _cfg_get("WORKERS", multiprocessing.cpu_count() // 2)

    parser = argparse.ArgumentParser(
        description="Parallel directory copy with pre-scan, resume, and optional adaptive workers.",
        epilog="Optional file_transfer_config.py sets defaults (SOURCE, DEST, …); CLI wins.",
    )
    parser.add_argument(
        "--source", "-s", default=_cfg_get("SOURCE", ""), help="Source directory path"
    )
    parser.add_argument(
        "--dest", "-d", default=_cfg_get("DEST", ""), help="Destination directory path"
    )
    parser.add_argument(
        "--workers",
        "-w",
        type=int,
        default=_workers_default,
        help=f"Parallel worker processes (default: {_workers_default})",
    )
    parser.add_argument(
        "--verbosity",
        "-v",
        type=int,
        choices=[0, 1, 2],
        default=_cfg_get("VERBOSITY", 1),
        help="0=quiet, 1=normal (default), 2=verbose",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=_cfg_get("DRY_RUN", False),
        help="Simulate without copying files",
    )
    parser.add_argument(
        "--strategy",
        choices=["smallest-first", "largest-first", "balanced"],
        default=_cfg_get("STRATEGY", "balanced"),
        help="File scheduling strategy (default: balanced)",
    )
    parser.add_argument(
        "--adaptive",
        action="store_true",
        default=_cfg_get("ADAPTIVE", False),
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
