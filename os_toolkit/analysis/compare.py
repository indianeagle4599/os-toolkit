"""
compare — inter-root profile comparison (structure + name similarity).
"""

import json
import os
import time
from contextlib import contextmanager
from types import SimpleNamespace

from os_toolkit.analysis.compare_filters import top_level_only
from os_toolkit.analysis.name_similarity import NameSimilarity
from os_toolkit.analysis.runs import (
    get_cache_folder,
    load_similarity_matrix,
    run_dir_for_paths,
    save_similarity_matrix,
    write_manifest,
)

pd = None
np = None
tqdm = None


def load_match_dependencies():
    global pd, np, tqdm
    try:
        import numpy as _np
        import pandas as _pd
        from tqdm import tqdm as _tqdm
    except ImportError as exc:
        raise SystemExit(
            "Missing compare dependency. Install numpy, pandas, and tqdm."
        ) from exc
    np = _np
    pd = _pd
    tqdm = _tqdm


@contextmanager
def timer(msg):
    start = time.perf_counter()
    yield
    end = time.perf_counter()
    print(f"[TIMER] {msg}: {end - start:.2f}s")


def load_features(csv_path):
    df = pd.read_csv(csv_path)
    df["size_bytes"] = df["size_bytes"].astype(float)
    df["files"] = df["files"].astype(int)
    df["folders"] = df["folders"].astype(int)
    df["depth"] = df["depth"].astype(int)
    return df


def normalize_features(df, cols):
    x = df[cols].to_numpy(dtype=np.float32)
    x = (x - x.mean(axis=0)) / (x.std(axis=0) + 1e-8)
    return x / (np.linalg.norm(x, axis=1, keepdims=True) + 1e-8)


def compute_cosine_batches(A, B, batch_size=10000):
    B_T = B.T
    sims = []
    print(f"[INFO] Computing cosine similarity in batches of {batch_size}...")
    for i in tqdm(range(0, A.shape[0], batch_size), desc="Structure Similarity"):
        A_batch = A[i : i + batch_size]
        sims.append(A_batch @ B_T)
    return np.vstack(sims)


def ordered_results(filtered_results, matches):
    unmatched = [(i, j) for i, j in filtered_results if j is None]
    matched = [(i, j) for i, j in filtered_results if j is not None]
    return unmatched + sorted(matched, key=lambda x: matches[x[0]][0][1])


def _match_rows(filtered_results, matches, paths_old, paths_new):
    """Yield match rows for console and file export (single source of truth)."""
    for i, j in ordered_results(filtered_results, matches):
        old_path = paths_old[i]
        if j is None:
            yield {
                "kind": "unmatched",
                "old_index": i,
                "old": old_path,
                "line": f"X {old_path} -> No match above threshold",
                "best_score": round(matches[i][0][1], 4) if matches[i] else 0.0,
            }
        else:
            score = matches[i][0][1]
            yield {
                "kind": "matched",
                "old_index": i,
                "old": old_path,
                "new_index": j,
                "new": paths_new[j],
                "score": round(score, 4),
                "line": f"OK {old_path} -> {paths_new[j]} ({score:.2f})",
            }


def match_candidates(matches, paths_old, paths_new):
    return [
        {
            "old_index": i,
            "old": paths_old[i],
            "matches": [
                {"new_index": j, "new": paths_new[j], "score": round(score, 4)}
                for j, score in row
            ],
        }
        for i, row in enumerate(matches)
    ]


def print_summary(filtered_results, matches, paths_old, paths_new, color=False):
    print("\nFinal Match Results:")
    for row in _match_rows(filtered_results, matches, paths_old, paths_new):
        if row["kind"] == "unmatched":
            red, reset = ("\033[91m", "\033[0m") if color else ("", "")
            print(f"{red}{row['line']}{reset}")
        else:
            green, reset = ("\033[92m", "\033[0m") if color else ("", "")
            print(f"{green}{row['line']}{reset}")


def export_results(filtered_results, matches, paths_old, paths_new, settings, run_dir):
    txt_path = os.path.join(run_dir, "matches.txt")
    json_path = os.path.join(run_dir, "matches.json")
    summary = []
    unmatched = []

    with open(txt_path, "w", encoding="utf-8") as f:
        for row in _match_rows(filtered_results, matches, paths_old, paths_new):
            f.write(row["line"] + "\n")
            if row["kind"] == "unmatched":
                unmatched.append(
                    {
                        "old_index": row["old_index"],
                        "old": row["old"],
                        "best_score": row["best_score"],
                    }
                )
            else:
                summary.append(
                    {
                        "old_index": row["old_index"],
                        "old": row["old"],
                        "new_index": row["new_index"],
                        "new": row["new"],
                        "score": row["score"],
                    }
                )

    counts = {
        "old_rows": len(paths_old),
        "new_rows": len(paths_new),
        "candidate_rows": sum(len(row) for row in matches),
        "summary_rows": len(summary),
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "inputs": {
                    "old_features": settings.old,
                    "new_features": settings.new,
                },
                "settings": {
                    "threshold": settings.threshold,
                    "topk": settings.topk,
                    "name_sim": settings.name_sim,
                },
                "counts": counts,
                "candidates": match_candidates(matches, paths_old, paths_new),
                "summary": summary,
                "unmatched": unmatched,
            },
            f,
            indent=2,
        )

    write_manifest(
        run_dir,
        {
            "command": "analyze.compare",
            "inputs": {
                "old_features": settings.old,
                "new_features": settings.new,
            },
            "outputs": {"matches_json": json_path, "matches_txt": txt_path},
            "settings": {
                "threshold": settings.threshold,
                "topk": settings.topk,
                "name_sim": settings.name_sim,
            },
            "counts": {**counts, "unmatched_rows": len(unmatched)},
        },
        merge=True,
    )
    print(f"\n[INFO] Exported match results to:\n  - {txt_path}\n  - {json_path}")


def cache_name(settings) -> str:
    return (
        f"name_sim_{settings.name_sim}_{settings.tokenizer}_"
        f"{settings.tfidf_ngrams}_{settings.structure_filter}.npz"
    )


def run_compare(settings) -> None:
    load_match_dependencies()
    start_time = time.time()
    run_path = getattr(settings, "run_path", None) or run_dir_for_paths(
        settings.old, settings.new, settings.run_id
    )

    print(
        f"[INFO] name-sim: {settings.name_sim}, topK: {settings.topk}, "
        f"threshold: {settings.threshold}"
    )
    print(f"[INFO] Using run directory: {run_path}")

    with timer("Load features"):
        df_old = load_features(settings.old)
        df_new = load_features(settings.new)
    if len(df_old) == 0 or len(df_new) == 0:
        raise SystemExit("Feature CSVs must contain at least one row.")

    topk = min(settings.topk, len(df_new))

    with timer("Structure sim: normalize"):
        cols = ["size_bytes", "files", "folders", "depth"]
        A = normalize_features(df_old, cols)
        B = normalize_features(df_new, cols)

    with timer("Structure sim: cosine batches"):
        structure_sim = compute_cosine_batches(A, B, batch_size=settings.batch_size)
    mask = structure_sim > settings.structure_filter

    cache_dir = get_cache_folder(settings.old, settings.new, run_dir_path=run_path)
    name_cache_path = os.path.join(cache_dir, cache_name(settings))

    if os.path.exists(name_cache_path):
        name_sim = load_similarity_matrix(name_cache_path)
        expected = (len(df_old), len(df_new))
        if name_sim.shape != expected:
            print(
                f"[WARN] Name-sim cache shape {name_sim.shape} != {expected}; recomputing."
            )
            os.remove(name_cache_path)
            name_sim = None
        else:
            print(f"[CACHE] Loaded name similarity from {name_cache_path}")
    else:
        name_sim = None

    if name_sim is None:
        print("[INFO] Computing name similarity matrix...")
        ngram_range = tuple(map(int, settings.tfidf_ngrams.split("-")))
        sim_engine = NameSimilarity(
            method=settings.name_sim,
            ngram_range=ngram_range,
            tokenizer=settings.tokenizer,
        )
        with timer("Name sim compute"):
            name_sim = sim_engine.compute(
                df_old["name"].tolist(),
                df_new["name"].tolist(),
                mask,
            )
        save_similarity_matrix(name_sim, name_cache_path)
        print(f"[CACHE] Saved name similarity to {name_cache_path}")

    with timer("Top-k filtering"):
        final_matrix = 0.6 * structure_sim + 0.4 * name_sim
        total = final_matrix.shape[0]
        batch = 1000
        matches = []
        for i in tqdm(range(0, total, batch), desc="Top-k Filtering"):
            chunk = final_matrix[i : i + batch]
            indices = np.argsort(-chunk, axis=1)[:, :topk]
            values = np.take_along_axis(chunk, indices, axis=1)
            for row_v, row_i in zip(values, indices):
                matches.append([(int(row_i[j]), float(row_v[j])) for j in range(topk)])

    print("[INFO] Performing top-level filtering...")
    with timer("Filter top-level groups"):
        filtered = top_level_only(
            matches,
            df_old["path"].tolist(),
            settings.threshold,
            depth_limit=settings.depth_limit,
            verbose=True,
            workers=settings.workers,
        )

    paths_old = df_old["path"].tolist()
    paths_new = df_new["path"].tolist()
    print_summary(filtered, matches, paths_old, paths_new, color=settings.color)
    export_results(filtered, matches, paths_old, paths_new, settings, run_path)
    print(f"\nDone in {time.time() - start_time:.2f} seconds.")


def settings_from_namespace(args) -> SimpleNamespace:
    run_id = getattr(args, "run_id", None) or "manual"
    return SimpleNamespace(
        old=args.old,
        new=args.new,
        run_id=run_id,
        run_path=getattr(args, "run_path", None),
        threshold=args.threshold,
        topk=args.topk,
        batch_size=args.batch_size,
        structure_filter=args.structure_filter,
        name_sim=args.name_sim,
        tfidf_ngrams=args.tfidf_ngrams,
        tokenizer=args.tokenizer,
        depth_limit=args.depth_limit,
        workers=args.workers,
        color=getattr(args, "color", False),
    )
