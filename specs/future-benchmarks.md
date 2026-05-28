# Future benchmarks (planning only)

This document plans adversarial and observability benchmarks **not implemented** in Phase A. Each section traces to a product guarantee and defines exact CLI, metrics, success criteria, and effort. No code in this file is executable.

---

## Resume adversarial

**Traces to:** [`specs/file_transfer.md`](file_transfer.md) — *Guarantees*: dry-run performs no writes; re-run skips files where destination size matches source. *Adversarial surfaces*: user interrupt; partial destination from a prior run.

**Why it matters:** Resume is a core transfer promise. Without kill-and-restart measurement, regressions in skip logic or double-copy risk ship silently.

### Setup

- Fixed corpus under `benchmarks/corpus/<tier>/<sub>/` with known `corpus_signature`.
- Destination on a separate path (or drive) from source.
- Tree hash utility (stdlib walk + per-file SHA-256) for before/after comparison — bench-only, not product code.

### Exact CLI (proposed)

```bash
python benchmarks/run_resume.py \
  --source <corpus_dir> \
  --dest <dest_dir> \
  --kill-at 10,50,90 \
  --kill-phase copy \
  --tool os_toolkit.transfer \
  --workers 4 \
  --output benchmarks/results/resume_<UTC>.jsonl
```

| Flag | Purpose |
|------|---------|
| `--kill-at` | Percent complete (or file count) to SIGINT/SIGTERM child |
| `--kill-phase` | `copy` \| `pre_scan` \| `verify` |
| `--tool` | `os_toolkit.transfer` only in v1 |

Additional cases (separate runs or matrix rows):

- Kill during **pre-scan** (before first byte copied).
- Kill at **90%** then re-run full job (must skip ≥90% of files by count or bytes).
- Kill **before verify** if verify phase exists in tool version under test.

### Metrics

| Metric | Source |
|--------|--------|
| `exit_status` | Child process |
| `files_copied`, `files_skipped` | Parse transfer summary or instrument hook |
| `wall_time_sec` | Harness |
| `dest_tree_hash` vs `source_tree_hash` | Post-run |
| `double_copy_detected` | Destination mtime/size drift on skipped files |

### Success criteria

1. After interrupted run + full re-run: `dest_tree_hash == source_tree_hash`.
2. Re-run reports skipped count ≥ files already correct from partial run (no full re-copy of completed files).
3. No duplicate divergent copies (same relative path, different content).
4. Dry-run kill: zero bytes written to destination.

### Effort estimate

**Medium — 2–3 days:** harness subprocess + kill timing, hash compare, JSONL schema, one owner-hardware validation pass.

---

## Adaptive observability

**Traces to:** [`specs/file_transfer.md`](file_transfer.md) — optional adaptive worker tuning; disabled for dry-run, single-worker, or tiny file counts.

**Why it matters:** Adaptive mode is only valuable if it beats a fixed worker count on realistic corpora. The bench must show *when* and *by how much*, not just that the flag runs.

### Setup

- Same corpus signature across A/B runs.
- Small export from `parallel_copy` (or probe module): `(elapsed_sec, active_workers)` samples at coarse intervals — **minimal product hook**, gated for bench builds or verbosity 2.

### Exact CLI (proposed)

```bash
python benchmarks/run_adaptive.py \
  --source <corpus_dir> \
  --dest <dest_dir> \
  --workers 4 \
  --adaptive \
  --output benchmarks/results/adaptive_on_<UTC>.jsonl

python benchmarks/run_adaptive.py \
  --source <corpus_dir> \
  --dest <dest_dir> \
  --workers 4 \
  --no-adaptive \
  --output benchmarks/results/adaptive_off_<UTC>.jsonl
```

Compare script (or notebook) reads both JSONL files.

### Metrics

| Metric | Source |
|--------|--------|
| `wall_time_sec` | Harness |
| `bytes_per_sec` | `total_bytes / wall_time_sec` |
| `worker_samples` | List of `{t, workers}` from probe |
| `bytes_at_t` | Optional cumulative bytes for throughput curve |

### Success criteria

1. On owner hardware with mixed-size corpus: adaptive `wall_time_sec` ≤ fixed −5% **or** documented failure with worker trace explaining why.
2. Worker trace shows at least one change in active workers when adaptive is on.
3. Dry-run and `workers=1`: adaptive path not exercised (matches product guard).

### Effort estimate

**Medium–high — 3–5 days:** probe hooks in `os_toolkit.transfer.copy`, paired runners, comparison report, owner validation.

---

## Strategy ordering

**Traces to:** [`specs/file_transfer.md`](file_transfer.md) — selectable strategy (`smallest-first`, `largest-first`, `balanced`).

**Why it matters:** Strategies should produce **measurably different completion curves** on mixed corpora; otherwise the flag is cosmetic.

### Setup

- Mixed-size synthetic or manifest corpus (many small + few large files).
- Progress sampling: `% of total bytes copied` vs `elapsed_sec` (requires progress callback or log parse).

### Exact CLI (proposed)

```bash
for strategy in smallest-first largest-first balanced; do
  python benchmarks/run_strategy.py \
    --source <corpus_dir> \
    --dest <dest_dir_<strategy>> \
    --strategy "$strategy" \
    --workers 4 \
    --sample-every-sec 1 \
    --output "benchmarks/results/strategy_${strategy}_<UTC>.jsonl"
done
```

### Metrics

| Metric | Source |
|--------|--------|
| `completion_curve` | `[{elapsed_sec, pct_bytes_done}, ...]` |
| `wall_time_sec` | End of run |
| `p50_file_latency` | Optional per-file timing if instrumented |

### Success criteria

1. At least two strategies differ by ≥10% time-to-50%-bytes on the same corpus (owner hardware).
2. Curves are monotonic in `% bytes` (no backward progress).
3. All strategies: `dest_tree_hash == source_tree_hash`.

### Effort estimate

**Low–medium — 1–2 days** if progress is already exposed; **+1–2 days** if `parallel_copy` needs a lightweight progress callback for sampling.

---

## Out of scope for these plans

- CI pass/fail gates on throughput (benchmarks measure only).
- Corpus fetch automation (see `just bench-fetch` and MVP-A).
- Zip benchmark drive matrix (zip stays single-root scan).
