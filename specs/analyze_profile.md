# Analyze Pro — profile (internal)

## What it does

Library implementation used by `analyze compare` — not a separate CLI subcommand. Walks a filesystem root bottom-up and builds a nested profile (sizes, file counts, folder counts per relative path). Writes profile JSON and a flattened features CSV under a run directory beneath `runs/`.

## Inputs

Called from `os_toolkit.analysis.runs.ensure_profile` with a root path, run directory, optional filename prefix (`old_` / `new_`), and verbosity.

## Outputs

Console scan messages when verbosity allows. Files under `runs/<run_id>/`: prefixed or unprefixed `profile.json` and `features.csv`. Manifest records root path and mtime for cache reuse.

## Guarantees

Does not delete or modify source files. Walk errors are reported at verbose levels; skipped paths do not abort the whole profile.

## Known limits

`runs/` is local and gitignored. No duplicate-file detection inside profile. Large trees produce large JSON.

## Adversarial surfaces

Invalid root; empty tree; permission skips; very large JSON.
