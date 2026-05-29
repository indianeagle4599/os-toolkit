"""
count_loc — tokenize-based code line counts for git-tracked Python.

Usage:
  python scripts/count_loc.py
  python scripts/count_loc.py --product-only
"""

import argparse
import subprocess
import tokenize
from collections import defaultdict
from pathlib import Path


def py_metrics(path: Path) -> tuple[int, int, int]:
    try:
        raw = path.read_bytes()
    except OSError:
        return 0, 0, 0
    lines = raw.splitlines()
    blank = sum(1 for ln in lines if not ln.strip())
    code_lines: set[int] = set()
    comment_lines: set[int] = set()
    try:
        line_iter = iter(raw.splitlines(True))

        def _readline():
            return next(line_iter, b"")

        for tok in tokenize.tokenize(_readline):
            if tok.start[0] == 0:
                continue
            ln = tok.start[0]
            if tok.type == tokenize.COMMENT:
                comment_lines.add(ln)
            elif tok.type not in (
                tokenize.NL,
                tokenize.NEWLINE,
                tokenize.ENCODING,
                tokenize.ENDMARKER,
                tokenize.INDENT,
                tokenize.DEDENT,
            ):
                code_lines.add(ln)
    except tokenize.TokenError:
        code = sum(1 for ln in lines if ln.strip() and not ln.strip().startswith("#"))
        return code, 0, blank
    code = len(code_lines)
    comment = len(comment_lines - code_lines)
    return code, comment, blank


def group_for(rel: str) -> str:
    if rel.startswith("tests/"):
        return "tests"
    if rel.startswith("benchmarks/"):
        return "benchmarks"
    if rel.startswith("os_toolkit/"):
        return "os_toolkit"
    if rel.startswith("scripts/"):
        return "scripts"
    if rel.endswith("_pro.py") or rel.endswith("_config.py"):
        return "root_CLIs"
    return "other"


def main() -> int:
    parser = argparse.ArgumentParser(description="Count git-tracked Python LOC.")
    parser.add_argument(
        "--product-only",
        action="store_true",
        help="Exclude tests/ from totals",
    )
    args = parser.parse_args()

    files = subprocess.check_output(["git", "ls-files"], text=True).splitlines()
    by_group: dict[str, dict[str, int]] = defaultdict(
        lambda: {"code": 0, "comment": 0, "blank": 0, "files": 0}
    )
    totals = {"code": 0, "comment": 0, "blank": 0, "files": 0}

    for rel in files:
        if not rel.endswith(".py"):
            continue
        p = Path(rel)
        if not p.is_file():
            continue
        if args.product_only and rel.startswith("tests/"):
            continue
        c, co, b = py_metrics(p)
        g = group_for(rel)
        for key, val in (("code", c), ("comment", co), ("blank", b)):
            by_group[g][key] += val
            totals[key] += val
        by_group[g]["files"] += 1
        totals["files"] += 1

    label = "product" if args.product_only else "all"
    print(f"Git-tracked Python code lines ({label}, tokenize)")
    print(f"{'group':<14} {'files':>5} {'code':>7}")
    for g in (
        "os_toolkit",
        "root_CLIs",
        "benchmarks",
        "scripts",
        "tests",
        "other",
    ):
        if g not in by_group:
            continue
        d = by_group[g]
        print(f"{g:<14} {d['files']:>5} {d['code']:>7}")
    print("-" * 28)
    print(f"{'TOTAL':<14} {totals['files']:>5} {totals['code']:>7}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
