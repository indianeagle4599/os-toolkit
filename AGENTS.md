# AGENTS.md

Doctrine for humans and agents working on **os-toolkit**.

This file has **two coupled halves**—**intention** (what outcomes we optimize for) and **instructions** (how to act to deliver those outcomes). Omit either and behaviour drifts.

---

## Intention (north star)

- **Aligned collaboration:** move toward the stated goal together; clarify instead of guessing; stay brief and on-topic when asked.
- **Assumption control:** approvals, plans, and questions **before** work—until the owner relaxes that mode—so intent doesn't silently diverge.
- **Smallest viable change:** meet the approved task with the **least** churn in code lines, deps, abstraction, and process risk.
- **Kaizen-quality growth:** intentional, cumulative steps toward a coherent system—never speculative "extras" unrelated to today's behaviour.
- **Shared judgment:** act like one consistent decision-maker under these written constraints—but **explicit chat overrides** deliberate exceptions.

---

## Instructions (executable rules)

Sections **from here through "Handbook layout"** are **operational**. Follow them by default unless the chat clearly says otherwise.

**KPI — change footprint:** minimise **both** lines **added** and lines **edited** across touched files—the smallest correct diff wins. Prefer deletions where they simplify. Net growth requires **an explicit, task-grounded justification** (see simplification/refactor section).

---

## Collaboration and approval (default)

**Until the owner signals a looser mode:** ask **approval before everything** that touches the project or environment—plans, file edits, new files, and **commands** (installs, tests, downloads, formatters, etc.).

**Before any repo change or new file**, give a **short** pass: motivation, objectives, proposed tasks, reasoning, and **what is unclear**. **Ask and confirm**; do not fill gaps with assumptions.

If something is ambiguous, **stop and clarify**. Misalignment costs more than a quick question.

When the user says **stay focused** or **be brief**, tighten scope and wording; keep the thread on the **stated goal**.

**Working mode:** this owner follows a **dump → organise → plan → execute** rhythm. When the owner shares a set of ideas or requirements, treat it as raw material for planning — not a work order. The correct response is to surface an organised list of proposals, ask clarifying questions, agree on scope and order, and only then execute. Starting to code or edit files based on an idea dump alone — before the plan is confirmed — is the failure mode to avoid. Ask explicitly; a question costs nothing, an unwanted change costs real work.

---

## Core rule

Solve the current task with the **minimum necessary** change.

Prefer **deletion, reuse, and strict boundaries** over new layers.

**Kaizen:** grow the system **one intentional step at a time**—foresight for a clean whole, but only add what the **present** task justifies. Curate each step so the system stays coherent.

---

## Default workflow

1. Read enough context first (`AGENTS.md`, `docs/CONTEXT.md`, `docs/ARCHITECTURE.md` / `docs/REFACTOR.md` for migration layout, and code near the change).
2. Reuse existing code and patterns before adding new ones.
3. Delete dead or redundant code before introducing helpers.
4. Put validation and cleanup at the boundary.
5. Keep the inner execution path linear and clean.
6. After approval, run the **smallest** relevant verification only.

---

## Hard rules

- Do work **once**. Do not add duplicate read, resize, render, parse, serialize, or request-building paths.
- If **one prepared structure** can drive validation, batching, and execution, use that structure.
- Keep **one source of truth**. Do not mirror state across wrapper objects or parallel variables.
- Do **not** add single-use helpers unless they clearly reduce complexity.
- Do **not** add thin wrappers that only forward or rename values.
- Do **not** add speculative abstractions, compatibility layers, or future-proofing for flows that **do not exist**.
- Do **not** spread the same validation across outer and inner layers unless the inner check is **required for safety**.
- Do **not** add or modify **tests** in **dev mode** unless the owner explicitly asks. **Test mode** and owner-directed test work are exceptions.

---

## Code intent

### Top-Down Intent Rule

Every line of code added, moved, or modified must trace upward to a specific feature requirement:

- Feature → capability → function/module → each line in that function

No line for: “might be useful later”; “cleaner” without what it enables; “standard practice” without what it prevents; “defensive” without what it defends against.

Before any function: state (1) feature served, (2) what it must do, (3) what it does **not** do.

Before any line: which requirement from (2) does it satisfy?

Untraceable code is removed. If the agent cannot trace planned code, report and wait — do not invent justification.

Applies to: `justfile` recipes, benchmark CLI flags, planning-doc sections.

### Dependency Documentation Rule

Any commit that adds or changes a dependency must update [`requirements.txt`](requirements.txt) with comment lines above the package: **Used by:** … **Why:** … (same commit).

---

## Simplification and refactors

Search in this order:

1. What can be **deleted**?
2. What work is **duplicated**?
3. What guardrail belongs at the **boundary**?
4. What is the **minimum** missing code after that?

If line count grows, explain **exactly** which present-day behavior required it.

The following are **not** sufficient reasons **by themselves**: cleaner architecture, better separation of concerns, more flexible, future-proof, safer.

---

## Before adding code

Ask:

1. Is this reused?
2. Does it reduce complexity instead of just moving lines?
3. Can this be inlined?
4. Can existing code already own this responsibility?

If the answer is weak, do **not** add it.

---

## Planning and architecture

- For architectural or multi-step work: align on **current state**, desired direction, tradeoffs, and **open questions** **before** writing code.
- Prefer a **small, explicit plan** in chat (and updating `docs/CONTEXT.md` when facts change) instead of speculative refactors.
- Ask targeted questions when requirements, ownership boundaries, or execution strategy are unclear.
- Keep decisions grounded in **present** behavior—not imaginary future flows.

---

## Communication

- Be **concise**. Avoid oversized templates and nested structure unless they help.
- Call out dead code, duplicate work, wrapper layers, and irreducible complexity **explicitly**.

---

## Python habits

- Prefer **stdlib**; add dependencies only with clear payoff for an **approved** task. `analyze_pro.py compare` already uses numpy/pandas/sklearn — stay within that set unless a new dep is explicitly approved.
- **Concurrency / I/O**: multiprocessing is the established pattern here (Pool + imap_unordered); do not casually introduce threading or async. File operations must stay **idempotent** — skip-if-exists / resume semantics are a feature, preserve them.
- **CLI**: use `argparse` throughout; follow the existing `--verbosity 0/1/2` and `--dry-run` flag conventions when adding new scripts.
- **Errors**: actionable error messages surfaced to the operator; no swallowed exceptions. Use the `try/except OSError` boundary pattern already established in the scanners.
- **Naming**: new standalone scripts follow the `<name>_pro.py` convention at the repo root; sub-packages get their own directory.

---

## Code formatting and file headers

- **Headers:** every new script gets a module-level docstring matching the existing style:

  ```python
  """
  Script Name — short tagline.
  Features:
  - ...
  """
  ```

- **Formatting:** after editing Python files, run **`black`** on the touched files (once approved and if `black` is available).
- **Linter:** resolve any `flake8`/`pylint` errors introduced by the change; do not add `# noqa` without explaining why.

---

## Handbook layout

Keep handbook files **lean**:

- **`AGENTS.md`** (repo root) — collaboration and coding doctrine.
- **`docs/CONTEXT.md`** — product intent, phase, targets, repo facts.
- **`docs/ARCHITECTURE.md`** — short structural map of `os_toolkit/` and pillars (Analysis vs Transfer).
- **`docs/REFACTOR.md`** — migration-first decisions, 2×2 analysis model, refactor phases, deferred backlog.

**All agents:** after reading this file, read `docs/CONTEXT.md`. For migration package layout or refactor scope, read **`docs/REFACTOR.md`** (and **`docs/ARCHITECTURE.md`** for the one-page map).

Expand only when it removes confusion, not for ceremony.

---

## Quality engineering modes

### DEV MODE vs TEST MODE

- **Dev mode:** Full repo context; implement features; maintain [`specs/`](specs/) as the product contract; **does not** add or change [`tests/`](tests/) unless the owner explicitly requests tests in that thread.
- **Test mode:** Load **only** `AGENTS.md` and the relevant [`specs/*.md`](specs/) — no `os_toolkit/`, no `*_pro.py`, no existing `tests/` when generating new cases.
- **Handoff:** Spec files are the contract between modes.
- **One conversation per mode** — do not mix dev and test mode in one thread.

### REUSE DOCTRINE

Code reusability is a primary success metric. What was reused matters more than what was added.

### SPEC-FIRST RULE

New behavior requires an approved spec in [`specs/`](specs/) before implementation. Specs are plain English and committed.

### SPEC EVOLUTION RULE

Changing a documented guarantee requires updating the spec in the **same commit** as the implementation change. Spec drift is treated as a bug.

### TEST DOCTRINE

- Tests live in [`tests/`](tests/), committed; each test cites a spec **Guarantee** or **Adversarial surfaces** line in its docstring.
- Default pytest run excludes `slow` and `requires_ml` (see `pytest.ini`; rationale in `benchmarks/README.md` and repo README if present).

### BENCHMARK DOCTRINE

- Harness in [`benchmarks/`](benchmarks/), committed; results under [`benchmarks/results/`](benchmarks/results/) are gitignored.
- Benchmarks **measure**; they do not assert pass/fail thresholds in CI.
- Run benchmarks before merging performance-sensitive changes.
- `--ignore-manifest` is for local dev only; tagged results use `corpus_signature: "unverified"`.

---

## Precedence

1. **Explicit instructions in the current chat** beat this file and `docs/CONTEXT.md` when they intentionally conflict.

---

## Cursor

- **`.cursor/rules/os-toolkit-bootstrap.mdc`** (`alwaysApply: true`) bootstraps reading this file and `docs/CONTEXT.md`.
