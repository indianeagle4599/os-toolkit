# Migration Pro

**Roadmap:** This workspace will fold into **`os_functions/analysis/`** with a unified **`analyze`** CLI; see **`docs/REFACTOR.md`** (phases, decisions) and **`docs/ARCHITECTURE.md`** (structural map). Until Phase 3, keep using the commands below.

Migration Pro is the file migration analysis workspace inside `os-functions`. It is being shaped as a future standalone repo for scanning folders, comparing old and new filesystem states, detecting duplicates/common files, and eventually producing safe migration and cleanup plans.

It is not a destructive migration executor yet. Current functionality is analysis-first: scan, extract features, compare profiles, and write auditable artifacts.

## Safety Contract

- No deletion by default.
- Migration execution is out of scope until scan, compare, and artifact outputs are reliable.
- Future migration/delete flows must support dry-run-first behavior.
- Outputs should be resumable and idempotent: rerunning a step should reuse or overwrite a clearly named artifact, not create hidden state.
- Generated run data lives under `migration_runs/<run_id>/`.

## Current Workflow

1. Scan a folder tree into a nested profile:
   ```bash
   python -m migration_pro.scan.profile <root> -o migration_pro/migration_runs/<run_id>/old_profile.json
   ```

2. Extract feature rows from a profile:
   ```bash
   python -m migration_pro.scan.features migration_pro/migration_runs/<run_id>/old_profile.json -o migration_pro/migration_runs/<run_id>/old_features.csv
   ```

3. Compare old and new feature CSVs:
   ```bash
   python -m migration_pro.compare.match --old migration_pro/migration_runs/<run_id>/old_features.csv --new migration_pro/migration_runs/<run_id>/new_features.csv
   ```

`matches.json` is the canonical machine artifact: it keeps top-k candidates even below the reporting threshold. `matches.txt` is only a short human-readable summary. `manifest.json` records the latest command, inputs, outputs, settings, and counts for the run. Similarity caches are stored under `migration_runs/<run_id>/cache/`.

## Layout

```text
migration_pro/
  scan/             # filesystem scan and feature extraction
  compare/          # profile matching, similarity, and filtering
  io/               # artifact and cache helpers
  migration_runs/   # generated analysis artifacts
```

The retained `migration_runs/initial/` artifacts were generated before this structure existed. They are kept for continuity and can be removed once the new workflow is stable.

## Dependencies

The baseline comparison path uses Python plus the existing data stack used by this folder: `numpy`, `pandas`, `sklearn`, and `tqdm`.

Optional similarity backends:

- `--name-sim tfidf` is the default.
- `--name-sim rapidfuzz` requires `rapidfuzz`.
- `--name-sim bert` requires `sentence-transformers` and may download a model if it is not already cached.

Embedding-backed comparison should stay behind the similarity module until there is enough real usage to justify a larger embedding subsystem.

## Git Notes

Do not run `git init` inside `migration_pro/` right now. Keep it as a normal folder in the master repo. If it later needs independent versioning, split it into a standalone repo deliberately or use a submodule only when the separate remote is worth the extra workflow cost.

`migration_pro/.gitignore` ignores local caches and bytecode while keeping the current run artifacts visible.
