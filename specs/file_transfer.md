# File Transfer Pro

## What it does

Recursively copies all files from a source directory to a destination directory. Before copying, it scans the source and prints size-bucket summaries. It schedules work using a selectable strategy (smallest-first, largest-first, or balanced), runs copies in a multiprocessing pool with optional adaptive worker tuning, shows live progress, and supports resume by skipping destination files that already match source size.

## Inputs

Required: source directory path, destination directory path.

Optional: worker count; verbosity level 0 (quiet), 1 (normal), or 2 (verbose); dry-run flag; strategy name; adaptive worker tuning flag.

Optional defaults file `file_transfer_config.py` may set SOURCE, DEST, WORKERS, VERBOSITY, DRY_RUN, STRATEGY, and ADAPTIVE. Command-line arguments override config values.

## Outputs

Startup banner and scan summary at normal verbosity. Live progress line while work runs. Final summary: duration, counts for copied, skipped, failed, or would-copy (dry-run), and average copy speed when applicable. Process exits after validation errors from missing required paths; per-file failures are counted but do not change the exit code today.

## Guarantees

Dry-run performs no file writes. Re-running against an existing destination skips files where the destination already exists with the same byte size as the source. Parent directories are created before each copy. On Windows, paths are passed through extended-length path handling for long paths. The tool does not delete or truncate source files.

## Known limits

Resume uses size equality only, not content hash or modification time. A failed file is reported but does not abort the whole job. Adaptive probing is disabled for dry-run, single-worker runs, or when the file count is too small for the probe sequence. There is no sync, merge, or delete mode. Output does not go under `runs/`.

## Adversarial surfaces

Missing source or destination; destination inside source; empty source tree; permission denied during copy; disk full; very many small files; very large files; user interrupt; partial destination from a prior run; cross-device copies; Windows paths longer than legacy limits.
