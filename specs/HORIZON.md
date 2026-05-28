# os-toolkit — Horizon

Long-horizon vision and scope contract for os-toolkit. Distinguishes **shipped**, **in-progress**, **planned**, and **speculative** work. Specs for individual tools live alongside this file under `specs/`.

---

## 1. Purpose of this document

This document locks the long-term product direction so scope decisions have a written contract. Anti-goals and domain boundaries limit scope drift. New contributors and agents can see where proposed work belongs before writing code. Items marked **planned** are intentional future work; items marked **speculative** or listed under **open horizon** are not commitments until promoted and spec’d.

---

## 2. What os-toolkit is and is not

### Character (the toolkit **is**)

- **Stdlib-first** with minimal mandatory dependencies.
- **OS-level utilities** for developers operating on local filesystems and environment.
- **Read-only by default**; destructive operations require explicit confirmation.
- **CLI-first for humans**, with room to grow machine-readable output for agents.
- **Idempotent and resumable** where applicable (copy, skip-if-same-size, dry-run patterns).
- **Composable** via shared code in `os_toolkit/core/` and domain packages.
- **Local-first**; runs on the developer’s machine, not as a hosted service.

### Anti-goals (the toolkit **is not**)

- **Not a backup tool** — we verify backups; we do not manage backup schedules or retention.
- **Not a full system monitor** — snapshot-style inspection, not always-on daemons.
- **Not a configuration manager** — we may diff configs; we do not deploy or enforce them.
- **Not a service or daemon** — no long-running agent required for core value.
- **Not a remote network scanner** — local ports and local dependency maps only.
- **Not a UI application** — root `*_pro.py` CLIs and stdout/filesystem artifacts.
- **Not a wholesale replacement** for rsync, robocopy, or similar — we add orchestration and policy on top of OS primitives, not a parallel copy engine for its own sake.
- **Not a cloud or data-exfiltration product** — no default off-machine upload of scanned content.

---

## 3. Shared primitives

### 3A — Shipped today (`os_toolkit/core/`)

| Module | API | Role |
|--------|-----|------|
| `paths.py` | `extended_path`, `rel_path`, `path_parts` | Windows long paths; relative path keys; path segment tuples |
| `format.py` | `human_readable_size`, `format_eta` | Operator-facing size and ETA strings |
| `config.py` | `cfg_get` | Optional `*_config.py` defaults; CLI wins |

### 3B — Planned primitives (enter when a **second** tool needs the same helper)

| Module | Role | Admission rule |
|--------|------|----------------|
| `workers.py` | Shared multiprocessing pool helpers | Second tool shares pool lifecycle beyond copy/archive |
| `hashing.py` | Standard digests (e.g. BLAKE2 via stdlib); optional xxhash behind flag | MVP-B file fingerprinting, backup_check stage 2, dedupe |
| `processes.py` | Cross-platform process introspection wrappers | port_finder, process_tree, resource_watch |
| `vcs.py` | Git subprocess helpers | git_repo_audit_pro |
| `serialize.py` | JSON/CSV writers with consistent schema | Multiple tools emitting tabular run artifacts |
| `terminal.py` | Progress and colored output | Deferred until **two or more** tools share the same UX |
| `errors.py` | Consistent `OSError` boundaries | Deferred until **two or more** tools share the same pattern |

`terminal.py`, `errors.py`, and early `workers.py` sketches were removed during migration cleanup because nothing yet justified them. They return only when reuse doctrine is satisfied: **primitives earn their place by use, not anticipation.**

---

## 4. Tools

For each tool: **name**, **domain**, **status**, **purpose**, **primitives**.

Status: `shipped` | `in-progress` | `planned` | `speculative`.

### A. Shipped today

| Tool | Domain | Status | Purpose | Primitives |
|------|--------|--------|---------|------------|
| `file_transfer_pro` | `transfer/` | shipped | Parallel directory copy with resume, strategies, optional adaptive workers | `core.paths`, `core.format`, `core.config`; introduces transfer copy/worker/strategies |
| `disk_analyzer_pro` | `analysis/` | shipped | Depth-limited usage tree for one root | `core.config`; `analysis.usage` |
| `smart_zip_pro` | `transfer/` | shipped | Folder-level zip recommendations; optional create | `core.config`, `core.format`, `core.paths`; `transfer.archive_*` |
| `analyze_pro` | `analysis/` | shipped | Subcommands: `usage`, `profile`, `compare` | `analysis.usage`, `profile`, `compare`, `runs`; compare uses optional ML stack |

### B. In-progress (current planning / execution round)

| Item | Domain | Status | Purpose | Primitives |
|------|--------|--------|---------|------------|
| Four-drive benchmark matrix | `benchmarks/` | in-progress | Multi-drive transfer/analysis measurement with physical-device tagging | Extends `benchmarks.devices`, new `benchmarks.matrix` |
| justfile + dependency docs | repo root | in-progress | Single operator catalog for test/bench/CLI | None in `os_toolkit/` |
| `specs/future-benchmarks.md` | `specs/` | in-progress | Plan resume/adaptive/strategy benches (no implementation this round) | N/A |

### C. Planned — Tier 1 (MVP-B: analysis depth)

| Tool / expansion | Domain | Status | Purpose | Primitives |
|------------------|--------|--------|---------|------------|
| **MVP-B analysis depth** | `analysis/` | planned | Per-file (or file-record) capture: size, hash, file-type, mtime; intra-tree duplicate detection; richer compare inputs | Introduces `core.hashing`; extends profile/features walker |
| `dedupe_pro` | `analysis/` | planned | User-facing duplicate report within one tree (and paths to identical content) | Reuses MVP-B walker + `hashing`; may share rows with profile |
| `analyze_pro compare` (expanded) | `analysis/` | planned | Compare using fingerprints where today only directory rollups exist | Reuses MVP-B features; existing compare + optional ML |

Not a new pillar — deepens **analysis** and adds one root CLI (`dedupe_pro`).

### D. Planned — Tier 2 (high reuse, after MVP-B)

| Tool | Domain | Status | Purpose | Primitives |
|------|--------|--------|---------|------------|
| `large_files_pro` | `analysis/` | planned | Top-N largest files; optional age filter | MVP-B walker, `core.format` |
| `junk_cleaner_pro` | `cleanup/` | planned | Reclaim space: **normal** (offline-regeneratable: `__pycache__`, `.pytest_cache`, build dirs) and **aggressive** (network re-download: `node_modules`, `.venv`, caches). Default dry-run | Walker + allowlists; new `cleanup/` domain |
| `backup_check_pro` | `analysis/` | planned | Read-only compare of source vs backup paths | **Stage 1:** size/mtime from MVP-B — missing, drift, extra. **Stage 2:** content hash equality. Domain: **analysis/** (owner decision) |

### E. Planned — Tier 3 (new domains, modest footprint)

| Tool | Domain | Status | Purpose | Primitives |
|------|--------|--------|---------|------------|
| `port_finder_pro` | `network/` | planned | Listening ports, owning process; optional kill-by-port (explicit confirm) | `processes.py` (planned) |
| `time_drift_pro` | `env/` | planned | System clock vs NTP | stdlib / subprocess NTP check |
| `path_health_pro` | `env/` | planned | Audit `PATH`: duplicates, missing dirs, shadowing | `path_parts`, path normalization |
| `tree_export_pro` | `analysis/` | planned | Export directory tree as JSON, Markdown, or HTML | MVP-B or usage walker, `serialize.py` |

### F. Planned — Tier 4 (heavier or newer domains)

| Tool | Domain | Status | Purpose | Primitives |
|------|--------|--------|---------|------------|
| `process_tree_pro` | `monitor/` | planned | Process tree snapshot: CPU/memory per process | **Optional mandatory dep:** `psutil` (see §7 exception policy) |
| `git_repo_audit_pro` | `vcs/` | planned | Multi-repo scan: branch, ahead/behind, dirty, stale; `--recommend-track` for untracked code-like dirs | `vcs.py` |
| `secret_hunter_pro` | `security/` | planned | Find keys/tokens in tree; optional git history; regex-first | Walker; `vcs.py` for history mode |
| `resource_watch_pro` | `monitor/` | planned | Threshold-oriented CPU/memory/disk watch (invocation-style, not daemon) | `psutil` if accepted; overlaps monitor domain with `process_tree_pro` |
| `dep_mapper_pro` | `network/` | planned | Local service/port dependency map | `port_finder` data + local connection tables |
| `env_check_pro` | `env/` | planned | Dev environment sanity: tool versions, paths, credential *presence* (not secret values) | `path_health` patterns + subprocess version probes |

### G. Speculative (needs more thought before scoping)

| Tool | Domain | Status | Notes |
|------|--------|--------|-------|
| `shell_history_pro` | `shell/` | speculative | History analytics; alias/automation candidates |
| `config_diff_pro` | `config/` | speculative | Semantic diff for JSON/YAML/TOML/INI/.env |
| `open_files_pro` | `monitor/` | speculative | Cross-platform lsof-like; revisit if `process_tree_pro` shows need |
| `pipeline_check_pro` | `ci/` | speculative | CI config security/optimization hints |
| `perf_bench_pro` | `perf/` | speculative | Likely overlaps `benchmarks/` rather than new root CLI |

**From codebase/handbook (not yet in tier list):** duplicate detection and rename/move via hash are named in `docs/REFACTOR.md` as analysis goals — absorbed into **MVP-B / dedupe_pro**, not separate speculative tools.

### H. Separate product (not os-toolkit core)

| Item | Status | Notes |
|------|--------|-------|
| **doc_gen** | deferred indefinitely | LLM hierarchical doc generator; may reuse walker/parsing; **not** in os-toolkit proper — breaks stdlib-first if bundled as mandatory |

---

## 5. Domains

| Domain | Scope (one line) | Anti-scope (one line) |
|--------|------------------|------------------------|
| **core** | Shared stdlib helpers used by multiple tools | No product features; no domain I/O |
| **analysis** | Read-mostly inspect, profile, compare, dedupe, backup verify | No deletion; no backup scheduling |
| **transfer** | Copy and local packaging (zip) | No sync/merge/delete source by default |
| **cleanup** | Reclaim space with explicit confirm and dry-run default | Not backup; not “fix my system” daemon |
| **network** | Local ports, connections, dependency map | No remote host scanning |
| **env** | Machine environment: PATH, clock, tool versions | No config deployment |
| **monitor** | Point-in-time or short-run resource/process snapshots | No always-on monitoring product |
| **vcs** | Git inspection across many repos | No git hosting; no force-push automation |
| **security** | Secret/credential discovery in local trees | Not AV; not pentest |
| **shell** (speculative) | Shell history analytics | Not a shell replacement |
| **config** (speculative) | Config file semantic diff | Not CMDB or deploy |
| **ci** (speculative) | CI file analysis | Not a CI runner |
| **perf** (speculative) | Micro-benchmark helpers | Prefer `benchmarks/` for toolkit perf |

**benchmarks/** is harness and corpus infrastructure, not a user-facing domain package.

---

## 6. Reuse map

| Planned tool | Reuses (today or MVP-B) | Introduces |
|--------------|-------------------------|------------|
| MVP-B / `dedupe_pro` | `paths`, profile walker pattern | `hashing`, per-file feature schema |
| `large_files_pro` | MVP-B walker, `format` | — |
| `junk_cleaner_pro` | `paths`, walker | `cleanup/` policies, delete confirm boundary |
| `backup_check_pro` stage 1 | MVP-B mtime/size records | comparison report schema |
| `backup_check_pro` stage 2 | `hashing`, stage 1 | content-equal verification |
| `tree_export_pro` | walker, `serialize` | export templates |
| `port_finder_pro` | `processes` | `network/` |
| `time_drift_pro` | subprocess / stdlib time | `env/` |
| `path_health_pro` | `path_parts` | `env/` |
| `process_tree_pro` | `processes` | `monitor/`; **psutil** |
| `git_repo_audit_pro` | `vcs` | `vcs/` |
| `secret_hunter_pro` | walker, optional `vcs` | `security/` regex sets |
| `resource_watch_pro` | `processes`, monitor patterns | thresholds |
| `dep_mapper_pro` | `port_finder`, local conn read | graph output |
| `env_check_pro` | `path_health`, subprocess | checklists |

**Dense reuse cluster:** MVP-B file inventory feeds `dedupe_pro`, `large_files_pro`, `backup_check_pro`, expanded `compare`, and `tree_export_pro`. **Sparse reuse:** `monitor/` and `security/` tools share less with analysis walker until `processes`/`vcs` exist.

---

## 7. Stdlib-first and its one exception

**Commitment:** Production tools stay **stdlib-only** for mandatory runtime dependencies. Optional dev/bench deps live commented in `requirements.txt` with Used-by / Why lines.

**Explicit exception — ML stack for `analyze_pro compare`:**

| Package | Role |
|---------|------|
| numpy, pandas, tqdm | Feature matrices, CSV load, batch similarity |
| sklearn (via `name_similarity` tfidf) | Name similarity backend |
| Optional: rapidfuzz, sentence-transformers | Alternate `--name-sim` backends |

**Why accepted:** Compare is fundamentally vector similarity over directory feature rows; stdlib-only alternatives are materially weaker for this path. Gated by `@pytest.mark.requires_ml` and optional install; not required for usage/profile/transfer/zip.

**Policy going forward:** New tools must not add **mandatory** non-stdlib dependencies. Optional deps behind flags are permitted but discouraged. Tier 4 `psutil` for `process_tree_pro` / `resource_watch_pro` requires an explicit future owner decision to become a **second** documented exception before implementation.

---

## 8. Open horizon

Items to explore before promotion to **planned**:

- **Agent-facing output mode** — structured JSON (or similar) across tools for automation.
- **Cross-tool orchestration** — chaining outputs (e.g. profile → compare → backup_check) without manual path passing.
- **Repo mode for analysis** — content-aware scanning scope (e.g. analysis tree that feeds secret discovery policies).
- **Long-running / daemon-shaped tools** — remain out of scope unless a concrete need appears; `resource_watch_pro` stays invocation-bound.

**Speculative backlog** — see §4G (`shell_history_pro`, `config_diff_pro`, `open_files_pro`, `pipeline_check_pro`, `perf_bench_pro`).

**Planning notes from verification (current code, not horizon promises):**

- Today `profile` / `features.csv` store **directory rollups** only (`size_bytes`, `files`, `folders`, `depth`, `name`, `path`) — no per-file hash. MVP-B closes that gap.
- Byte-identical **cross-tree** file match and **intra-tree duplicate** listing are **not** possible on shipped code; Tier 1 addresses duplicates; `backup_check` stage 2 addresses backup content equality.

**Owner decisions recorded for this document:**

| Topic | Decision |
|-------|----------|
| `backup_check_pro` domain | **analysis/** |
| `backup_check_pro` delivery | **Two stages** — stat/mtime first (post MVP-B capture), hash verification second |

**Agent notes (no owner answer required — factual):**

| Topic | Note |
|-------|------|
| Tool tiering | Tier order matches dependency order (MVP-B before backup_check stage 2, before large_files/dedupe). |
| Destructive tools | `junk_cleaner_pro` and `port_finder` kill mode align with character only if dry-run/confirm remain default. |
| Anti-goals | Consider adding “not an enterprise MDM/agent” if scope questions recur — not added without owner request. |
| `resource_watch_pro` vs `process_tree_pro` | Both in monitor/; differentiate by snapshot vs threshold watch before specs. |

---

*Horizon doc version: planning round MVP-A context. Update when tools ship or tiers change. Per-tool guarantees belong in `specs/<tool>.md`.*
