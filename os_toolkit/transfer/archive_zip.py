"""
archive_zip — zip creation, validation, and job execution.
"""

import multiprocessing
import os
import shutil
import sys
import time
import zipfile
from collections import Counter

from os_toolkit.core.format import human_readable_size
from os_toolkit.transfer.archive_scan import is_descendant, zip_non_dir_count


def _fail(candidate, error, **kw):
    return {
        "status": "failed",
        "path": candidate.stat.path,
        "zip_path": candidate.zip_path,
        "error": error,
        "valid": False,
        **kw,
    }


def archive_items(source_dir):
    parent = os.path.dirname(source_dir.rstrip(os.sep))
    for current, dirs, files in os.walk(source_dir, topdown=True, followlinks=False):
        dirs[:] = sorted(
            d for d in dirs if not os.path.islink(os.path.join(current, d))
        )
        rel_dir = os.path.relpath(current, parent)
        yield "dir", current, rel_dir.replace(os.sep, "/").rstrip("/") + "/"
        for filename in sorted(files):
            fpath = os.path.join(current, filename)
            if not os.path.islink(fpath) and os.path.isfile(fpath):
                yield "file", fpath, os.path.join(rel_dir, filename).replace(
                    os.sep, "/"
                )


def validate_existing_zip(candidate):
    path = candidate.zip_path
    if not os.path.exists(path):
        return None
    try:
        archived, bad = zip_non_dir_count(path, verify_crc=True)
        valid = archived == candidate.stat.files and bad is None
        return {
            "status": "already_done" if valid else "zip_exists_invalid",
            "path": candidate.stat.path,
            "zip_path": path,
            "archived_files": archived,
            "expected_files": candidate.stat.files,
            "zip_bytes": os.path.getsize(path),
            "valid": valid,
        }
    except Exception as error:
        return _fail(candidate, str(error))


def remove_partial_zip(zip_path):
    part = f"{zip_path}.part"
    if os.path.exists(part):
        try:
            os.remove(part)
        except OSError:
            pass


def zip_folder(candidate, overwrite, verbosity=0):
    path = candidate.zip_path
    if is_descendant(path, candidate.stat.path):
        return _fail(candidate, "zip path is inside the source folder")
    if os.path.exists(path) and not overwrite:
        existing = validate_existing_zip(candidate)
        msg = (
            "zip exists but does not validate"
            if (existing and not existing["valid"])
            else "zip exists"
        )
        return _fail(candidate, msg)

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    part = f"{path}.part"
    remove_partial_zip(path)
    start = time.time()
    files = 0
    try:
        with zipfile.ZipFile(
            part,
            mode="x",
            compression=zipfile.ZIP_DEFLATED,
            allowZip64=True,
            compresslevel=6,
            strict_timestamps=False,
        ) as archive:
            for kind, src, name in archive_items(candidate.stat.path):
                archive.write(src, name)
                if kind == "file":
                    files += 1
                    if verbosity and files % 5000 == 0:
                        print(
                            f"    {files:,} / ~{candidate.stat.files:,} files archived..."
                        )
        with zipfile.ZipFile(part, "r") as archive:
            archived = sum(1 for info in archive.infolist() if not info.is_dir())
            bad = archive.testzip()
        valid = files == archived == candidate.stat.files and bad is None
        zip_bytes = os.path.getsize(part)
        if valid:
            if not overwrite and os.path.exists(path):
                remove_partial_zip(path)
                return _fail(candidate, "zip appeared while this job was running")
            os.replace(part, path)
        else:
            remove_partial_zip(path)
        return {
            "status": "created" if valid else "validation_failed",
            "path": candidate.stat.path,
            "zip_path": path,
            "files": files,
            "archived_files": archived,
            "expected_files": candidate.stat.files,
            "zip_bytes": os.path.getsize(path) if valid else zip_bytes,
            "valid": valid,
            "seconds": round(time.time() - start, 3),
        }
    except KeyboardInterrupt:
        remove_partial_zip(path)
        raise
    except Exception as error:
        remove_partial_zip(path)
        return _fail(candidate, str(error))


def finish_zip_result(result, delete_original):
    if not delete_original:
        return result
    if result.get("valid") and result["status"] == "created":
        try:
            shutil.rmtree(result["path"])
            result["deleted_original"] = True
        except Exception as error:
            result["deleted_original"] = False
            result["delete_error"] = str(error)
    return result


def zip_with_resume(args):
    candidate, overwrite, resume, delete_original, verbosity = args
    existing = validate_existing_zip(candidate)
    replaced_invalid = False
    if existing and existing["valid"] and resume and not overwrite:
        if delete_original:
            existing["delete_error"] = (
                "delete skipped because this zip was not created in this run; "
                "rerun with --overwrite to recreate before deleting"
            )
        return finish_zip_result(existing, delete_original)
    if existing and not existing["valid"] and resume and not overwrite:
        try:
            os.remove(candidate.zip_path)
            replaced_invalid = True
        except OSError as error:
            return _fail(candidate, f"could not remove invalid zip: {error}")
    elif existing and not existing["valid"] and not overwrite:
        return _fail(candidate, "zip exists but does not validate")
    result = zip_folder(candidate, overwrite, verbosity)
    if replaced_invalid:
        result["replaced_invalid_zip"] = True
    return finish_zip_result(result, delete_original)


def failed_count(counts):
    return counts["failed"] + counts["validation_failed"] + counts["interrupted"]


def run_zip_jobs(candidates, cfg):
    if not candidates:
        return []

    workers = min(cfg["workers"], len(candidates))
    print(f"\nCreating {len(candidates):,} zip(s) with {workers} worker(s)...")
    file_verbosity = cfg["verbosity"] if workers == 1 else 0
    tasks = [
        (candidate, cfg["overwrite"], cfg["resume"], delete_original, file_verbosity)
        for candidate, delete_original in candidates
    ]
    results = []

    def show_progress():
        counts = Counter(r["status"] for r in results)
        done, total, w = len(results), len(tasks), 20
        bar = "#" * int(w * done / total) + "-" * (w - int(w * done / total))
        sys.stdout.write(
            f"\r[{bar}] {done}/{total} zip jobs | "
            f"created {counts['created']} | resumed {counts['already_done']} | "
            f"failed {failed_count(counts)}"
        )
        sys.stdout.flush()

    try:
        if workers > 1:
            with multiprocessing.Pool(workers) as pool:
                for result in pool.imap_unordered(zip_with_resume, tasks):
                    results.append(result)
                    show_progress()
        else:
            for task in tasks:
                results.append(zip_with_resume(task))
                show_progress()
        sys.stdout.write("\n")
    except KeyboardInterrupt:
        for candidate, _ in candidates:
            remove_partial_zip(candidate.zip_path)
        sys.stdout.write(
            "\nZip creation interrupted; partial zip files were cleaned.\n"
        )
        done_paths = {r["path"] for r in results}
        results.extend(
            {
                "status": "interrupted",
                "path": c.stat.path,
                "zip_path": c.zip_path,
                "valid": False,
            }
            for c, _ in candidates
            if c.stat.path not in done_paths
        )
        return results

    for r in results:
        if r["status"] == "created":
            prefix = "Recreated" if r.get("replaced_invalid_zip") else "Created"
            print(
                f"  {prefix} {human_readable_size(r['zip_bytes'], extended_units=True)}; "
                f"validation passed: {r['zip_path']}"
            )
        elif r["status"] == "already_done":
            print(f"  Resume: already valid  {r['zip_path']}")
        else:
            print(f"  {r['status']}: {r.get('error', 'file-count mismatch')}")
        if r.get("deleted_original"):
            print(f"    Deleted original: {r['path']}")
        elif r.get("delete_error"):
            print(f"    Delete failed: {r['delete_error']}")

    counts = Counter(r["status"] for r in results)
    print(
        f"\nZip creation complete."
        f"\n  Created : {counts['created']:,}"
        f"\n  Resumed : {counts['already_done']:,}"
        f"\n  Failed  : {failed_count(counts):,}"
        f"\n  Deleted : {sum(1 for r in results if r.get('deleted_original')):,}"
    )
    return results
