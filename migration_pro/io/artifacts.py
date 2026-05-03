"""
artifacts.py - Migration run artifact helpers.

Features:
- Stable migration_runs directory resolution
- Run-local cache directory creation
- Minimal manifest writing
"""

import json
from datetime import datetime, timezone
from pathlib import Path


MIGRATION_ROOT = Path(__file__).resolve().parents[1]
RUNS_ROOT = MIGRATION_ROOT / "migration_runs"


def run_dir(run_id: str) -> str:
    path = RUNS_ROOT / run_id
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


def run_dir_for_paths(path1, path2, fallback: str = "manual") -> str:
    runs_root = RUNS_ROOT.resolve()
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


def cache_dir_for(run_path) -> str:
    path = Path(run_path) / "cache"
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


def write_manifest(run_path, data) -> str:
    path = Path(run_path) / "manifest.json"
    payload = {"updated_at_utc": datetime.now(timezone.utc).isoformat(), **data}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")
    return str(path)
