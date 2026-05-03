#!/usr/bin/env python3

"""
match.py - Folder profile matcher.

Features:
- Structure similarity with batched NumPy cosine scoring
- Optional name similarity backends
- Run-local cache and result exports
"""

import argparse
import json
import os
import time
from contextlib import contextmanager

from migration_pro.compare.filters import top_level_only
from migration_pro.io.artifacts import run_dir_for_paths, write_manifest
from migration_pro.io.cache import (
    get_cache_folder,
    load_similarity_matrix,
    save_similarity_matrix,
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
            "Missing matcher dependency. Install numpy, pandas, and tqdm before "
            "running profile comparison."
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
        sim = A_batch @ B_T
        sims.append(sim)

    return np.vstack(sims)


def ordered_results(filtered_results, matches):
    unmatched = [(i, j) for i, j in filtered_results if j is None]
    matched = [(i, j) for i, j in filtered_results if j is not None]
    return unmatched + sorted(matched, key=lambda x: matches[x[0]][0][1])


def match_candidates(matches, paths_old, paths_new):
    return [
        {
            "old_index": i,
            "old": paths_old[i],
            "matches": [
                {
                    "new_index": j,
                    "new": paths_new[j],
                    "score": round(score, 4),
                }
                for j, score in row
            ],
        }
        for i, row in enumerate(matches)
    ]


def print_summary(filtered_results, matches, paths_old, paths_new, color=False):
    print("\n📁 Final Match Results:")
    for i, j in ordered_results(filtered_results, matches):
        if j is None:
            red, reset = ("\033[91m", "\033[0m") if color else ("", "")
            print(f"{red}✗ {paths_old[i]} → No match above threshold{reset}")
        else:
            score = matches[i][0][1]
            green, reset = ("\033[92m", "\033[0m") if color else ("", "")
            print(f"{green}✅ {paths_old[i]} → {paths_new[j]} ({score:.2f}){reset}")


def export_results(filtered_results, matches, paths_old, paths_new, args, run_dir):
    txt_path = os.path.join(run_dir, "matches.txt")
    json_path = os.path.join(run_dir, "matches.json")
    summary = []
    unmatched = []

    with open(txt_path, "w", encoding="utf-8") as f:
        for i, j in ordered_results(filtered_results, matches):
            if j is None:
                f.write(f"✗ {paths_old[i]} → No match above threshold\n")
                unmatched.append(
                    {
                        "old_index": i,
                        "old": paths_old[i],
                        "best_score": (
                            round(matches[i][0][1], 4) if matches[i] else 0.0
                        ),
                    }
                )
            else:
                score = matches[i][0][1]
                f.write(f"✅ {paths_old[i]} → {paths_new[j]} ({score:.2f})\n")
                summary.append(
                    {
                        "old_index": i,
                        "old": paths_old[i],
                        "new_index": j,
                        "new": paths_new[j],
                        "score": round(score, 4),
                    }
                )

    counts = {
        "old_rows": len(paths_old),
        "new_rows": len(paths_new),
        "candidate_rows": sum(len(row) for row in matches),
        "summary_rows": len(summary),
    }
    settings = {
        "threshold": args.threshold,
        "topk": args.topk,
        "name_sim": args.name_sim,
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "inputs": {"old": args.old, "new": args.new},
                "settings": settings,
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
            "command": "compare.match",
            "inputs": {"old": args.old, "new": args.new},
            "outputs": {"matches_json": json_path, "matches_txt": txt_path},
            "settings": settings,
            "counts": {**counts, "unmatched_rows": len(unmatched)},
        },
    )

    print(f"\n[INFO] Exported match results to:\n  - {txt_path}\n  - {json_path}")


def cache_name(args):
    return (
        f"name_sim_{args.name_sim}_{args.tokenizer}_"
        f"{args.tfidf_ngrams}_{args.structure_filter}.npz"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Modular folder profile matcher with caching and multiple backends"
    )
    parser.add_argument("--old", required=True, help="Old profile CSV")
    parser.add_argument("--new", required=True, help="New profile CSV")
    parser.add_argument(
        "--threshold", type=float, default=0.7, help="Similarity threshold"
    )
    parser.add_argument("--topk", type=int, default=3, help="Top-K matches")
    parser.add_argument(
        "--batch-size", type=int, default=5000, help="Batch size for cosine sim"
    )
    parser.add_argument(
        "--structure-filter", type=float, default=0.4, help="Prune before name sim"
    )
    parser.add_argument(
        "--name-sim",
        default="tfidf",
        choices=["rapidfuzz", "tfidf", "bert"],
        help="Similarity method",
    )
    parser.add_argument(
        "--tfidf-ngrams", default="2-4", help="TF-IDF n-gram range (e.g. 2-4)"
    )
    parser.add_argument(
        "--tokenizer",
        default="char",
        choices=["char", "path"],
        help="TF-IDF tokenizer",
    )
    parser.add_argument(
        "--depth-limit", type=int, default=0, help="Folder depth limit for reporting"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=min(os.cpu_count() or 1, 6),
        help="Parallel workers",
    )
    parser.add_argument(
        "--device",
        default=None,
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--color", action="store_true", help="Enable colored output")

    args = parser.parse_args()
    if args.topk < 1:
        parser.error("--topk must be >= 1")
    if args.workers < 1:
        parser.error("--workers must be >= 1")

    load_match_dependencies()

    start_time = time.time()
    run_dir = run_dir_for_paths(args.old, args.new)

    print(
        f"[INFO] name-sim: {args.name_sim}, topK: {args.topk}, "
        f"threshold: {args.threshold}"
    )
    print(f"[INFO] Using run directory: {run_dir}")

    with timer("Load features"):
        df_old = load_features(args.old)
        df_new = load_features(args.new)
    if len(df_old) == 0 or len(df_new) == 0:
        raise SystemExit("Feature CSVs must contain at least one row.")
    args.topk = min(args.topk, len(df_new))

    with timer("Structure sim: normalize"):
        A = normalize_features(df_old, ["size_bytes", "files", "folders", "depth"])
        B = normalize_features(df_new, ["size_bytes", "files", "folders", "depth"])

    with timer("Structure sim: cosine batches"):
        structure_sim = compute_cosine_batches(A, B, batch_size=args.batch_size)
    mask = structure_sim > args.structure_filter

    cache_dir = get_cache_folder(args.old, args.new, run_dir=run_dir)
    name_cache_path = os.path.join(cache_dir, cache_name(args))

    if os.path.exists(name_cache_path):
        name_sim = load_similarity_matrix(name_cache_path)
        print(f"[CACHE] Loaded name similarity from {name_cache_path}")
    else:
        print("[INFO] Computing name similarity matrix...")
        if args.name_sim == "bert":
            print("[INFO] Checking for BERT model... will download if not present.")

        ngram_range = tuple(map(int, args.tfidf_ngrams.split("-")))
        from migration_pro.compare.similarity import NameSimilarity

        sim_engine = NameSimilarity(
            method=args.name_sim, ngram_range=ngram_range, tokenizer=args.tokenizer
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
        batch_size = 1000
        matches = []

        for i in tqdm(range(0, total, batch_size), desc="Top-k Filtering"):
            batch = final_matrix[i : i + batch_size]
            indices = np.argsort(-batch, axis=1)[:, : args.topk]
            values = np.take_along_axis(batch, indices, axis=1)
            for row_v, row_i in zip(values, indices):
                row = [
                    (int(row_i[j]), float(row_v[j]))
                    for j in range(args.topk)
                ]
                matches.append(row)

    print("[INFO] Performing top-level filtering...")
    with timer("Filter top-level groups"):
        filtered_results = top_level_only(
            matches,
            df_old["path"].tolist(),
            args.threshold,
            depth_limit=args.depth_limit,
            verbose=True,
            workers=args.workers,
        )

    print_summary(
        filtered_results,
        matches,
        df_old["path"].tolist(),
        df_new["path"].tolist(),
        color=args.color,
    )
    export_results(
        filtered_results,
        matches,
        df_old["path"].tolist(),
        df_new["path"].tolist(),
        args,
        run_dir,
    )

    print(f"\nDone in {time.time() - start_time:.2f} seconds.")


if __name__ == "__main__":
    main()
