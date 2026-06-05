# Transfer benchmark results (hardware)

Owner-machine copy benchmarks for **`os_toolkit.transfer`** (ours) vs **`stdlib.copytree`** and **`robocopy`**. Raw JSONL and aggregates live under `benchmarks/results/` (gitignored); this file is the committed summary.

**Machine:** Windows, drives `C:\bench`, `D:\bench` (SSD), `E:\bench` (HDD).  
**Corpus:** ~1.00 GB per profile (`dst_bytes` ≈ 1.00×10⁹). Signatures: `06857ead…` (balanced, tiny-heavy), `812ec5f0…` (media-heavy).

---

## Methodology

| Item | Value |
|------|--------|
| Runner | `just bench-multi transfer` → `benchmarks/orchestrator.py` |
| Runs per (tool, scenario) | ≥3 valid after MAD outlier filter (threshold 3.5); up to 10 attempts |
| Metric | Median `wall_time_sec` and median `bytes_per_sec` from `transfer_aggregate.json` |
| Isolation | Each tool in a fresh subprocess (`benchmarks/run_tool.py`); corpus staged to source-drive scratch |
| Tool order | `--shuffle-tools --tool-seed 42` |
| Throughput | `dst_bytes / wall_time` (verified destination size) |

### Scenarios aggregated

With `--drive-a C:\bench --drive-b D:\bench --drive-c E:\bench` and `--scenarios all`:

| Filter | Drives included | Scenario pairs | Meaning |
|--------|-----------------|----------------|---------|
| `--media-filter ssd` | `a`, `b` only (both SSD) | `a_to_a`, `a_to_b`, `b_to_a`, `b_to_b` | Same-disk and cross-SSD copies |
| `--media-filter hdd` | Any pair where source or dest is HDD (`c` = E:) | e.g. `c_to_c`, `a_to_c`, `c_to_a`, … | HDD within and SSD↔HDD |

Scenario id format: `{src_drive}_to_{dst_drive}` (e.g. `a_to_b` = copy from drive-a scratch to drive-b scratch).

### Corpus profiles (1G)

| Profile | File mix |
|---------|----------|
| `1G/balanced` | Mixed tiny + medium files across datasets |
| `1G/tiny-heavy` | Many small files (metadata / seek stress) |
| `1G/media-heavy` | Larger files (throughput-oriented) |

---

## Rollup (median across scenarios)

Values are the **median of per-scenario medians** within each block (quick overall read; see scenario tables for detail).

| Profile | Storage | Status | **os_toolkit.transfer** (ours) | stdlib.copytree | robocopy |
|---------|---------|--------|--------------------------------|-----------------|----------|
| `1G/balanced` | SSD | **complete** | **~14.3 s**, **~70 MB/s** | ~20.8 s, ~48 MB/s | ~24.2 s, ~42 MB/s |
| `1G/balanced` | HDD | **complete** | **~60 s**, **~17 MB/s**† | ~62 s, ~16 MB/s | ~81 s, ~12 MB/s |
| `1G/tiny-heavy` | SSD | **complete** | **~15.6 s**, **~65 MB/s** | ~21.3 s, ~47 MB/s | ~25.5 s, ~39 MB/s |
| `1G/tiny-heavy` | HDD | **complete** | **~63 s**, **~16 MB/s**† | ~68 s, ~15 MB/s | ~90 s, ~12 MB/s |
| `1G/media-heavy` | SSD | **complete** | **~1.8 s**, **~553 MB/s** | ~2.6 s, ~392 MB/s | ~2.7 s, ~370 MB/s |
| `1G/media-heavy` | HDD | **complete** | **~10.7 s**, **~95 MB/s**† | ~11.3 s, ~88 MB/s | ~11.3 s, ~90 MB/s |

†HDD filter mixes slow HDD-touching paths (`a_to_c`, `c_to_c` ~60 s) with fast SSD-leg paths (`c_to_a`, `c_to_b` ~13–16 s). See scenario tables — rollup median is **not** a single operating point.

*SSD rollup: median of four scenario medians (wall 11.8–16.6 s; throughput 60–85 MB/s for ours).*

---

## os_toolkit.transfer (ours) — scenario detail

### 1G/balanced · SSD · complete

4 orchestrator runs; `pairs_satisfied: true`. Command:

```powershell
just bench-multi transfer --drive-a C:\bench --drive-b D:\bench --drive-c E:\bench `
  --profile 1G/balanced --corpus benchmarks/corpus/1G/balanced `
  --scenarios all --media-filter ssd --shuffle-tools --tool-seed 42 `
  --results-dir benchmarks/results/ssd-1g-balanced
```

| Scenario | Median wall | Median throughput | Valid runs |
|----------|-------------|-------------------|------------|
| `a_to_a` (C→C) | 15.6 s | 64.2 MB/s | 4/4 |
| `b_to_b` (D→D) | 13.0 s | 76.7 MB/s | 3/4 |
| `a_to_b` (C→D) | 11.8 s | 84.9 MB/s | 4/4 |
| `b_to_a` (D→C) | 16.6 s | 60.2 MB/s | 3/4 |

### 1G/balanced · HDD · complete

5 orchestrator runs (4 attempts until `pairs_satisfied`); scenarios with HDD (`E:\bench` = drive `c`).

```powershell
just bench-multi transfer --drive-a C:\bench --drive-b D:\bench --drive-c E:\bench `
  --profile 1G/balanced --corpus benchmarks/corpus/1G/balanced `
  --scenarios all --media-filter hdd --shuffle-tools --tool-seed 42 `
  --results-dir benchmarks/results/hdd-1g-balanced
```

| Scenario | Median wall | Median throughput | Valid runs |
|----------|-------------|-------------------|------------|
| `a_to_c` (C→E, SSD→HDD) | 61.8 s | 16.2 MB/s | 3/4 |
| `b_to_c` (D→E, SSD→HDD) | 62.3 s | 16.0 MB/s | 3/4 |
| `c_to_a` (E→C, HDD→SSD) | 15.6 s | 63.9 MB/s | 3/4 |
| `c_to_b` (E→D, HDD→SSD) | 12.8 s | 78.0 MB/s | 4/4 |
| `c_to_c` (E→E, HDD same disk) | 60.0 s | 16.7 MB/s | 4/4 |

### 1G/tiny-heavy · SSD · complete

4 orchestrator runs; `pairs_satisfied: true`.

```powershell
just bench-multi transfer --drive-a C:\bench --drive-b D:\bench --drive-c E:\bench `
  --profile 1G/tiny-heavy --corpus benchmarks/corpus/1G/tiny-heavy `
  --scenarios all --media-filter ssd --shuffle-tools --tool-seed 42 `
  --results-dir benchmarks/results/ssd-1g-tiny-heavy
```

| Scenario | Median wall | Median throughput | Valid runs |
|----------|-------------|-------------------|------------|
| `a_to_a` (C→C) | 16.9 s | 59.1 MB/s | 3/4 |
| `b_to_b` (D→D) | 14.2 s | 70.3 MB/s | 3/4 |
| `a_to_b` (C→D) | 12.7 s | 78.6 MB/s | 3/4 |
| `b_to_a` (D→C) | 17.1 s | 58.4 MB/s | 4/4 |

### 1G/tiny-heavy · HDD · complete

4 orchestrator runs; `pairs_satisfied: true`.

| Scenario | Median wall | Median throughput | Valid runs |
|----------|-------------|-------------------|------------|
| `a_to_c` (C→E) | 63.6 s | 15.7 MB/s | 4/4 |
| `b_to_c` (D→E) | 65.6 s | 15.2 MB/s | 3/4 |
| `c_to_a` (E→C) | 19.1 s | 53.2 MB/s | 4/4 |
| `c_to_b` (E→D) | 13.1 s | 76.5 MB/s | 3/4 |
| `c_to_c` (E→E) | 62.9 s | 15.9 MB/s | 3/4 |

### 1G/media-heavy · SSD · complete

4 orchestrator runs; `pairs_satisfied: true`. Larger files → higher MB/s, lower metadata overhead (wall times ~2 s).

| Scenario | Median wall | Median throughput | Valid runs |
|----------|-------------|-------------------|------------|
| `a_to_a` (C→C) | 1.9 s | 522 MB/s | 4/4 |
| `b_to_b` (D→D) | 1.4 s | 716 MB/s | 3/4 |
| `a_to_b` (C→D) | 1.8 s | 562 MB/s | 3/4 |
| `b_to_a` (D→C) | 1.8 s | 545 MB/s | 3/4 |

### 1G/media-heavy · HDD · complete

4 orchestrator runs; `pairs_satisfied: true`. Larger files → faster than balanced/tiny-heavy on HDD (~10 s SSD→HDD vs ~63 s).

| Scenario | Median wall | Median throughput | Valid runs |
|----------|-------------|-------------------|------------|
| `a_to_c` (C→E) | 10.5 s | 95.0 MB/s | 3/4 |
| `b_to_c` (D→E) | 10.7 s | 93.6 MB/s | 3/4 |
| `c_to_a` (E→C) | 2.5 s | 405 MB/s | 4/4 |
| `c_to_b` (E→D) | 2.9 s | 351 MB/s | 3/4 |
| `c_to_c` (E→E) | 10.8 s | 92.5 MB/s | 3/4 |

---

## Baselines — scenario detail

### 1G/balanced · SSD · stdlib.copytree

| Scenario | Median wall | Median throughput | Valid runs |
|----------|-------------|-------------------|------------|
| `a_to_a` | 21.8 s | 45.8 MB/s | 3/4 |
| `b_to_b` | 20.2 s | 49.6 MB/s | 3/4 |
| `a_to_b` | 18.3 s | 54.5 MB/s | 3/4 |
| `b_to_a` | 22.8 s | 44.0 MB/s | 3/4 |

### 1G/balanced · SSD · robocopy

| Scenario | Median wall | Median throughput | Valid runs |
|----------|-------------|-------------------|------------|
| `a_to_a` | 24.4 s | 40.9 MB/s | 3/4 |
| `b_to_b` | 24.3 s | 41.4 MB/s | 4/4 |
| `a_to_b` | 21.1 s | 47.3 MB/s | 3/4 |
| `b_to_a` | 26.8 s | 37.2 MB/s | 3/4 |

### 1G/balanced · HDD · stdlib.copytree

| Scenario | Median wall | Median throughput | Valid runs |
|----------|-------------|-------------------|------------|
| `a_to_c` | 63.0 s | 15.9 MB/s | 3/4 |
| `b_to_c` | 67.4 s | 14.9 MB/s | 4/4 |
| `c_to_a` | 20.8 s | 48.1 MB/s | 3/4 |
| `c_to_b` | 17.9 s | 55.8 MB/s | 3/4 |
| `c_to_c` | 61.8 s | 16.2 MB/s | 4/4 |

### 1G/balanced · HDD · robocopy

| Scenario | Median wall | Median throughput | Valid runs |
|----------|-------------|-------------------|------------|
| `a_to_c` | 81.3 s | 12.3 MB/s | 3/4 |
| `b_to_c` | 82.4 s | 12.1 MB/s | 4/4 |
| `c_to_a` | 23.5 s | 42.6 MB/s | 3/4 |
| `c_to_b` | 20.1 s | 49.8 MB/s | 3/4 |
| `c_to_c` | 88.2 s | 11.3 MB/s | 3/4 |

### 1G/tiny-heavy · SSD · stdlib.copytree

| Scenario | Median wall | Median throughput | Valid runs |
|----------|-------------|-------------------|------------|
| `a_to_a` | 22.0 s | 45.5 MB/s | 4/4 |
| `b_to_b` | 20.6 s | 48.6 MB/s | 4/4 |
| `a_to_b` | 19.5 s | 51.4 MB/s | 4/4 |
| `b_to_a` | 24.6 s | 40.8 MB/s | 4/4 |

### 1G/tiny-heavy · SSD · robocopy

| Scenario | Median wall | Median throughput | Valid runs |
|----------|-------------|-------------------|------------|
| `a_to_a` | 25.6 s | 39.1 MB/s | 4/4 |
| `b_to_b` | 25.3 s | 39.6 MB/s | 4/4 |
| `a_to_b` | 22.3 s | 44.8 MB/s | 3/4 |
| `b_to_a` | 27.9 s | 36.0 MB/s | 4/4 |

### 1G/tiny-heavy · HDD · stdlib.copytree

| Scenario | Median wall | Median throughput | Valid runs |
|----------|-------------|-------------------|------------|
| `a_to_c` | 66.1 s | 15.1 MB/s | 3/4 |
| `b_to_c` | 68.2 s | 14.7 MB/s | 3/4 |
| `c_to_a` | 29.0 s | 34.5 MB/s | 3/4 |
| `c_to_b` | 19.8 s | 50.5 MB/s | 3/4 |
| `c_to_c` | 68.4 s | 14.7 MB/s | 4/4 |

### 1G/tiny-heavy · HDD · robocopy

| Scenario | Median wall | Median throughput | Valid runs |
|----------|-------------|-------------------|------------|
| `a_to_c` | 83.1 s | 12.0 MB/s | 3/4 |
| `b_to_c` | 90.4 s | 11.1 MB/s | 3/4 |
| `c_to_a` | 30.9 s | 32.4 MB/s | 4/4 |
| `c_to_b` | 24.7 s | 40.5 MB/s | 4/4 |
| `c_to_c` | 91.4 s | 11.0 MB/s | 4/4 |

### 1G/media-heavy · SSD · stdlib.copytree

| Scenario | Median wall | Median throughput | Valid runs |
|----------|-------------|-------------------|------------|
| `a_to_a` | 2.9 s | 343 MB/s | 4/4 |
| `b_to_b` | 2.5 s | 394 MB/s | 4/4 |
| `a_to_b` | 2.4 s | 426 MB/s | 4/4 |
| `b_to_a` | 2.6 s | 389 MB/s | 3/4 |

### 1G/media-heavy · SSD · robocopy

| Scenario | Median wall | Median throughput | Valid runs |
|----------|-------------|-------------------|------------|
| `a_to_a` | 2.9 s | 342 MB/s | 3/4 |
| `b_to_b` | 2.7 s | 370 MB/s | 3/4 |
| `a_to_b` | 2.7 s | 376 MB/s | 4/4 |
| `b_to_a` | 2.7 s | 364 MB/s | 3/4 |

### 1G/media-heavy · HDD · stdlib.copytree

| Scenario | Median wall | Median throughput | Valid runs |
|----------|-------------|-------------------|------------|
| `a_to_c` | 11.4 s | 88.1 MB/s | 4/4 |
| `b_to_c` | 11.3 s | 88.3 MB/s | 3/4 |
| `c_to_a` | 5.2 s | 230 MB/s | 4/4 |
| `c_to_b` | 4.7 s | 237 MB/s | 4/4 |
| `c_to_c` | 10.0 s | 100 MB/s | 3/4 |

### 1G/media-heavy · HDD · robocopy

| Scenario | Median wall | Median throughput | Valid runs |
|----------|-------------|-------------------|------------|
| `a_to_c` | 11.3 s | 88.5 MB/s | 3/4 |
| `b_to_c` | 11.1 s | 89.8 MB/s | 3/4 |
| `c_to_a` | 3.4 s | 298 MB/s | 3/4 |
| `c_to_b` | 7.0 s | 143 MB/s | 3/4 |
| `c_to_c` | 13.9 s | 75.5 MB/s | 4/4 |

---

## Run health

| Results dir | Aggregate | JSONL rows/run | Failures | Verdict |
|-------------|-----------|----------------|----------|---------|
| `ssd-1g-balanced/` | `pairs_satisfied: true` | 12 | 0 | **Good** |
| `hdd-1g-balanced/` | `pairs_satisfied: true` | 15 | 0 | **Good** |
| `ssd-1g-tiny-heavy/` | `pairs_satisfied: true` | 12 | 0 | **Good** |
| `hdd-1g-tiny-heavy/` | `pairs_satisfied: true` | 15 | 0 | **Good** |
| `ssd-1g-media-heavy/` | `pairs_satisfied: true` | 12 | 0 | **Good** |
| `hdd-1g-media-heavy/` | `pairs_satisfied: true` | 15 | 0 | **Good** |

All six suites: `pairs_satisfied: true`, no failed rows.

---

## Status

**6/6 suites complete** (2026-06-05). Ready for docs commit.

---

## Reproduce on your hardware

Full prep, flags, and **warnings** (downloads, disk space, real copies, runtime): **[benchmarks/README.md § Reproduce on your hardware](README.md#reproduce-on-your-hardware)**.
