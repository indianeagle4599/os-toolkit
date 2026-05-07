# os-functions (`python os+`)

`os-functions` is a Python-first OS utility repo for file system operations that need more **control**, **safety**, and **operational clarity** than ad-hoc shell commands.  
Think **python os+**: a practical layer between raw `os`/`shutil` and a future agent-native ops toolkit.

## Current phase

The repo is in **migration-first** mode:
- **Analysis pillar**: inspect, profile, and compare directory trees.
- **Transfer pillar**: copy and package data safely with resume/validation behavior.

Destructive behavior is never default; dry-run and explicit confirmation patterns are preferred.

## Repository layout

```text
os-functions/
  file_transfer_pro.py        # parallel copy utility (resume/verify/adaptive workers)
  disk_analyzer_pro.py        # usage/tree analysis utility
  smart_zip_pro.py            # zip recommendation + optional archive creation
  *_config.py                 # optional default values (CLI overrides)
  migration_pro/              # analysis pipeline package-in-folder (profile/features/match)
    scan/
    compare/
    io/
    migration_runs/
  docs/
    CONTEXT.md                # project facts and current scope
    ARCHITECTURE.md           # short structure map
    REFACTOR.md               # migration-first refactor plan and phase order
  TODO.md
```

## What is usable today

### 1) `file_transfer_pro.py`
Parallel file copy with resumable behavior and progress reporting.

```bash
python file_transfer_pro.py --source "<src>" --dest "<dst>"
```

### 2) `disk_analyzer_pro.py`
Directory usage scanner for storage and layout visibility.

```bash
python disk_analyzer_pro.py --path "<root>"
```

### 3) `smart_zip_pro.py`
Recommends high-value folder-level zip targets and can create validated archives.

```bash
# dry-run recommendations (default)
python smart_zip_pro.py --root "<root>"

# approve per candidate
python smart_zip_pro.py --root "<root>" --interactive

# single-confirm batch execute
python smart_zip_pro.py --root "<root>" --execute
```

Common smart-zip flags:
- `--sensitivity low|normal|high`
- `--exclude "name1,name2"`
- `--output "<zip_output_dir>"` (must be outside `--root`)
- `--resume`, `--overwrite`, `--delete-originals`, `--workers`

## Configuration model

Each root script can load optional defaults from a colocated config file:
- `file_transfer_config.py`
- `disk_analyzer_config.py`
- `smart_zip_config.py`

Rule: **CLI arguments always win** over config defaults.

## Safety and design principles

- Python-only tooling.
- Stdlib-first dependency policy.
- No destructive defaults.
- Clear operator feedback (progress, counts, explicit warnings).
- Idempotent/re-runnable behavior where possible (resume/skip-valid flows).

## Refactor direction (planned, not fully landed)

The repo is moving toward a shared package layout:

```text
os_functions/
  core/        # shared paths/format/config/terminal/ui/error helpers
  analysis/    # usage/profile/features/match/runs
  transfer/    # copy/worker/verify/strategies/cli
```

Planned order:
1. Package skeleton + shared core.
2. Root shim dedupe (no behavior change).
3. Analysis unification under a single analysis entrypoint.
4. Transfer extraction from root script.
5. Deeper analysis features.
6. Migration executor (last).

For exact decisions and sequencing, see `docs/REFACTOR.md`.

## Companion docs

- `docs/CONTEXT.md` — product intent, active phase, constraints.
- `docs/ARCHITECTURE.md` — concise structure map.
- `docs/REFACTOR.md` — detailed phases, decisions, deferred scope.
- `AGENTS.md` — collaboration and change doctrine.
