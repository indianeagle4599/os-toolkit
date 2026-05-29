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


_MERGE_DICT_KEYS = frozenset({"inputs", "outputs", "settings", "counts"})


def merge_manifest(existing: dict, update: dict) -> dict:
    """Shallow-merge top-level keys; deep-merge known nested dict fields."""
    merged = dict(existing)
    for key, value in update.items():
        if key in _MERGE_DICT_KEYS and isinstance(value, dict):
            nested = dict(merged.get(key) or {})
            nested.update(value)
            merged[key] = nested
        else:
            merged[key] = value
    return merged


def write_manifest(run_path: str, data: dict, *, merge: bool = False) -> str:
    path = Path(run_path) / "manifest.json"
    payload = merge_manifest(read_manifest(run_path), data) if merge else data
    payload = {"updated_at_utc": datetime.now(timezone.utc).isoformat(), **payload}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")
    return str(path)


def read_manifest(run_path: str) -> dict:
    path = Path(run_path) / "manifest.json"
    if not path.is_file():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def root_mtime(root: str) -> float:
    try:
        return os.path.getmtime(root)
    except OSError:
        return 0.0


def _profile_side_keys(prefix: str) -> tuple[str, str]:
    side = "old" if prefix.startswith("old") else "new"
    return f"{side}_root", f"{side}_root_mtime"


def profile_is_current(run_path: str, root: str, prefix: str) -> bool:
    """True when features CSV exists and root path/mtime match manifest."""
    root = os.path.abspath(root)
    features = os.path.join(run_path, f"{prefix}features.csv")
    if not os.path.isfile(features):
        return False
    inputs = read_manifest(run_path).get("inputs") or {}
    key_root, key_mtime = _profile_side_keys(prefix)
    if inputs.get(key_root) != root:
        return False
    return inputs.get(key_mtime) == root_mtime(root)


def ensure_profile(
    root: str, run_path: str, prefix: str = "", verbosity: int = 1
) -> str:
    """Profile root into run_path when missing or stale; return features CSV path."""
    from os_toolkit.analysis.profile import run_profile_to_dir

    root = os.path.abspath(root)
    if not os.path.isdir(root):
        raise NotADirectoryError(f"{root} is not a valid directory")

    os.makedirs(run_path, exist_ok=True)
    features_path = os.path.join(run_path, f"{prefix}features.csv")
    if profile_is_current(run_path, root, prefix):
        if verbosity >= 1:
            print(f"Profile cache hit: {features_path}")
        return features_path

    run_profile_to_dir(root, run_path, prefix=prefix, verbosity=verbosity)
    key_root, key_mtime = _profile_side_keys(prefix)
    features_path = os.path.join(run_path, f"{prefix}features.csv")
    write_manifest(
        run_path,
        {
            "command": "analyze.profile",
            "inputs": {key_root: root, key_mtime: root_mtime(root)},
            "outputs": {
                f"{prefix}profile": os.path.join(run_path, f"{prefix}profile.json"),
                f"{prefix}features": features_path,
            },
        },
        merge=True,
    )
    return features_path


def compare_run_id(old_root: str, new_root: str) -> str:
    pair = f"{os.path.abspath(old_root)}\0{os.path.abspath(new_root)}".encode("utf-8")
    return "compare_" + hashlib.sha256(pair).hexdigest()[:12]


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
