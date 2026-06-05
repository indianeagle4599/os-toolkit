# Integration and usability testing

## Overview

Usability tests treat the toolkit like an operator would: run a command, read stdout/stderr, and check artifacts (JSONL, manifest). They catch silent long runs, vague errors, and missing bench fields—not just unit logic.

When you fix a user-visible bug, add a test that would have failed before the fix. Prefer subprocess calls with tight timeouts; mark tests `@pytest.mark.slow` when they exceed ~10 seconds so `just check` stays fast.

## Automated tests

| Test | What it checks |
|------|----------------|
| `test_just_check_passes` | `just check` exits 0 (pytest + synthetic bench smoke). |
| `test_just_list_shows_recipes` | `just --list` includes core recipes with descriptions. |
| (see `tests/test_corpus_sampler.py`) | Corpus sampler prints progress lines on a tiny cache. |
| `test_fetch_corpus_handles_bad_url_gracefully` | Bad URL → clear fail message; manifest `failed`; other datasets still `ok`. |
| `test_bench_runners_validate_corpus_path` | Missing `--corpus` → clear error, nonzero exit, no traceback. |
| `test_root_pro_help_works` | Root `*_pro.py` tools respond to `--help` with purpose text. |
| `test_jsonl_outputs_have_required_fields` | Synthetic bench JSONL lines include required metrics/tags. |

Also see `tests/test_corpus_sampler.py` and `tests/test_dataset_registry.py` for sampler progress and dataset registry validation.

```bash
pytest tests/test_usability.py
pytest tests/test_corpus_sampler.py tests/test_dataset_registry.py
```

## Manual smoke tests

Commands that are slow, network-bound, or need real drives—run periodically, not on every commit:

Bench scripts are invoked via `python -m benchmarks.<script>`, not as standalone scripts.

```bash
just bench-fetch
python -m benchmarks.corpus --profile small/mixed
just bench-multi -- --suite all --corpus benchmarks/corpus/small/mixed \
  --drive-a <SSD_A> --drive-b <SSD_B> --results-dir benchmarks/results
# Single-run (optional):
just bench analysis -- --drive-a <SSD_A> --drive-b <SSD_B> --corpus benchmarks/corpus/small/mixed --output benchmarks/results/analysis_run1.jsonl
just bench zip -- --corpus benchmarks/corpus/small/mixed --output benchmarks/results/zip_run1.jsonl
just bench transfer -- --drive-a <SSD_A> --drive-b <SSD_B> --scenarios all --corpus benchmarks/corpus/small/mixed --output benchmarks/results/transfer_run1.jsonl
```

## When to run what

| When | What |
|------|------|
| Every commit | Pre-commit hook (`just pre-commit` or installed git hook) |
| Before push | `just check` plus one manual bench on a small corpus if you touched runners |
| Before release | Full integration: `just bench-fetch`, corpus sampling, real-corpus benches on target hardware |

## Adding new tests

1. Reproduce the bug as a single command (or short script).
2. Assert on **output the user sees** (messages, exit code, JSONL keys)—not private helpers.
3. Keep runtime under 10s when possible; otherwise `@pytest.mark.slow`.
4. Document any command that must stay owner-run in this file’s manual section.
