<h1>
  <img src="assets/os-toolkit-logo-blink.gif" alt="" width="39" align="absmiddle" />
  <samp>OS Toolkit</samp>
</h1>

`os-toolkit` is a Python-first OS utility repo for file system operations that need more **control**, **safety**, and **operational clarity** than ad-hoc shell commands.
It is a practical layer between raw `os`/`shutil` and a future agent-native ops toolkit.

## Current phase

The repo is in **migration-first** mode:
- **Analysis pillar**: inspect, profile, and compare directory trees.
- **Transfer pillar**: copy and package data safely with resume/validation behavior.

Destructive behavior is never default; dry-run and explicit confirmation patterns are preferred.

## Setup

1. Install [Miniconda](https://docs.conda.io/en/latest/miniconda.html) (or Anaconda).
2. From the repo root:

```bash
conda env create -f environment.yml
conda activate ostk
just install dev
```

3. Install [just](https://github.com/casey/just) (see [Installing just](#installing-just) below) if it is not already on your PATH.

All `just` recipes assume the **`ostk`** conda environment is active (`CONDA_DEFAULT_ENV=ostk`). Use `just install` with optional profiles:

| Profile | Installs |
|---------|----------|
| *(none)* | Nothing — runtime is stdlib-only |
| `dev` | pytest, black |
| `bench` | requests (corpus fetch) |
| `ml` | numpy, pandas, scikit-learn, tqdm |
| `all` | dev + bench + ml |

Continuous integration via GitHub Actions can be added when the repo is pushed publicly. The `just pre-commit` recipe and installable hook source already enforce the same checks locally.

## Repository layout

```text
os-toolkit/
  file_transfer_pro.py        # parallel copy (permanent CLI)
  disk_analyzer_pro.py        # usage tree (permanent CLI)
  analyze_pro.py              # usage | profile | compare subcommands
  smart_zip_pro.py            # zip recommendation + optional archives
  *_config.py                 # optional defaults (CLI overrides)
  runs/                       # generated analysis artifacts only
  os_toolkit/                 # shared implementation (not run directly)
    core/
    analysis/
    transfer/
```

## What is usable today

### 1) `file_transfer_pro.py`
Parallel file copy with resume, dry-run, optional verify, adaptive workers, and progress reporting.

```bash
python file_transfer_pro.py --source "<src>" --dest "<dst>"
```

### 2) `disk_analyzer_pro.py` and `analyze_pro.py`
Directory usage scanner (standalone) and unified analysis CLI.

```bash
python disk_analyzer_pro.py --path "<root>"
python analyze_pro.py usage --path "<root>"
python analyze_pro.py profile --root "<root>" --run-id myrun
python analyze_pro.py compare --old runs/myrun/old_features.csv --new runs/myrun/new_features.csv
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

## Installing just

[just](https://github.com/casey/just) is the optional task runner for tests, benchmarks, and root CLIs. Install it once, then run recipes from the repo root (e.g. `just test`, `just check`).

| Platform | Install |
|----------|---------|
| Linux (Debian/Ubuntu) | [packages](https://github.com/casey/just#packages) — e.g. `cargo install just` or distro package where available |
| macOS | [Homebrew](https://brew.sh/): `brew install just` |
| Windows | [Scoop](https://scoop.sh/): `scoop install just` — or [Chocolatey](https://chocolatey.org/): `choco install just` |

Forward CLI flags after `--`, e.g. `just transfer -- --source "<src>" --dest "<dst>"`.

## Architecture

Root `*_pro.py` scripts are the permanent user interface. `os_toolkit/` holds shared implementation only (never `python -m os_toolkit`). Analysis artifacts go under `runs/`.

Remaining roadmap: deepen analysis (duplicates, inter-usage), expand `transfer/`, add new domains (`dedupe`, `security`, `network`) with matching root tools.
