"""
pre_commit_check — black + fast pytest for `just pre-commit`.

Feature: Local gate matching CI intent before commit.
Must do: Format changed Python files; run fast pytest; exit non-zero on failure.
Must NOT: Stage files or create commits.
"""

import subprocess
import sys
from pathlib import Path


def _changed_py_files() -> list[str]:
    names: list[str] = []
    for cmd in (
        ["git", "diff", "--name-only", "--diff-filter=ACM"],
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
    ):
        out = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if out.stdout:
            names.extend(out.stdout.splitlines())
    seen: set[str] = set()
    unique: list[str] = []
    for name in names:
        if name.endswith(".py") and name not in seen and Path(name).exists():
            seen.add(name)
            unique.append(name)
    return unique


def main() -> int:
    py_files = _changed_py_files()
    if py_files:
        print(f"black: {len(py_files)} file(s)")
        rc = subprocess.call([sys.executable, "-m", "black", *py_files])
        if rc != 0:
            print("pre-commit: FAIL (black)")
            return rc
        dirty = [
            f
            for f in py_files
            if subprocess.run(["git", "diff", "--quiet", f], check=False).returncode
            != 0
        ]
        if dirty:
            print("pre-commit: FAIL (black reformatted files; review, git add, retry):")
            for f in dirty:
                print(f"  - {f}")
            return 1
    else:
        print("black: no Python files in diff")

    print("pytest: fast suite")
    rc = subprocess.call(
        [
            sys.executable,
            "-m",
            "pytest",
            "-m",
            "not slow and not requires_ml",
        ]
    )
    if rc != 0:
        print("pre-commit: FAIL (pytest)")
        return rc

    print("pre-commit: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
