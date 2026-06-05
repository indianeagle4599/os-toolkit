"""
strategies — prescan, ordering, and adaptive probe helpers.

NOTE: prescan_source and apply_strategy are NOT used by the production copy path.
They exist only as test infrastructure.
effective_workers-related functions (probe_sequence, choose_optimal) are fully dead.
Candidate for cleanup in a future pass.
"""

import os
from typing import List, Tuple

from os_toolkit.core.paths import extended_path

FileEntry = Tuple[str, str, int]


def prescan_source(source_dir: str) -> List[FileEntry]:
    files = []
    source_root = os.path.abspath(source_dir)
    for root, _, filenames in os.walk(source_dir):
        for filename in filenames:
            plain_path = os.path.join(root, filename)
            full_path = extended_path(plain_path)
            rel = os.path.relpath(plain_path, source_root)
            try:
                size = os.path.getsize(full_path)
            except OSError:
                size = 0
            files.append((full_path, rel, size))
    return files


def apply_strategy(files: List[FileEntry], strategy: str) -> List[FileEntry]:
    if strategy == "smallest-first":
        return sorted(files, key=lambda x: x[2])
    if strategy == "largest-first":
        return sorted(files, key=lambda x: x[2], reverse=True)
    asc = sorted(files, key=lambda x: x[2])
    result, left, right = [], 0, len(asc) - 1
    toggle = True
    while left <= right:
        result.append(asc[left] if toggle else asc[right])
        left, right = (left + 1, right) if toggle else (left, right - 1)
        toggle = not toggle
    return result


def scan_size_buckets(files: List[FileEntry]) -> Tuple[int, int, int, int, int, int]:
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


def probe_sequence(max_workers: int) -> List[int]:
    raw = [max(1, max_workers // 4), max(1, max_workers // 2), max_workers]
    seen, result = set(), []
    for w in raw:
        if w not in seen:
            seen.add(w)
            result.append(w)
    return result


def choose_optimal(probe_results: List[Tuple[int, float]]) -> int:
    if not probe_results:
        return 1
    best = max(t for _, t in probe_results)
    good = [w for w, t in probe_results if t >= best * 0.90]
    return min(good)


IN_FLIGHT_MULT = 2
