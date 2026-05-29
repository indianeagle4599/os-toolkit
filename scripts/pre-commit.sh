#!/bin/sh
# Git hook entry — delegates to `just pre-commit`.
set -e
cd "$(git rev-parse --show-toplevel)"
just pre-commit
