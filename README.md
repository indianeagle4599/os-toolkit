<h1>
  <img src="assets/os-toolkit-logo-blink.gif" alt="" width="39" align="absmiddle" />
  <samp>OS Toolkit</samp>
</h1>

`os-toolkit` is a Python-first OS utility repo for file system operations that need more **control**, **safety**, and **operational clarity** than ad-hoc shell commands.
It is a practical layer between raw `os`/`shutil` and a future agent-native ops toolkit.

## Disk usage performance

**Runtime:** **0.30 s** median to scan **~2.0 GB** (~108K files) on SSD and emit a usage tree — **11× faster** than `os.walk` sizing (3.31 s), **+8%** vs bare `scandir` total-only (0.28 s).

| Tool | Runtime | Output |
|------|---------|--------|
| **os_toolkit.usage** (ours) | **0.30 s** | size + % tree |
| stdlib.os.walk + sum | 3.31 s | byte total only |
| stdlib.scandir + sum | 0.28 s | byte total only |

Example (`analyze_pro usage`, same corpus, depth 2):

```
`- mixed ................................................   2.0 GB (100.0%)
    |- linux_kernel_src_extracted .......................   1.3 GB ( 63.0%)
    |- coco2017_val_subset_extracted .................... 676.5 MB ( 33.0%)

Analysis completed in 0.26 seconds
```

Detail: [benchmarks/RESULTS.md](benchmarks/RESULTS.md#disk-usage-analysis)

## Transfer performance (1G copy benchmarks)

Hardware copy benchmarks on ~1 GB corpora (Windows, SSD/HDD matrix). **Our tool:** `os_toolkit.transfer` via `file_transfer_pro.py`. Compared to `stdlib.copytree` and `robocopy`. Medians from multi-run orchestrator (≥3 valid runs, MAD outliers removed).

| Profile | Storage | **os_toolkit** (ours) | vs copytree | vs robocopy |
|---------|---------|----------------------|-------------|-------------|
| `1G/balanced` | SSD | **~14 s**, **~70 MB/s** | ~1.4× | ~1.6× |
| `1G/balanced` | HDD† | **~13–60 s**, **~17–78 MB/s** | ~1.0–1.4× | ~1.2–1.5× |
| `1G/tiny-heavy` | SSD | **~15 s**, **~65 MB/s** | ~1.4× | ~1.6× |
| `1G/tiny-heavy` | HDD† | **~13–66 s**, **~15–77 MB/s** | ~1.0–1.4× | ~1.2–1.5× |
| `1G/media-heavy` | SSD | **~1.8 s**, **~553 MB/s** | ~1.4× | ~1.5× |
| `1G/media-heavy` | HDD† | **~3–11 s**, **~93–405 MB/s** | ~1.0–1.4× | ~1.0–1.3× |

†HDD row: five scenarios touching `E:` (HDD); not comparable to SSD-only row. Detail: [benchmarks/RESULTS.md § Transfer](benchmarks/RESULTS.md#transfer-copy).

SSD `1G/balanced`: four scenarios (`a_to_a`, `a_to_b`, `b_to_a`, `b_to_b` on C:/D: SSDs). Median-of-scenario-medians; same `corpus_signature` required to compare elsewhere.

**Full scenario tables:** [benchmarks/RESULTS.md](benchmarks/RESULTS.md) · **How to run (warnings, corpus prep, time):** [benchmarks/README.md](benchmarks/README.md#reproduce-on-your-hardware)

> **Before you benchmark:** Requires multi-GB dataset fetch, ~1 GB+ free space per drive used, and **real full-tree copies** on paths you choose. A full 1G matrix suite can run for **hours**. Use empty bench folders only.

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
| `file_transfer_pro.py` | Disk-aware parallel copy (SSD/HDD routing, resume, dry-run) | Yes |
| `disk_analyzer_pro.py` | Directory usage tree (legacy entry) | Yes |
| `smart_zip_pro.py` | Zip recommendations / optional archives | Yes |
| `analyze_pro.py` | `usage`, `compare` subcommands | `usage` yes; `compare` needs ML stack |

**Optional — `analyze_pro compare`:** `pip install numpy pandas scikit-learn tqdm` (see commented lines in `requirements.txt`).

**Optional — developer shortcuts:** with [just](https://github.com/casey/just) installed, `just list` shows recipes such as `just test`, `just transfer --help`, `just analyze usage --help`.

**Tests (optional):** `pip install pytest` then `python -m pytest -m "not slow and not requires_ml" -q` (67 passed, 2 deselected at last check). Or `just test`.

**Benchmarks (optional):** `just install bench` for corpus fetch (`requests`); `just check` runs fast tests plus synthetic bench smoke. Hardware transfer medians: `just bench-multi transfer ...` — see [benchmarks/README.md](benchmarks/README.md) (prep, warnings, runtime) and published numbers in [benchmarks/RESULTS.md](benchmarks/RESULTS.md).

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

The repo is in **migration-first** mode (package + shims largely complete):
- **Analysis pillar**: inspect, profile (internal), and compare directory trees.
- **Transfer pillar**: disk-aware copy and zip packaging with resume/validation behavior.
- **Benchmarks**: harness shipped; owner 1G transfer baselines in [`benchmarks/RESULTS.md`](benchmarks/RESULTS.md).

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
  benchmarks/                 # performance harness (results gitignored)
```

## What is usable today

### 1) `file_transfer_pro.py`

Disk-aware parallel copy: SSD paths use threaded `ssd_copy`; HDD paths use sequential `hdd_copy`. Resume (skip when destination size matches source), dry-run, byte progress bar, and verbosity levels. Rejects destination paths inside the source tree.

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

Remaining roadmap: post-copy tree verification, MVP-B analysis depth (`dedupe_pro`, per-file inventory), additional domains per [`specs/PHASES.md`](specs/PHASES.md). Transfer hardware baselines: [`benchmarks/RESULTS.md`](benchmarks/RESULTS.md).
