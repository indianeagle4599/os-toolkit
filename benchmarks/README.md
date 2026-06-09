# Benchmarks

Informational performance harness for os-toolkit tools and stdlib baselines.

## Setup

Uncomment dependencies in `requirements.txt` (pytest for tests; `requests` for corpus fetch).

## Corpus

1. `python -m benchmarks.fetch_corpus` — downloads into `benchmarks/corpus/_cache/` (gitignored).
2. `python -m benchmarks.corpus --profile <size>/<mix>` — samples a profile directory.

**1G hardware profiles:** `1G/balanced`, `1G/tiny-heavy`, `1G/media-heavy` (also `2G/*`, `5G/*`, `10G/*`, legacy `small/mixed`). Build each once before hardware runs:

```bash
python -m benchmarks.corpus --profile 1G/balanced
python -m benchmarks.corpus --profile 1G/tiny-heavy
python -m benchmarks.corpus --profile 1G/media-heavy
```

Note: 5G and 10G profiles currently produce identical output (~2.62GB, 111k files) due to cache size limit. Fetch additional datasets to make these sizes meaningful.

Partial downloads are allowed; runners print warnings for unavailable datasets. For publishable numbers, verify the full pool first.

## Runners

Each runner writes line-delimited JSON under `benchmarks/results/`. Records include `corpus_signature` (or `unverified` when `--ignore-manifest` is used), `wall_time_sec`, `bytes_per_sec`, `dst_bytes` (verified destination size), and device tags.

Default profile: `small/mixed` (synthetic smoke via `just check`). Hardware transfer runs use explicit `--corpus` and `--profile`.

**Multi-run methodology:** Use `just bench-multi transfer ...` to run a suite up to N times (default 10), stopping early when each (tool, scenario) pair has ≥3 non-outlier valid runs. Outliers are detected via modified Z-score (MAD, threshold 3.5). Medians over valid runs are written to `transfer_aggregate.json` under `--results-dir`. Single `just bench` runs measure once — use for quick checks only, not for publishable numbers.

**Example — full SSD then HDD matrix (3 drives, 1G/balanced):**

```powershell
just bench-multi transfer `
  --drive-a C:\bench --drive-b D:\bench --drive-c E:\bench `
  --profile 1G/balanced --corpus benchmarks/corpus/1G/balanced `
  --scenarios all --media-filter ssd --shuffle-tools --tool-seed 42 `
  --results-dir benchmarks/results/ssd-1g-balanced

just bench-multi transfer `
  --drive-a C:\bench --drive-b D:\bench --drive-c E:\bench `
  --profile 1G/balanced --corpus benchmarks/corpus/1G/balanced `
  --scenarios all --media-filter hdd --shuffle-tools --tool-seed 42 `
  --results-dir benchmarks/results/hdd-1g-balanced
```

Repeat with `1G/tiny-heavy` and `1G/media-heavy` (swap `--profile`, `--corpus`, and `--results-dir`). Omit `--drive-*` only for synthetic smoke — not for hardware baselines.

**Disk usage (analysis) — multi-run + report:**

```powershell
just bench-multi analysis `
  --drive-a C:\bench --drive-b D:\bench `
  --profile small/mixed --corpus benchmarks/corpus/small/mixed `
  --scenarios all --media-filter ssd `
  --results-dir benchmarks/results/small-mixed-ssd `
  --write-report --report-label small-mixed-ssd `
  --corpus-note "~2.0 GB, ~108K files"
```

Stages corpus to each drive scratch tree, compares `os_toolkit.usage` (scandir + usage tree) vs `os.walk` / bare `scandir` size sums. Writes `analysis_aggregate.json` and patches **`RESULTS.md`** when `--write-report` is set. Re-render: `just bench-report benchmarks/results/<dir>/analysis_aggregate.json --label <id>` (suite inferred from filename).

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

## Worker policy

Product copy (`file_transfer_pro`, bench `run_tool` → `ssd_copy` / `hdd_copy`) uses disk-aware caps from `os_toolkit.core.storage`:

- SSD destination: up to `cpu_count // 2` workers (`ssd_copy`)
- HDD destination: sequential walk (`hdd_copy`, one worker)
- Unknown media: conservative (max 2)

`workers_requested` / `workers_effective` in JSONL reflect the worker count passed to the bench subprocess (SSD runs only).

Use `just bench-quick` for a fast SSD cross-matrix smoke before a full hardware suite.

## Reference results

Committed summary tables: **[RESULTS.md](RESULTS.md)** (scenario-level detail, methodology, reproduce warnings).

Raw aggregates: `benchmarks/results/<label>/{analysis,transfer,zip}_aggregate.json` (gitignored). Update `RESULTS.md` when new orchestrator runs complete (`--write-report` for analysis).

## Reproduce on your hardware

See **[RESULTS.md](RESULTS.md)** for published numbers and scenario tables.

**Warnings before you run:**

1. **Downloads** — `just bench-fetch` pulls multi-GB dataset archives over the network.
2. **Disk space** — Each 1G profile needs ~1 GB on disk plus scratch trees on every `--drive-*` you use.
3. **Your machine** — Benchmarks perform **real full-tree copies** to paths you pass. Use dedicated empty folders (e.g. `C:\bench`), never production data.
4. **Time** — One `bench-multi` transfer suite often takes **hours** (orchestrator retries × scenarios × tools × ~1 GB). Six profile/filter combinations multiply that.
5. **Comparability** — Numbers apply only on the same hardware with the same `corpus_signature`.

```powershell
just install bench
just bench-fetch
python -m benchmarks.corpus --profile 1G/balanced

just bench-multi transfer --drive-a C:\bench --drive-b D:\bench --drive-c E:\bench `
  --profile 1G/balanced --corpus benchmarks/corpus/1G/balanced `
  --scenarios all --media-filter ssd --shuffle-tools --tool-seed 42 `
  --results-dir benchmarks/results/my-ssd-1g-balanced
```

Synthetic smoke only (no hardware, not publishable): `just check`.
