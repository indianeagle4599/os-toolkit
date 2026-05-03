# TODO — os-functions

Working task list for **planning**, **ordering**, and **tracking**. Maintain **Kaizen-sized** steps; defer anything not justified by immediate scope (see **`AGENTS.md`**, **`docs/CONTEXT.md`**, **`docs/REFACTOR.md`**).

- **Next up:** a short, ordered runway — trim or **[X]** as items complete.
- **Tasks:** grouped by area; **[ ]** open, **[X]** done — remove **[X]** sub-items when pruning after a milestone.

---

## Next up

[X] Config file for `file_transfer_pro.py` — importable defaults; CLI args override.
[X] Review and organise `migration_pro/` — initial repo-like structure, README, TODO, and run artifacts in place.
[X] `file_transfer_pro.py` — adaptive probe gate semantics (`bytes_moved`), feeder cap tied to live pool size, chunked copy (`copyfileobj` + `copystat`) + shared partial-byte progress.
[X] Phase 0 docs — `docs/REFACTOR.md`, `docs/ARCHITECTURE.md`; handbook updates (`CONTEXT`, `AGENTS`, `CLAUDE`, `migration_pro/README`, `.cursor` bootstrap).
[ ] Shared formatting/paths — superseded by **`os_functions/core/`** per **`docs/REFACTOR.md`** Phase 1–2 (old “utils.py” item folds into that).

---

## Tasks

### file_transfer_pro

    [X] Pre-scan with file size distribution before transfer starts.
    [X] Transfer strategy: smallest-first, largest-first, balanced (interleaved).
    [X] Size-based live progress bar with bytes%, speed (MB/s), and ETA.
    [X] Revised verbosity model: 0=quiet, 1=normal, 2=per-file errors.
    [X] Uniform worker return tuple; single getsize call per file at scan time.
    [X] Config file with importable defaults (source, dest, strategy, workers, verbosity, dry-run); CLI args override config.
    [X] Adaptive probe: timer-driven gates use `bytes_moved` (completed + in-flight copy bytes) vs remaining job bytes; feeder `target_in_flight` tracks live `pool_workers`.
    [X] Chunked data copy: `shutil.copyfileobj` + `shutil.copystat`; `multiprocessing.Value`/`Lock` for in-flight bytes (smooth speed / progress during large files).
    [ ] Quantile / per-worker queue scheduling (HDD seek contention); deferred until measured against current adaptive + chunking stack.

---

### Migration / `os_functions` refactor

See **`docs/REFACTOR.md`** §5 for full descriptions.

    [ ] Phase 1 — Create `os_functions/` + `core/` (paths, format, terminal, config, ui, errors).
    [ ] Phase 2 — Wire `file_transfer_pro.py` / `disk_analyzer_pro.py` shims to `os_functions.core` (no behavior change).
    [ ] Phase 3 — `os_functions/analysis/*`; unified `analyze` CLI; absorb `migration_pro` + disk analyzer.
    [ ] Phase 4 — `os_functions/transfer/*`; extract from `file_transfer_pro.py`.
    [ ] Phase 5 — Depth: duplicates (intra), ML path, rename/conflict analysis milestones.
    [ ] Phase 6 — Migration executor (merge apply, plans) — last.
    [ ] Parallel directory delete (dry-run default, confirm, trash-first) — design in REFACTOR §7; low priority until scheduled.

---

### disk_analyzer_pro

    [ ] No active tasks — stable as-is.
    [ ] Future: expose a structured output mode usable by agents (JSON alongside human output).

---

### migration_pro

    [X] Review current state — decide what's complete vs. what needs building.
    [X] Add migration-specific README / TODO and repo-like module layout.
    [ ] Agree on whether disk analysis belongs in a migration orchestrator (deferred — not before migration_pro is stable).

---

### Repo & hygiene

    [X] Git repo initialised.
    [X] AGENTS.md / CLAUDE.md / docs/CONTEXT.md scaffolded.
    [X] .gitignore with AGENTS.md, CLAUDE.md, .cursor/, __pycache__, .cache/.
    [ ] Shared `utils.py` — **superseded:** use **`os_functions/core/`** per **`docs/REFACTOR.md`**; remove this line when Phase 2 lands.
    [ ] README.md with first-run instructions (only when welcomed).

---

### Agent-facing interfaces (future)

_Not in scope until the tool set is more complete._

    [ ] Design structured output mode for each tool (JSON alongside human-readable CLI).
    [ ] Each script callable as a building block by an OS/infra-level agent.

---

### Future scripts (from backlog — not commitments until approved)

    [ ] resource_watch.py — real-time CPU/memory/disk monitor with threshold alerting.
    [ ] dep_mapper.py — network service dependency visualiser.
    [ ] doc_gen.py — auto-documentation generator (Python/JS/Java).
    [ ] env_check.py — dev environment sanity checker (tool versions, cloud credentials).
    [ ] pipeline_check.py — CI/CD config auditor and security misconfiguration detector.
    [ ] secret_hunter.py — API key/credential scanner with git history support.
    [ ] perf_bench.py — execution time and memory profiler with comparative analysis.
