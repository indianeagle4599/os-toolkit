"""
cache.py - Similarity cache helpers.

Features:
- Run-local cache directories
- Compressed NumPy similarity matrix storage
"""

import hashlib
import os

from migration_pro.io.artifacts import cache_dir_for, run_dir_for_paths


def get_cache_folder(path1, path2, run_dir=None):
    def hash_path(path):
        try:
            mtime = os.path.getmtime(path)
        except FileNotFoundError:
            mtime = 0
        return f"{path}_{mtime}"

    hash_input = (hash_path(path1) + hash_path(path2)).encode("utf-8")
    digest = hashlib.md5(hash_input).hexdigest()
    run_dir = run_dir or run_dir_for_paths(path1, path2)
    cache_dir = os.path.join(cache_dir_for(run_dir), digest)
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def save_similarity_matrix(matrix, path):
    import numpy as np

    path = path.replace(".npy", ".npz")
    np.savez_compressed(path, sim=matrix.astype(np.float16))


def load_similarity_matrix(path):
    import numpy as np

    path = path.replace(".npy", ".npz")
    with np.load(path) as data:
        return data["sim"].astype(np.float32)
