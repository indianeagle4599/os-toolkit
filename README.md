<h1>
  <img src="assets/os-toolkit-logo-blink.gif" alt="" width="39" align="absmiddle" />
  <samp>OS Toolkit</samp>
</h1>

`os-toolkit` is a Python-first OS utility repo for file system operations that need more **control**, **safety**, and **operational clarity** than ad-hoc shell commands.
It is a practical layer between raw `os`/`shutil` and a future agent-native ops toolkit.

## Setup

**Requirements:** Python 3.10+ on your PATH. Clone the repo and run scripts from the repo root — no `pip install` required for copy, usage, or smart zip.

```bash
git clone https://github.com/indianeagle4599/os-toolkit.git
cd os-toolkit
python file_transfer_pro.py --help
python disk_analyzer_pro.py --help
python smart_zip_pro.py --help
python analyze_pro.py --help
```

| Tool | Role | Stdlib-only? |
|------|------|--------------|
| `file_transfer_pro.py` | Parallel copy (resume, dry-run, strategies) | Yes |
| `disk_analyzer_pro.py` | Directory usage tree (legacy entry) | Yes |
| `smart_zip_pro.py` | Zip recommendations / optional archives | Yes |
| `analyze_pro.py` | `usage`, `compare` subcommands | `usage` yes; `compare` needs ML stack |

**Optional — `analyze_pro compare`:** `pip install numpy pandas scikit-learn tqdm` (see commented lines in `requirements.txt`).

**Optional — developer shortcuts:** with [just](https://github.com/casey/just) installed, `just list` shows recipes such as `just test`, `just transfer --help`, `just analyze usage --help`.

**Tests (optional):** `pip install pytest` then `python -m pytest -m "not slow and not requires_ml" -q` (25 passed, 1 deselected at last check). Or `just test`.

**Behavior guarantees and limits:** see [`specs/README.md`](specs/README.md) (maps each tool to its spec file).

## Quick start

Run from the repo root. Replace paths with your own directories.

```bash
# Transfer — dry-run first (no writes)
python file_transfer_pro.py --source ./src --dest ./dst --dry-run

# Usage tree — prefer unified CLI; disk_analyzer_pro is the legacy shim with config-file defaults
python analyze_pro.py usage -p .

# Compare two directory trees (profiles cached under runs/, then matching)
pip install numpy pandas scikit-learn tqdm   # once, for compare only
python analyze_pro.py compare --old ./dir-a --new ./dir-b
# Artifacts: runs/compare_<hash>/ (profiles, matches.json, manifest.json)

# Smart zip — recommendations only by default (no zips created)
python smart_zip_pro.py --root .
# Without --output, planned zips go in <parent-of-root>/<rootname>_zips/ (outside the scan root)
python smart_zip_pro.py --root . --interactive   # prompt per candidate
```

**Windows note:** `disk_analyzer_pro.py` with no flags defaults to `D:/`. Prefer `python analyze_pro.py usage -p .` or pass `-p` explicitly.

## Current phase

The repo is in **migration-first** mode:
- **Analysis pillar**: inspect, profile, and compare directory trees.
- **Transfer pillar**: copy and package data safely with resume/validation behavior.

Destructive behavior is never default; dry-run and explicit confirmation patterns are preferred.

## Repository layout

```text
os-toolkit/
  file_transfer_pro.py        # parallel copy (permanent CLI)
  disk_analyzer_pro.py        # usage tree (legacy CLI; same engine as analyze usage)
  analyze_pro.py              # usage | compare subcommands
  smart_zip_pro.py            # zip recommendation + optional archives
  *_config.py                 # optional defaults (CLI overrides)
  runs/                       # generated analysis artifacts only
  os_toolkit/                 # shared implementation (not run directly)
    core/
    analysis/
    transfer/
  specs/                      # per-tool behavior contracts
```

## What is usable today

### 1) `file_transfer_pro.py`

Parallel file copy with resume (skip when destination size matches source), dry-run, adaptive workers, and progress reporting. Rejects destination paths inside the source tree.

```bash
python file_transfer_pro.py --source "<src>" --dest "<dst>"
```

### 2) Usage analysis

Same `run_usage` engine in both entry points. **Prefer `analyze_pro usage`** for one unified CLI. Use **`disk_analyzer_pro.py`** only if you rely on `disk_analyzer_config.py` defaults.

```bash
python analyze_pro.py usage -p "<root>"
python disk_analyzer_pro.py -p "<root>"
python analyze_pro.py compare --old "<dir-a>" --new "<dir-b>"
```

### 3) `smart_zip_pro.py`

Recommends high-value folder-level zip targets and can create validated archives.

```bash
python smart_zip_pro.py --root "<root>"
python smart_zip_pro.py --root "<root>" --interactive
python smart_zip_pro.py --root "<root>" --execute
```

Common flags: `--sensitivity low|normal|high`, `--exclude "name1,name2"`, `--output "<dir>"` (must be outside `--root`), `--resume`, `--overwrite`, `--delete-originals`, `--workers`.

## Configuration model

Each root script can load optional defaults from a colocated config file:
- `file_transfer_config.py`
- `disk_analyzer_config.py`
- `smart_zip_config.py`

Rule: **CLI arguments always win** over config defaults.

## Safety and design principles

- Python-only tooling.
- Stdlib-first dependency policy (ML stack only for compare).
- No destructive defaults.
- Clear operator feedback (progress, counts, explicit warnings).
- Idempotent/re-runnable behavior where possible (resume/skip-valid flows).

## Architecture

Root `*_pro.py` scripts are the permanent user interface. `os_toolkit/` holds shared implementation only (never `python -m os_toolkit`). Analysis artifacts go under `runs/`.

Remaining roadmap: benchmarks, deeper analysis modes, expand `transfer/`, additional domains with matching root tools.
