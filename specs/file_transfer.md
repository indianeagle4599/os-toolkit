# File Transfer Pro

## What it does

Recursively copies all files from a source directory to a destination directory. `parallel_copy` validates paths, probes destination media type with `rotational_for_path`, then routes to one of two copy paths:

- **HDD or unknown destination** (`hdd_copy`): single-threaded `os.walk` plus `shutil.copy2`. Before walking, it builds a destination size index (one recursive scan when resume is enabled) so matching files are skipped without rereading content.
- **SSD destination** (`ssd_copy`): collects copy pairs with the same resume logic, then runs `shutil.copy2` in a `ThreadPoolExecutor` (default worker count `cpu_count // 2`, at least 1).

On Windows, when the destination is rotational and `OS_TOOLKIT_ROBOCOPY=1`, an optional robocopy backend may run for large trees (see Guarantees) before falling back to `hdd_copy`.

At verbosity 1, both paths print periodic progress (`files_done/total_files`) and a final line with duration and copied/skipped/failed counts. Failed files are reported; the job continues and returns `False` if any copy failed.

There is no prescan size-bucket summary, no file-ordering strategy, no adaptive worker tuning, and no multiprocessing pool on the production path.

## Inputs

Required: source directory path, destination directory path.

Optional: worker count (SSD path only; default `cpu_count // 2`); verbosity level 0 (quiet), 1 (normal), or 2 (verbose); dry-run flag.

Optional defaults file `file_transfer_config.py` may set SOURCE, DEST, WORKERS, VERBOSITY, DRY_RUN, and HDD_FILE_COUNT_THRESHOLD (robocopy large-tree threshold). Command-line arguments override config values.

## Outputs

Optional startup banner from the CLI. Progress lines at verbosity 1 while work runs. Final summary: duration and counts for copied, skipped, and failed (HDD/SSD paths), or robocopy summary when that backend completes. Dry-run on the SSD path prints would-copy and skip counts without writing files; dry-run on the HDD path walks the tree and counts work without `copy2`.

The copy function returns `False` when validation fails, robocopy fails with exit code ≥ 8, or any file copy failed; `True` when every file was copied or skipped as already up to date.

## Guarantees

Dry-run performs no file writes on the SSD path; the HDD dry-run path does not call `copy2`. Re-running against an existing destination skips files where the destination already exists with the same byte size as the source (no content hash). Parent directories are created before each copy. On Windows, source paths use extended-length path handling where applicable. The tool does not delete or truncate source files.

**Media routing**

Destination is treated as slow (HDD or unknown rotational) when `rotational_for_path` is not `False`; otherwise the SSD threaded path is used. Slow destinations do not use `ThreadPoolExecutor`; worker count applies only on the SSD path.

**Source stat calls**

Per-file `os.stat` on the source runs only when resume indexing is active (`dest_sizes` non-empty) or `verbosity >= 1` (byte progress). Fresh destinations at `verbosity=0` skip source stats; resume still compares sizes when the destination index was built. At `verbosity=0`, no progress lines and no final `done` summary are printed.

**Robocopy backend (Windows, opt-in)**

Set `OS_TOOLKIT_ROBOCOPY=1` to attempt robocopy for HDD destinations when the source file count exceeds `HDD_FILE_COUNT_THRESHOLD` (default 50 000) and the run is not a dry-run. Requires robocopy on PATH. Exit codes 0–1 = success; 2–3 = partial (warned); ≥ 8 = error. Falls back to `hdd_copy` if robocopy is not found or not selected. Not enabled by default; no behaviour change without the env var.

## Known limits

Resume uses size equality only, not content hash or modification time. A failed file is reported but does not abort the whole job. There is no sync, merge, or delete mode. Output does not go under `runs/`. `worker.py` and `strategies.py` are not used by the production copy path (test infrastructure only).

## Adversarial surfaces

Missing source or destination; destination inside source; empty source tree; permission denied during copy; disk full; very many small files; very large files; user interrupt; partial destination from a prior run; cross-device copies; Windows paths longer than legacy limits.
