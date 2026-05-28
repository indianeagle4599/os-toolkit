# Usage analysis

Canonical spec for disk usage tree analysis. Implementation: `os_toolkit.analysis.usage`.

## What it does

Scans a single root directory up to a maximum depth and prints a hierarchical usage tree. Each line shows name, size, and percentage of the root total. Children below the percentage threshold are omitted from the printed tree. Supports a shallow scan mode that avoids rolling up sizes from directories deeper than the max depth.

## Inputs

Required: root path.

Optional: max depth (default 7); percentage threshold (default 1.0); verbosity 0, 1, or 2; shallow-scan flag.

Entrypoints:

- `disk_analyzer_pro.py` — may use optional `disk_analyzer_config.py` for defaults; CLI overrides config.
- `analyze_pro.py usage` — CLI only; no config file.

Both call the same `run_usage` function and must produce equivalent results for the same arguments.

## Outputs

Scan progress messages at higher verbosity levels. Unicode tree lines with connectors. Total analysis duration. Exit success when a scan completes; exit failure when scan data cannot be produced (invalid path or permissions).

## Guarantees

Read-only: no writes under the scanned tree. Directory traversal does not follow symbolic links for size accounting. Same inputs through either entrypoint yield the same tree structure and sizes.

## Known limits

No artifacts under `runs/`. No JSON export. Shallow mode may under-report totals for subtrees beyond max depth. Dual-root usage comparison is not implemented (deferred). Inter-usage compare is out of scope for this spec.

## Adversarial surfaces

Invalid or missing path; permission errors on subtrees; empty directory; single huge file; very deep or very wide trees; symlink cycles (not followed); non-UTF-8 console on Windows; threshold hiding all children.
