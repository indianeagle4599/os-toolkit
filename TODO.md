# TODO — os-toolkit (local)

Gitignored. Align with `specs/HORIZON.md` and `specs/PHASES.md`.

## Shipped (local branch)

- [X] Migration: `os_toolkit/core`, `analysis`, `transfer`; root CLIs; `migration_pro/` removed
- [X] QE: specs, pytest (67 fast), benchmarks harness + orchestrator
- [X] Phase A: `justfile`, multi-drive matrix, `run_tool`, aggregate/outliers
- [X] MVP-A: six 1G transfer suites; [`benchmarks/RESULTS.md`](benchmarks/RESULTS.md) summary
- [X] Transfer: disk-aware `ssd_copy`/`hdd_copy`, robocopy backend, byte progress
- [X] `runs/` gitignored; LICENSE, NOTICE, `requirements.txt` (commented)

## Next (owner decision)

- [ ] MVP-B: per-file hash, `dedupe_pro`, expanded compare
- [ ] Commit/push stack — see `specs/PHASES.md` §6 open questions
- [ ] Optional: un-ignore `docs/` in `.gitignore` if handbook should ship with commit 3

## PHASES roadmap (planned)

- [ ] 2a: `large_files_pro`, `tree_export_pro`
- [ ] 2b-1 / 2b-2: `backup_check_pro`
- [ ] 2c: `junk_cleaner_pro`
- [ ] 2d: perf bench promotion (conditional)
- [ ] Phase 3–5: env, vcs, security (medium detail)
- [ ] Phase 6: network/monitor (deferred schedule)

## Deferred / speculative (HORIZON only)

- `shell_history`, `config_diff`, `open_files`, `pipeline_check`, `perf_bench_pro` (product)
- `doc_gen` (separate product)
- `specs/future-benchmarks.md` — resume/adaptive/strategy benches (plan only)

## Hygiene

- [X] Handbook sync: `docs/CONTEXT.md`, `ARCHITECTURE.md`, `REFACTOR.md`, `specs/PHASES.md`, `specs/HORIZON.md`, `README.md`, `benchmarks/README.md`, `benchmarks/RESULTS.md` (2026-06-04)
- [ ] Push to origin — owner timing
