# os-toolkit operator recipes — thin wrappers; CLIs own argparse.

set windows-shell := ["powershell.exe", "-NoProfile", "-Command"]
set shell := ["sh", "-cu"]

# Fast pytest (skips slow and ML-heavy tests).
test:
    python -m pytest -m "not slow and not requires_ml"

# Full pytest including slow and ML markers.
test-all:
    python -m pytest -m ""

# Run pytest on a single file path.
test-file FILE:
    python -m pytest {{FILE}}

# Forward args to file_transfer_pro CLI.
transfer *ARGS:
    python file_transfer_pro.py {{ARGS}}

# Forward args to analyze_pro CLI.
analyze *ARGS:
    python analyze_pro.py {{ARGS}}

# Forward args to smart_zip_pro CLI.
zip *ARGS:
    python smart_zip_pro.py {{ARGS}}

# Forward args to disk_analyzer_pro CLI.
disk *ARGS:
    python disk_analyzer_pro.py {{ARGS}}

# List all recipes with descriptions.
list:
    @just --list

# Fast pytest (bench smoke added Day 5).
check: test

# Install pip extras: dev, bench, ml, or all (stdlib default).
install PROFILE='':
    python scripts/install_profile.py {{PROFILE}}

# Black changed Python files plus fast pytest (no commit).
pre-commit:
    python scripts/pre_commit_check.py

# Install git pre-commit hook that runs just pre-commit (Unix).
[unix]
hooks-install:
    cp scripts/pre-commit.sh .git/hooks/pre-commit
    chmod +x .git/hooks/pre-commit
    @echo "Installed: $(pwd)/.git/hooks/pre-commit"

# Install git pre-commit hook that runs just pre-commit (Windows).
[windows]
hooks-install:
    Copy-Item scripts/pre-commit.sh .git/hooks/pre-commit -Force
    Write-Host "Installed: $((Get-Location).Path)/.git/hooks/pre-commit"

# Remove generated runs, bench artifacts, and caches (Unix).
[unix]
clean:
    rm -rf runs benchmarks/results benchmarks/corpus tmp
    find . -type d -name __pycache__ -prune -exec rm -rf {} +
    rm -rf .pytest_cache

# Remove generated runs, bench artifacts, and caches (Windows).
[windows]
clean:
    $dirs = @('runs','benchmarks/results','benchmarks/corpus','tmp','.pytest_cache'); foreach ($d in $dirs) { if (Test-Path $d) { Remove-Item -Recurse -Force $d } }
    Get-ChildItem -Recurse -Directory -Filter __pycache__ -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
