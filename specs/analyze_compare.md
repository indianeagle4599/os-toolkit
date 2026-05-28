# Analyze Pro — compare

## What it does

Loads old and new feature CSVs from profile runs, normalizes structural features, computes similarity, applies optional name-similarity backends, filters to top-level groups for human-readable summaries, and writes match artifacts. Can resolve CSV paths from a prior run id. May cache similarity matrices under the run cache directory.

## Inputs

Required: paths to old and new feature CSVs, or a `--run-id` that resolves `old_features.csv` and `new_features.csv` under that run.

Optional: similarity threshold, top-k, batch size, structure filter, name-similarity backend and related tokenizer or n-gram settings, depth limit, worker count, color output, run id for manifest updates.

## Outputs

Timer lines and summary lines on the console. `matches.json`, `matches.txt`, and updated `manifest.json` under the run directory. Optional compressed similarity cache files.

## Guarantees

Read-only on original filesystem trees (inputs are CSV only). Given identical CSV inputs and unchanged cache files, matching output is reproducible.

## Known limits

Requires numpy, pandas, and tqdm. Optional rapidfuzz or sentence-transformers for some name backends. Memory grows with product of row counts for similarity. Top-level filter may collapse sibling paths in the text summary. Process exits with an error when dependencies or required columns are missing.

## Adversarial surfaces

Missing Python dependencies; empty CSV; schema mismatch between old and new; very large CSVs; stale cache after CSV regeneration; Windows path strings embedded in CSV cells.
