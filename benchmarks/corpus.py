"""
corpus — sample profile directories from cache and compute corpus signatures.

Manifest schema: see fetch_corpus.py module docstring.
"""

import argparse
import atexit
import hashlib
import json
import os
import random
import shutil
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from benchmarks.datasets import DATASETS

BENCH_ROOT = Path(__file__).resolve().parent
CACHE_ROOT = BENCH_ROOT / "corpus" / "_cache"
CORPUS_ROOT = BENCH_ROOT / "corpus"
MANIFEST_PATH = BENCH_ROOT / "toolkit_manifest.json"
RESULTS_DIR = BENCH_ROOT / "results"
_CLEANUP_ROOTS: List[Path] = []

# Cache ceiling (~2.62 GB across 7 fetched datasets; see toolkit_manifest.json
# datasets[].size_bytes). Budgets above that (5G, 10G, large/*) sample until the
# cache is exhausted, so those profiles match each other and "all available data".
# 1G and 2G are meaningful with the current pool; larger sizes need more datasets.
RECIPE_SIZE_BUDGETS = {
    "1G": 1_000_000_000,
    "2G": 2_000_000_000,
    "5G": 5_000_000_000,
    "10G": 10_000_000_000,
}

_TINY_HEAVY_ORDER = [
    "linux_kernel_src",
    "newsgroups_20",
    "python_stdlib_lib",
    "gutenberg_top100",
    "scipy_lectures",
    "coco2017_val_subset",
    "librispeech_dev_clean",
]

_MEDIA_HEAVY_ORDER = [
    "coco2017_val_subset",
    "librispeech_dev_clean",
    "linux_kernel_src",
    "newsgroups_20",
    "python_stdlib_lib",
    "gutenberg_top100",
    "scipy_lectures",
]

# Cache sizes descending, interleaved large/small so no type dominates early fill.
_BALANCED_ORDER = [
    "linux_kernel_src",
    "scipy_lectures",
    "coco2017_val_subset",
    "gutenberg_top100",
    "librispeech_dev_clean",
    "newsgroups_20",
    "python_stdlib_lib",
]

_RECIPE_VARIANT_ORDERS = {
    "tiny-heavy": _TINY_HEAVY_ORDER,
    "media-heavy": _MEDIA_HEAVY_ORDER,
    "balanced": _BALANCED_ORDER,
}

PROFILE_RECIPES: Dict[str, List[str]] = {
    f"{size}/{variant}": order
    for size in RECIPE_SIZE_BUDGETS
    for variant, order in _RECIPE_VARIANT_ORDERS.items()
}

PROFILE_BUDGETS = {
    ("small", "code-heavy"): 500 * 1024 * 1024,
    ("small", "media-heavy"): int(1.5 * 1024**3),
    ("small", "mixed"): 2 * 1024**3,
    ("large", "code-heavy"): 5 * 1024**3,
    ("large", "media-heavy"): 15 * 1024**3,
    ("large", "mixed"): 20 * 1024**3,
}
for _size, _budget in RECIPE_SIZE_BUDGETS.items():
    for _variant in _RECIPE_VARIANT_ORDERS:
        PROFILE_BUDGETS[(_size, _variant)] = _budget


def require_corpus_dir(path: str) -> Path:
    """Boundary check: bench runners need an existing corpus directory."""
    root = Path(path)
    if not root.is_dir():
        raise SystemExit(f"corpus path not found or not a directory: {root}")
    return root


def load_manifest() -> dict:
    if MANIFEST_PATH.is_file():
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"datasets": {}, "profiles": {}}


def save_manifest(data: dict) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def warn_unavailable_datasets() -> None:
    manifest = load_manifest()
    bad = [
        name
        for name, row in manifest.get("datasets", {}).items()
        if row.get("status") != "ok"
    ]
    if not bad and not manifest.get("datasets"):
        bad = [d["name"] for d in DATASETS]
    if bad:
        print("WARNING: partial corpus pool — unavailable or unfetched datasets:")
        for name in bad[:20]:
            print(f"  - {name}")
        if len(bad) > 20:
            print(f"  ... and {len(bad) - 20} more")


def write_jsonl_record(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def track_scratch_cleanup(root: Path) -> None:
    if root not in _CLEANUP_ROOTS:
        _CLEANUP_ROOTS.append(root)


def remove_scratch_tree(root: Path) -> None:
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)


def _cleanup_tracked_scratch() -> None:
    for root in reversed(_CLEANUP_ROOTS):
        remove_scratch_tree(root)


atexit.register(_cleanup_tracked_scratch)


def bench_bytes_per_sec(dst: Path, elapsed: float, exit_status: int) -> int:
    """Throughput from bytes on dest after copy; zero when the run failed or timed out."""
    if exit_status != 0 or elapsed <= 0:
        return 0
    return int(corpus_tree_bytes(dst) / elapsed)


def corpus_tree_bytes(root: Path) -> int:
    if not root.exists():
        return 0
    return sum(p.stat().st_size for p in root.rglob("*") if p.is_file())


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def resolve_corpus_for_bench(
    profile: str,
    corpus_arg: str,
    ignore_manifest: bool,
    smoke_parent: Path,
    *,
    synthetic_files: int = 25,
    synthetic_size: int = 800,
) -> Tuple[Path, str]:
    if corpus_arg:
        root = require_corpus_dir(corpus_arg)
        signature = validate_profile(str(root), "", ignore_manifest)
        return root, signature
    info = build_synthetic_corpus(
        smoke_parent, files=synthetic_files, size=synthetic_size
    )
    root = Path(info["path"])
    signature = (
        "unverified"
        if ignore_manifest
        else validate_profile(str(root), info["signature"], False)
    )
    return root, signature


def run_timed(fn: Callable[[], object]) -> Tuple[float, int]:
    start = time.perf_counter()
    exit_status = 0
    try:
        result = fn()
        if isinstance(result, bool):
            exit_status = 0 if result else 1
        elif isinstance(result, int) and result != 0:
            exit_status = int(result)
    except Exception:
        exit_status = 1
    return time.perf_counter() - start, exit_status


def build_bench_record(
    *,
    tool: str,
    profile: str,
    scenario: str,
    scenario_id: str,
    device_tags: dict,
    signature: str,
    wall_time_sec: float,
    bytes_per_sec: int,
    exit_status: int,
    dst_bytes: int = 0,
    workers_requested: int | None = None,
    workers_effective: int | None = None,
) -> dict:
    record = {
        "tool": tool,
        "profile": profile,
        "scenario": scenario,
        "scenario_id": scenario_id,
        **device_tags,
        "corpus_signature": signature,
        "timestamp": utc_now_iso(),
        "wall_time_sec": round(wall_time_sec, 4),
        "bytes_per_sec": bytes_per_sec,
        "dst_bytes": dst_bytes,
        "exit_status": exit_status,
    }
    if workers_requested is not None:
        record["workers_requested"] = workers_requested
    if workers_effective is not None:
        record["workers_effective"] = workers_effective
    return record


def default_transfer_tools() -> List[str]:
    tools = ["os_toolkit.transfer", "stdlib.copytree"]
    if shutil.which("rsync"):
        tools.append("rsync")
    if os.name == "nt":
        tools.append("robocopy")
    return tools


def corpus_signature(files: List[Tuple[str, int]]) -> str:
    payload = "|".join(f"{rel}:{size}" for rel, size in sorted(files))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _cache_file_usable(path: Path) -> bool:
    if path.name == ".complete":
        return False
    parts = path.relative_to(CACHE_ROOT).parts
    if not parts:
        return False
    top = parts[0]
    if "_staging" in parts:
        return False
    if top.endswith("_extracted"):
        return True
    if top == "gutenberg_top100":
        return True
    return False


def _dataset_label(cache_rel: str) -> str:
    top = cache_rel.split("/")[0]
    if top.endswith("_extracted"):
        return top[: -len("_extracted")]
    return top


def list_cache_files() -> List[Tuple[Path, int]]:
    rows = []
    if not CACHE_ROOT.is_dir():
        return rows
    for path in CACHE_ROOT.rglob("*"):
        if not path.is_file() or not _cache_file_usable(path):
            continue
        try:
            rows.append((path, path.stat().st_size))
        except OSError:
            pass
    return rows


def _emit(msg: str, quiet: bool) -> None:
    if not quiet:
        print(msg, flush=True)


def _emit_error(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def _fmt_bytes(n: int) -> str:
    value = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024.0 or unit == "TB":
            if unit == "B":
                return f"{int(value)}{unit}"
            return f"{value:.1f}{unit}"
        value /= 1024.0
    return f"{n}B"


def sample_profile(
    tier: str,
    sub: str,
    seed: int = 42,
    dest: Path = None,
    quiet: bool = False,
) -> Dict:
    key = f"{tier}/{sub}"
    dest = dest or CORPUS_ROOT / tier / sub
    dest.mkdir(parents=True, exist_ok=True)

    by_dataset: Dict[str, List[Tuple[Path, int]]] = defaultdict(list)
    for src, size in list_cache_files():
        rel = str(src.relative_to(CACHE_ROOT)).replace("\\", "/")
        by_dataset[_dataset_label(rel)].append((src, size))

    rng = random.Random(seed)

    # Reproducibility: recipe profiles use fixed dataset order (PROFILE_RECIPES);
    # legacy profiles shuffle dataset labels. File order within each dataset is
    # always rng.shuffle(files) with seed. Same recipe + seed + unchanged cache
    # => identical corpus content and signature every run.
    recipe = PROFILE_RECIPES.get(key)
    if recipe is not None:
        budget = PROFILE_BUDGETS[(tier, sub)]
        labels = [label for label in recipe if label in by_dataset]
    else:
        budget = PROFILE_BUDGETS.get((tier, sub), PROFILE_BUDGETS[("small", "mixed")])
        labels = list(by_dataset.keys())
        rng.shuffle(labels)

    picked: List[Tuple[str, int]] = []
    total = 0
    for label in labels:
        if total >= budget:
            break
        ds_files = 0
        ds_bytes = 0
        files = by_dataset[label][:]
        rng.shuffle(files)
        for src, size in files:
            if total >= budget:
                break
            rel = str(src.relative_to(CACHE_ROOT)).replace("\\", "/")
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                try:
                    shutil.copy2(src, target)
                except OSError as exc:
                    _emit_error(f"  [{label}] skip {rel}: {exc}")
                    continue
            try:
                on_disk = target.stat().st_size
            except OSError as exc:
                _emit_error(f"  [{label}] skip {rel}: {exc}")
                continue
            picked.append((rel, on_disk))
            total += on_disk
            ds_files += 1
            ds_bytes += on_disk
        if ds_files:
            _emit(
                f"  {label:28} {ds_files:>7,} files {_fmt_bytes(ds_bytes):>12}",
                quiet,
            )

    sig = corpus_signature(picked) if picked else "empty"
    info = {
        "signature": sig,
        "files": [r for r, _ in picked],
        "total_bytes": total,
        "sampled_at": datetime.now(timezone.utc).isoformat(),
    }
    manifest = load_manifest()
    manifest.setdefault("profiles", {})[key] = info
    save_manifest(manifest)

    _emit(f"Results: {dest}", quiet)
    return {"path": str(dest), "signature": sig, "total_bytes": total, "files": picked}


def build_synthetic_corpus(root: Path, files: int = 20, size: int = 1024) -> Dict:
    """Tiny tree for runner smoke tests (no network fetch)."""
    root.mkdir(parents=True, exist_ok=True)
    picked = []
    for i in range(files):
        rel = f"bin/file_{i:03d}.dat"
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x" * size)
        picked.append((rel, size))
    sig = corpus_signature(picked)
    return {
        "path": str(root),
        "signature": sig,
        "total_bytes": files * size,
        "files": picked,
    }


def validate_profile(profile_path: str, signature: str, ignore_manifest: bool) -> str:
    if ignore_manifest:
        return "unverified"
    manifest = load_manifest()
    for prof in manifest.get("profiles", {}).values():
        if prof.get("signature") == signature:
            return signature
    root = Path(profile_path)
    files = []
    for p in root.rglob("*"):
        if p.is_file():
            rel = str(p.relative_to(root)).replace("\\", "/")
            files.append((rel, p.stat().st_size))
    return corpus_signature(files)


def _profile_summary(tier: str, sub: str, info: dict) -> dict:
    files = info.get("files") or []
    return {
        "profile": f"{tier}/{sub}",
        "path": info["path"],
        "signature": info["signature"],
        "total_bytes": info["total_bytes"],
        "file_count": len(files),
    }


def main():
    recipe_profiles = sorted(PROFILE_RECIPES.keys())
    recipe_help = ", ".join(recipe_profiles)
    parser = argparse.ArgumentParser(
        description="Sample benchmark corpus profiles.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Recipe profiles (fixed dataset order, reproducible with --seed):\n  "
            + "\n  ".join(recipe_profiles)
            + "\n\nLegacy profiles: small/{code-heavy,media-heavy,mixed}, "
            "large/{code-heavy,media-heavy,mixed}"
        ),
    )
    parser.add_argument(
        "--tier",
        default="1G",
        help="Profile tier (1G|2G|5G|10G or small|large; default: 1G)",
    )
    parser.add_argument(
        "--sub",
        default="balanced",
        help=(
            "Profile variant (tiny-heavy|media-heavy|balanced or "
            "code-heavy|media-heavy|mixed; default: balanced)"
        ),
    )
    parser.add_argument(
        "--profile",
        default="",
        help=f"Full profile name e.g. 1G/balanced, small/mixed. Recipes: {recipe_help}",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--synthetic", action="store_true", help="Build tiny smoke tree only"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress output (errors still print to stderr)",
    )
    args = parser.parse_args()

    if args.profile:
        tier, sub = args.profile.split("/", 1)
    else:
        tier, sub = args.tier, args.sub

    if args.synthetic:
        dest = CORPUS_ROOT / tier / sub / "_smoke"
        info = build_synthetic_corpus(dest)
        print(json.dumps(_profile_summary(tier, sub, info), indent=2))
        return

    info = sample_profile(tier, sub, seed=args.seed, quiet=args.quiet)
    print(json.dumps(_profile_summary(tier, sub, info), indent=2))


if __name__ == "__main__":
    main()
