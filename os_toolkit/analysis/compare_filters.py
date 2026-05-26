"""
compare_filters — top-level grouping for folder match summaries.
"""

from collections import defaultdict
import multiprocessing

from os_toolkit.core.paths import path_parts


def _evaluate_group(args):
    indices, matches, threshold = args
    best = (indices[0], None, 0.0)
    for i in indices:
        row = matches[i]
        if row and row[0][1] > best[2]:
            best = (i, row[0][0], row[0][1])
    return (best[0], best[1] if best[2] >= threshold else None)


def top_level_only(
    matches, paths_old, threshold, depth_limit=0, verbose=False, workers=4
):
    grouped_by_root = defaultdict(list)

    for i, path in enumerate(paths_old):
        parts = path_parts(path)
        key = tuple(parts[: 1 + depth_limit])
        grouped_by_root[key].append(i)

    grouped_args = [
        (indices, matches, threshold) for indices in grouped_by_root.values()
    ]

    if verbose:
        print(
            f"[INFO] Grouped {len(paths_old)} paths into "
            f"{len(grouped_by_root)} top-level groups"
        )

    if workers <= 1 or len(grouped_args) < 2:
        return [_evaluate_group(args) for args in grouped_args]

    if verbose:
        print(f"[INFO] Evaluating groups in parallel with {workers} workers...")

    with multiprocessing.Pool(processes=workers) as pool:
        return pool.map(_evaluate_group, grouped_args)
