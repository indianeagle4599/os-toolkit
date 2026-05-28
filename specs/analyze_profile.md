# Analyze Pro — profile

## What it does

Walks a filesystem root bottom-up and builds a nested profile (sizes, file counts, folder counts per relative path). Writes profile JSON and a flattened features CSV under a run directory beneath `runs/`. Can profile one root or two roots (old and new) in one run for later compare. Writes or updates `manifest.json` describing inputs and output paths.

## Inputs

Single-root mode: `--root` and optional `--run-id` (auto-generated UTC timestamp id if omitted).

Dual-root mode: `--old-root` and `--new-root` with optional `--run-id`.

Optional verbosity 0, 1, or 2.

## Outputs

Console scan messages. Files under `runs/<run_id>/`: `profile.json` and `features.csv`, or `old_*` / `new_*` prefixed pairs plus `manifest.json`. Printed run directory path.

## Guarantees

Does not delete or modify source files. Re-running with the same run id overwrites artifacts in that run directory. Walk errors are reported at verbose levels; skipped paths do not abort the whole profile.

## Known limits

`runs/` is local and gitignored. No duplicate-file detection inside profile. Profile alone does not run compare; that is a separate subcommand. Large trees produce large JSON.

## Adversarial surfaces

Invalid root; empty tree; permission skips; very large JSON; manual run id collision; dual-root mode with only one root provided.
