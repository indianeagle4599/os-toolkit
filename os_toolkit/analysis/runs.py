"""
runs — repo-root artifact directories, manifests, and compare caches.
"""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNS_ROOT = REPO_ROOT / "runs"


def ensure_runs_root() -> Path:
    RUNS_ROOT.mkdir(parents=True, exist_ok=True)
    return RUNS_ROOT


def run_dir(run_id: str) -> str:
    path = ensure_runs_root() / run_id
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


def new_run_id(prefix: str = "run") -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}_{stamp}"


def run_dir_for_paths(path1, path2, fallback: str = "manual") -> str:
    runs_root = ensure_runs_root().resolve()
    candidates = []

    for raw_path in (path1, path2):
        try:
            relative = Path(raw_path).resolve().relative_to(runs_root)
        except ValueError:
            return run_dir(fallback)
        if not relative.parts:
            return run_dir(fallback)
        candidates.append(runs_root / relative.parts[0])

    if candidates and candidates[0] == candidates[1]:
        candidates[0].mkdir(parents=True, exist_ok=True)
        return str(candidates[0])

    return run_dir(fallback)


def cache_dir_for(run_path: str) -> str:
    path = Path(run_path) / "cache"
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


def write_manifest(run_path: str, data: dict) -> str:
    path = Path(run_path) / "manifest.json"
    payload = {"updated_at_utc": datetime.now(timezone.utc).isoformat(), **data}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")
    return str(path)


def get_cache_folder(path1: str, path2: str, run_dir_path: Optional[str] = None) -> str:
    def hash_path(path: str) -> str:
        try:
            mtime = os.path.getmtime(path)
        except FileNotFoundError:
            mtime = 0
        return f"{path}_{mtime}"

    digest = hashlib.md5(
        (hash_path(path1) + hash_path(path2)).encode("utf-8")
    ).hexdigest()
    run_dir_path = run_dir_path or run_dir_for_paths(path1, path2)
    cache_dir = os.path.join(cache_dir_for(run_dir_path), digest)
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def save_similarity_matrix(matrix, path: str) -> None:
    import numpy as np

    path = path.replace(".npy", ".npz")
    np.savez_compressed(path, sim=matrix.astype(np.float16))


def load_similarity_matrix(path: str):
    import numpy as np

    path = path.replace(".npy", ".npz")
    with np.load(path) as data:
        return data["sim"].astype(np.float32)
