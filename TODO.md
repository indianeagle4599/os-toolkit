# TODO — os-toolkit (local)

Gitignored. Align with `specs/HORIZON.md` and `specs/PHASES.md`.

## Shipped on feature/quality-engineering (local, not pushed to origin/master)

- [X] Migration: `os_toolkit/core`, `analysis`, `transfer`; root CLIs; `migration_pro/` removed
- [X] QE: specs (6 tools), pytest (20 fast), benchmarks harness (3 runners)
- [X] `runs/` gitignored; LICENSE, NOTICE, `requirements.txt` (commented)

## Next (prompt 3 — Phase A)

- [ ] Commit 0: AGENTS Top-Down Intent + dependency documentation rules
- [ ] `justfile` + `requirements.txt` comments + README (Installing just)
- [ ] Four-drive matrix (`devices`, `matrix.py`, `run_transfer`, `run_analysis`)
- [ ] `specs/future-benchmarks.md` (plan only)

## Then (MVP-A)

- [ ] Owner drive paths + real transfer bench matrix run (owner hardware)
- [ ] `BENCHMARKS.md` at repo root (no JSONL committed)

## PHASES roadmap (not started)

- [ ] MVP-B: per-file hash, `dedupe_pro`, expanded compare
- [ ] 2a: `large_files_pro`, `tree_export_pro`
- [ ] 2b-1 / 2b-2: `backup_check_pro`
- [ ] 2c: `junk_cleaner_pro`
- [ ] 2d: perf bench promotion (conditional)
- [ ] Phase 3–5: env, vcs, security (medium detail)
- [ ] Phase 6: network/monitor (deferred schedule)

## Deferred / speculative (HORIZON only)

- `shell_history`, `config_diff`, `open_files`, `pipeline_check`, `perf_bench_pro` (product)
- `doc_gen` (separate product)

## Hygiene

- [X] Retire stale `migration_pro/` task bullets (superseded by shipped migration)
- [ ] Optional: refresh local `docs/CONTEXT.md` from specs (`docs/` still gitignored)
- [ ] Push to origin — single decision after MVP-A review and `BENCHMARKS.md` is interpreted
