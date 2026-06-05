# Benchmarks

Informational performance harness for os-toolkit tools and stdlib baselines.

## Setup

Uncomment dependencies in `requirements.txt` (pytest for tests; `requests` for corpus fetch).

## Corpus

1. `python -m benchmarks.fetch_corpus` — downloads into `benchmarks/corpus/_cache/` (gitignored).
2. `python -m benchmarks.corpus --profile small/mixed` — samples a profile directory.

Note: 5G and 10G profiles currently produce identical output (~2.62GB, 111k files) due to cache size limit. Fetch additional datasets to make these sizes meaningful.

Partial downloads are allowed; runners print warnings for unavailable datasets. For publishable numbers, verify the full pool first.

## Runners

Each runner writes line-delimited JSON under `benchmarks/results/`. Records include `corpus_signature` (or `unverified` when `--ignore-manifest` is used).

Default profile: `small/mixed`.

**Multi-run methodology:** Use `just bench-multi transfer ...` to run a suite up to N times (default 10), stopping early when each (tool, scenario) pair has ≥3 non-outlier valid runs. Outliers are detected via modified Z-score (MAD, threshold 3.5). Medians over valid runs are written to `*_aggregate.json` in `benchmarks/results/`. Single `just bench` runs measure once — use for quick checks only, not for publishable numbers.

## Hardware

Record `device_src` / `device_dst` from `benchmarks/devices.py` labels (`mount`, `rotational`, `physical_id`). Not comparable across machines unless `corpus_signature` matches.

## Multi-drive benchmarks

Pass 1–4 drive roots (folders on distinct volumes or partitions). Omit all `--drive-*` flags to use the built-in synthetic corpus under `benchmarks/corpus/` (used by `just check`).

```bash
python -m benchmarks.run_transfer \
  --drive-a D:\ssd1 --drive-b D:\ssd2 \
  --profile small/mixed --scenarios all

python -m benchmarks.run_analysis \
  --drive-a D:\ssd1 --drive-b E:\hdd \
  --scenarios all
```

| Flag | Transfer | Analysis |
|------|----------|----------|
| `--drive-a` … `--drive-d` | Source/dest mount roots | Corpus host per drive |
| `--scenarios all` | N² copy pairs | N within-drive scans |
| `--scenarios within` | Diagonal only (a→a, …) | Same as `all` (already N) |
| `--scenarios cross` | Off-diagonal only | **Error** |
| `--scenarios "a->c,b->d"` | Custom subset | **Error** |

Each JSONL line includes `scenario_id`, `physical_id_src`, `physical_id_dst`, and `same_physical_device` (bool or `null` if unknown). Use these fields when interpreting results: **partitioned HDD** layouts often show `same_physical_device: true` for paths on different letters that share one disk—do not treat that as independent multi-disk throughput.

Scratch trees are `bench_<UTC>_<scenario_id>/` on the relevant drives; runners remove them in `finally` and register an `atexit` cleanup on interrupt.

**Transfer isolation:** Each tool runs in a fresh subprocess via `benchmarks/run_tool.py` (no shared Python heap or OS cache between tools). Timed window is full copy (blank slate to done). Matrix runs stage `--corpus` into `bench_<UTC>_<scenario_id>/corpus` on the source drive before copy; each tool writes under `dest/<tool_name>/`. Default `--media-filter ssd` skips non-SSD scenarios. Use `--shuffle-tools` and optional `--tool-seed` for tool order.

## Worker policy and scenario order

os-toolkit now applies disk-aware worker caps automatically:
- SSD→SSD: up to cpu_count // 2 workers
- Any HDD involved: max 2 workers
- HDD dest + >50 000 files: 1 worker (avoids seek thrashing)
- Unknown media: treated conservatively (max 2)

`workers_requested` and `workers_effective` are recorded in every
os-toolkit JSONL result row.

Scenarios run lighter-first: SSD-within → SSD-cross → SSD→HDD
→ HDD→SSD → HDD-cross → HDD-within. Use `just bench-quick` for
a fast SSD-only smoke run before committing to a full matrix.
