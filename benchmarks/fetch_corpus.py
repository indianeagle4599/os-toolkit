"""
fetch_corpus — download registry datasets into corpus/_cache and update manifest.

Feature: Fetch real corpus archives with size validation and extraction.
Must do: Reject undersized downloads; extract archives to *_extracted trees.
Must NOT: Mark ok without validation; leave redirect HTML as success.
"""

import argparse
import gzip
import hashlib
import json
import shutil
import sys
import tarfile
import zipfile
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

from benchmarks.corpus import (
    MANIFEST_PATH,
    corpus_tree_bytes,
    load_manifest,
    save_manifest,
    utc_now_iso,
)
from benchmarks.datasets import DATASETS

BENCH_ROOT = Path(__file__).resolve().parent
CACHE_ROOT = BENCH_ROOT / "corpus" / "_cache"
NOTICE_PATH = BENCH_ROOT.parent / "NOTICE.md"

tree_size_bytes = corpus_tree_bytes
_utc_now = utc_now_iso


def append_notice(entry: dict) -> None:
    if not NOTICE_PATH.is_file():
        return
    row = (
        f"| {entry['name']} | {entry.get('license_name', '')} | "
        f"{entry.get('license_url', '')} | {entry.get('attribution', '')} |"
    )
    text = NOTICE_PATH.read_text(encoding="utf-8")
    placeholder = "| _(none fetched yet)_ | | | |"
    if placeholder in text:
        text = text.replace(placeholder, row)
    elif row not in text:
        text = text.rstrip() + "\n" + row + "\n"
    NOTICE_PATH.write_text(text, encoding="utf-8")


def _archive_name(url: str) -> str:
    path = urlparse(url).path
    name = Path(path).name or "download.bin"
    return name


def _fail(record: dict, reason: str) -> dict:
    record["status"] = "failed"
    record["reason"] = reason
    print(f"[fail] {record.get('name', '?')}: {reason}")
    return record


def _remove_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    elif path.is_file():
        path.unlink(missing_ok=True)


def _download_file(url: str, dest: Path, session) -> int:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with session.get(url, stream=True, timeout=(30, 600)) as resp:
        if resp.status_code == 404:
            raise FileNotFoundError(f"HTTP 404 for {url}")
        resp.raise_for_status()
        with open(dest, "wb") as out:
            for chunk in resp.iter_content(chunk_size=65536):
                if chunk:
                    out.write(chunk)
    return dest.stat().st_size


def _tar_extractall(tf: tarfile.TarFile, path: Path) -> None:
    if sys.version_info >= (3, 12):
        tf.extractall(path, filter="data")
    else:
        tf.extractall(path)


def _extract_archive(archive: Path, staging: Path) -> None:
    staging.mkdir(parents=True, exist_ok=True)
    lower = archive.name.lower()
    if lower.endswith(".zip"):
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(staging)
    elif lower.endswith((".tar.gz", ".tgz")):
        with tarfile.open(archive, "r:gz") as tf:
            _tar_extractall(tf, staging)
    elif lower.endswith(".tar.xz"):
        with tarfile.open(archive, "r:xz") as tf:
            _tar_extractall(tf, staging)
    elif lower.endswith(".tar"):
        with tarfile.open(archive, "r:") as tf:
            _tar_extractall(tf, staging)
    elif lower.endswith(".gz") and not lower.endswith(".tar.gz"):
        out_name = archive.name[:-3] or "decompressed.bin"
        target = staging / out_name
        with gzip.open(archive, "rb") as src, open(target, "wb") as dst:
            shutil.copyfileobj(src, dst)
    else:
        raise ValueError(f"unsupported archive type: {archive.name}")


def _copy_children(src_dir: Path, dst_dir: Path) -> None:
    dst_dir.mkdir(parents=True, exist_ok=True)
    for child in src_dir.iterdir():
        dest = dst_dir / child.name
        if child.is_dir():
            shutil.copytree(child, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(child, dest)


def _promote_subdir(staging: Path, extract_root: Path, subdir: str) -> None:
    src = staging.joinpath(*subdir.strip("/").split("/"))
    if not src.exists():
        raise FileNotFoundError(f"extract subdir missing: {subdir}")
    if src.is_dir():
        _copy_children(src, extract_root)
    else:
        extract_root.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, extract_root / src.name)


def _finalize_extract(archive: Path, extract_root: Path, extract_subdir: str) -> None:
    staging = extract_root.parent / f"{extract_root.name}_staging"
    _remove_path(staging)
    _extract_archive(archive, staging)
    _remove_path(extract_root)
    if extract_subdir:
        _promote_subdir(staging, extract_root, extract_subdir)
    else:
        _copy_children(staging, extract_root)
    _remove_path(staging)


def _validate_tree_size(
    root: Path, minimum: int, record: dict, label: str
) -> Optional[dict]:
    size = tree_size_bytes(root)
    if size < minimum:
        _remove_path(root)
        return _fail(
            record,
            f"{label} size too small (got {size} bytes, expected {minimum} minimum)",
        )
    return None


def fetch_gutenberg(entry: dict, force: bool, session) -> dict:
    name = entry["name"]
    dest = CACHE_ROOT / name
    extract_marker = dest / ".complete"
    record = {
        "name": name,
        "status": "unavailable",
        "size_bytes": 0,
        "hash": "",
        "fetched_at": _utc_now(),
    }
    minimum = entry.get("expected_size_min", 0)
    urls = entry.get("urls") or []

    if extract_marker.is_file() and not force:
        record["status"] = "ok"
        record["size_bytes"] = tree_size_bytes(dest)
        record["hash"] = extract_marker.read_text(encoding="ascii").strip()
        return record

    _remove_path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    total = 0
    try:
        for url in urls:
            fname = Path(urlparse(url).path).name or "book.txt"
            target = dest / fname
            size = _download_file(url, target, session)
            total += size
        if minimum and total < minimum:
            _remove_path(dest)
            return _fail(
                record,
                f"size too small (got {total} bytes, expected {minimum} minimum)",
            )
        record["size_bytes"] = total
        record["hash"] = hashlib.sha256(f"{name}:{total}".encode()).hexdigest()
        extract_marker.write_text(record["hash"], encoding="ascii")
        record["status"] = "ok"
        append_notice(entry)
        print(f"[ok] {name}: {total} bytes ({len(urls)} files)")
    except Exception as exc:
        _remove_path(dest)
        return _fail(record, str(exc))
    return record


def fetch_archive(entry: dict, force: bool, session) -> dict:
    name = entry["name"]
    url = (entry.get("url") or "").strip()
    minimum = entry.get("expected_size_min", 0)
    extract_subdir = entry.get("extract_subdir", "")
    download_dir = CACHE_ROOT / name
    extract_root = CACHE_ROOT / f"{name}_extracted"
    marker = extract_root / ".complete"

    record = {
        "name": name,
        "status": "unavailable",
        "size_bytes": 0,
        "hash": "",
        "fetched_at": _utc_now(),
    }

    if not url:
        return _fail(record, "no download URL configured")

    if marker.is_file() and not force:
        record["status"] = "ok"
        record["size_bytes"] = tree_size_bytes(extract_root)
        record["hash"] = marker.read_text(encoding="ascii").strip()
        return record

    archive_path = download_dir / _archive_name(url)
    try:
        _remove_path(download_dir)
        _remove_path(extract_root)
        download_dir.mkdir(parents=True, exist_ok=True)
        archive_size = _download_file(url, archive_path, session)
        if archive_size < 1_000_000:
            _remove_path(download_dir)
            return _fail(
                record,
                f"download too small (got {archive_size} bytes, likely not a real archive)",
            )
        _finalize_extract(archive_path, extract_root, extract_subdir)
        _remove_path(download_dir)
        err = _validate_tree_size(extract_root, minimum, record, "extracted")
        if err:
            return err
        record["size_bytes"] = tree_size_bytes(extract_root)
        record["hash"] = hashlib.sha256(
            f"{name}:{record['size_bytes']}".encode()
        ).hexdigest()
        marker.write_text(record["hash"], encoding="ascii")
        record["status"] = "ok"
        append_notice(entry)
        print(
            f"[ok] {name}: archive {archive_size} bytes, tree {record['size_bytes']} bytes"
        )
    except Exception as exc:
        _remove_path(download_dir)
        _remove_path(extract_root)
        return _fail(record, str(exc))
    return record


def fetch_one(entry: dict, force: bool) -> dict:
    name = entry["name"]
    try:
        import requests
    except ImportError:
        print(f"[skip] {name}: requests not installed (just install bench)")
        return {
            "name": name,
            "status": "unavailable",
            "size_bytes": 0,
            "hash": "",
            "fetched_at": _utc_now(),
            "reason": "requests not installed",
        }

    session = requests.Session()
    session.headers.update(
        {"User-Agent": "os-toolkit-benchmark-fetch/1.0 (local corpus cache)"}
    )

    if entry.get("urls"):
        return fetch_gutenberg(entry, force, session)
    return fetch_archive(entry, force, session)


def main():
    parser = argparse.ArgumentParser(description="Fetch benchmark corpus datasets.")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--only", action="append", default=[])
    args = parser.parse_args()

    CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()
    manifest.setdefault("datasets", {})
    selected = DATASETS
    if args.only:
        names = set(args.only)
        selected = [d for d in DATASETS if d["name"] in names]

    for entry in selected:
        manifest["datasets"][entry["name"]] = fetch_one(entry, args.force)

    save_manifest(manifest)
    print(f"Manifest written: {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
