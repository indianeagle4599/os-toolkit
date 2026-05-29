# Analyze Pro — compare

## What it does

Compares two directory trees. Profiles each root internally (nested JSON + features CSV under `runs/`), reusing cached profiles when the root path and directory mtime are unchanged, then runs structure and name similarity matching and writes match artifacts.

## Inputs

Required: `--old` and `--new` directory roots.

Optional: `--run-id` (default: stable id derived from both roots), similarity threshold, top-k, batch size, structure filter, name-similarity backend and related tokenizer or n-gram settings, depth limit, worker count, color output, verbosity 0–2.

## Outputs

Console scan messages when profiling runs; cache-hit line when a profile is reused. Timer lines and summary lines from compare. `old_*` / `new_*` profile artifacts, `matches.json`, `matches.txt`, and `manifest.json` under the run directory. Optional compressed similarity cache files.

## Guarantees

Does not delete or modify source files. Given the same roots and unchanged directory mtimes, re-running compare reuses profile CSVs without rescanning. Compare matching output is reproducible for identical feature CSV inputs and unchanged similarity cache files.

## Known limits

Requires numpy, pandas, and tqdm for compare. Optional rapidfuzz or sentence-transformers for some name backends. Memory grows with product of row counts for similarity. Top-level filter may collapse sibling paths in the text summary. Staleness uses each root directory mtime only (not per-file changes with unchanged root mtime).

## Adversarial surfaces

Missing Python dependencies; invalid or missing root directories; empty tree; permission skips during profile; very large trees; stale similarity cache after profile regeneration; Windows path strings embedded in CSV cells.
