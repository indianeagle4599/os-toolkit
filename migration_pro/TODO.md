# TODO - Migration Pro

Working list for the migration tooling repo-in-folder. Keep this lean and ordered; do not add speculative features until the current layer is stable.

## Next up

[X] Finish artifact convention: standard run IDs, manifest fields, and run-local outputs.
[X] Replace profile generation with a one-pass scanner that avoids repeated subtree walks.
[X] Tighten canonical matcher outputs into a reliable migration-analysis artifact.

## Immediate Cleanup

[X] Create repo-like folder structure inside `migration_pro/`.
[X] Preserve existing generated artifacts under `migration_runs/initial/`.
[X] Move comparison, scan, cache, and filter code into responsibility folders.
[X] Remove duplicate legacy matcher path.
[X] Add migration-specific README and TODO.

## Near Term

[ ] Add duplicate/common-file detection based on size and name.
[ ] Add optional hash verification for duplicate/common-file candidates.
[ ] Add manifest-backed resume semantics for scan steps.
[ ] Add confidence reporting for matches and unmatched folders.
[ ] Decide whether retained initial artifacts should remain tracked or be pruned.

## Later

[ ] Generate dry-run migration plans.
[ ] Integrate file transfer execution only after dry-run plans are reliable.
[ ] Add safe delete proposals with explicit confirmation and audit output.
[ ] Add folder organizer flows.
[ ] Expand embedding-backed similarity only after the base matcher is stable.
